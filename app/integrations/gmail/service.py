"""
Gmail API service.

Auth + message fetch + mark-as-read. The googleapiclient SDK is synchronous, so
every public method runs the blocking work in a thread via ``asyncio.to_thread``
to stay compatible with the async app/scheduler.
"""

import asyncio
import base64
import logging
import os
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.core.config import config
from app.integrations.gmail.dto import EmailDTO
from app.integrations.gmail.senders import (
    TransactionSender,
    bank_for_sender,
    build_transaction_query,
)

logger = logging.getLogger(__name__)

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]*\n[ \t\n]*")


class GmailService:
    """Read-only-ish Gmail client (also marks messages read via modify scope)."""

    # If these scopes change, delete token.json and re-authorize.
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",
    ]

    def __init__(
        self,
        credentials_path: Optional[str] = None,
        token_path: Optional[str] = None,
    ):
        self.credentials_path = credentials_path or config.gmail_credentials_path
        self.token_path = token_path or config.gmail_token_path
        self._service = None

    # -------------------------------------------------------------------------
    # Auth (sync)
    # -------------------------------------------------------------------------

    def _get_credentials(self) -> Credentials:
        creds = None
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.debug("Refreshing expired Gmail credentials")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.credentials_path}. "
                        "Download the OAuth client from Google Cloud Console."
                    )
                logger.info("Initiating Gmail OAuth flow (one-time)")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(self.token_path, "w") as token_file:
                token_file.write(creds.to_json())
                logger.debug("Saved Gmail credentials to %s", self.token_path)

        return creds

    def _get_service(self):
        if self._service is None:
            creds = self._get_credentials()
            self._service = build("gmail", "v1", credentials=creds, cache_discovery=False)
        return self._service

    # -------------------------------------------------------------------------
    # Parsing helpers (sync)
    # -------------------------------------------------------------------------

    @staticmethod
    def _parse_headers(headers: list) -> dict:
        result = {}
        for header in headers:
            name = header.get("name", "").lower()
            if name in ("from", "to", "subject", "date"):
                result[name] = header.get("value", "")
        return result

    @staticmethod
    def _parse_from(from_header: str) -> tuple[str, str]:
        if "<" in from_header and ">" in from_header:
            name = from_header.split("<")[0].strip().strip('"')
            email = from_header.split("<")[1].split(">")[0].strip()
        else:
            name, email = "", from_header.strip()
        return name, email.lower()

    @classmethod
    def _get_body(cls, payload: dict) -> str:
        plain = ""
        html = ""

        def walk(part: dict):
            nonlocal plain, html
            mime = part.get("mimeType", "")
            data = part.get("body", {}).get("data")
            if mime == "text/plain" and data and not plain:
                plain = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif mime == "text/html" and data and not html:
                html = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            for sub in part.get("parts", []) or []:
                walk(sub)

        if payload.get("body", {}).get("data") and not payload.get("parts"):
            plain = base64.urlsafe_b64decode(payload["body"]["data"]).decode(
                "utf-8", errors="replace"
            )
        for part in payload.get("parts", []) or []:
            walk(part)

        if plain.strip():
            return plain.strip()
        if html.strip():
            return cls._strip_html(html)
        return ""

    @staticmethod
    def _strip_html(html: str) -> str:
        text = _HTML_TAG_RE.sub(" ", html)
        text = (
            text.replace("&nbsp;", " ")
            .replace("&amp;", "&")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
            .replace("&rsquo;", "'")
            .replace("&#39;", "'")
        )
        text = _WS_RE.sub("\n", text)
        return text.strip()

    def _to_dto(self, msg_data: dict) -> EmailDTO:
        payload = msg_data.get("payload", {})
        headers = self._parse_headers(payload.get("headers", []))
        from_name, from_addr = self._parse_from(headers.get("from", ""))
        try:
            date = parsedate_to_datetime(headers["date"]) if headers.get("date") else None
        except Exception:
            date = None
        internal_date = None
        raw_internal = msg_data.get("internalDate")
        if raw_internal is not None:
            try:
                internal_date = int(raw_internal) // 1000  # ms -> seconds
            except (TypeError, ValueError):
                internal_date = None
        return EmailDTO(
            id=msg_data["id"],
            thread_id=msg_data.get("threadId", ""),
            subject=headers.get("subject", ""),
            from_email=from_addr,
            from_name=from_name,
            date=date,
            internal_date=internal_date,
            body=self._get_body(payload),
            snippet=msg_data.get("snippet", ""),
        )

    # -------------------------------------------------------------------------
    # Sync workers
    # -------------------------------------------------------------------------

    def _fetch_sync(self, query: str, max_results: int) -> list[EmailDTO]:
        service = self._get_service()
        logger.debug("Gmail query: %s", query or "(all)")

        listing = (
            service.users()
            .messages()
            .list(userId="me", q=query or None, maxResults=max_results)
            .execute()
        )
        messages = listing.get("messages", [])
        logger.debug("Gmail returned %d message id(s)", len(messages))

        emails: list[EmailDTO] = []
        for msg in messages:
            msg_data = (
                service.users()
                .messages()
                .get(userId="me", id=msg["id"], format="full")
                .execute()
            )
            emails.append(self._to_dto(msg_data))
        return emails

    def _mark_read_sync(self, message_id: str) -> bool:
        service = self._get_service()
        service.users().messages().modify(
            userId="me",
            id=message_id,
            body={"removeLabelIds": ["UNREAD"]},
        ).execute()
        return True

    # -------------------------------------------------------------------------
    # Async public API
    # -------------------------------------------------------------------------

    async def fetch(self, query: str, max_results: int = 25) -> list[EmailDTO]:
        """Fetch emails matching a raw Gmail query string."""
        try:
            return await asyncio.to_thread(self._fetch_sync, query, max_results)
        except Exception as e:
            logger.error("Gmail fetch failed: %s", e)
            raise

    async def fetch_transaction_emails(
        self,
        senders: Optional[list[TransactionSender]] = None,
        newer_than_days: int = 1,
        after_epoch: Optional[int] = None,
        max_results: int = 50,
    ) -> list[EmailDTO]:
        """Fetch likely transaction alerts using the sender allowlist pre-filter.

        Uses ``after_epoch`` (high-water-mark) when provided, else ``newer_than_days``.
        """
        query = build_transaction_query(
            senders, newer_than_days=newer_than_days, after_epoch=after_epoch
        )
        if not query:
            logger.warning("No transaction senders configured; skipping Gmail fetch")
            return []
        return await self.fetch(query, max_results=max_results)

    async def mark_as_read(self, message_id: str) -> bool:
        try:
            return await asyncio.to_thread(self._mark_read_sync, message_id)
        except Exception as e:
            logger.warning("Gmail mark_as_read failed for %s: %s", message_id, e)
            return False

    @staticmethod
    def resolve_bank(from_email: str) -> Optional[str]:
        return bank_for_sender(from_email)
