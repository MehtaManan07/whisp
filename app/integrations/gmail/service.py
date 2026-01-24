import base64
import logging
import os
from datetime import datetime
from email.utils import parsedate_to_datetime
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

from app.integrations.gmail.dto import EmailDTO

logger = logging.getLogger(__name__)


class GmailService:
    """Service for interacting with Gmail API."""

    # If modifying these scopes, delete the token.json file
    SCOPES = [
        "https://www.googleapis.com/auth/gmail.readonly",
        "https://www.googleapis.com/auth/gmail.modify",  # For marking as read
    ]

    def __init__(
        self,
        credentials_path: str = "credentials.json",
        token_path: str = "token.json",
    ):
        self.credentials_path = credentials_path
        self.token_path = token_path
        self._service = None
        self._credentials = None

    def _get_credentials(self) -> Credentials:
        """Get or refresh OAuth2 credentials."""
        creds = None

        # Load existing token if available
        if os.path.exists(self.token_path):
            creds = Credentials.from_authorized_user_file(self.token_path, self.SCOPES)

        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired Gmail credentials")
                creds.refresh(Request())
            else:
                if not os.path.exists(self.credentials_path):
                    raise FileNotFoundError(
                        f"Gmail credentials file not found at {self.credentials_path}. "
                        "Please download from Google Cloud Console."
                    )
                logger.info("Initiating Gmail OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_path, self.SCOPES
                )
                creds = flow.run_local_server(port=0)

            # Save the credentials for next run
            with open(self.token_path, "w") as token:
                token.write(creds.to_json())
                logger.info(f"Saved Gmail credentials to {self.token_path}")

        return creds

    def _get_service(self):
        """Get or create Gmail API service instance."""
        if self._service is None:
            self._credentials = self._get_credentials()
            self._service = build("gmail", "v1", credentials=self._credentials)
        return self._service

    def _parse_email_headers(self, headers: list) -> dict:
        """Parse email headers into a dictionary."""
        result = {}
        for header in headers:
            name = header.get("name", "").lower()
            value = header.get("value", "")
            if name in ["from", "to", "subject", "date"]:
                result[name] = value
        return result

    def _parse_from_header(self, from_header: str) -> tuple[str, str]:
        """Parse 'From' header into name and email."""
        if "<" in from_header and ">" in from_header:
            name = from_header.split("<")[0].strip().strip('"')
            email = from_header.split("<")[1].split(">")[0].strip()
        else:
            name = ""
            email = from_header.strip()
        return name, email

    def _get_email_body(self, payload: dict) -> tuple[str, Optional[str]]:
        """Extract plain text and HTML body from email payload."""
        plain_body = ""
        html_body = None

        def extract_parts(part: dict):
            nonlocal plain_body, html_body
            mime_type = part.get("mimeType", "")
            
            if mime_type == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    plain_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif mime_type == "text/html":
                data = part.get("body", {}).get("data", "")
                if data:
                    html_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
            elif "parts" in part:
                for sub_part in part["parts"]:
                    extract_parts(sub_part)

        # Handle single-part messages
        if "body" in payload and payload.get("body", {}).get("data"):
            data = payload["body"]["data"]
            plain_body = base64.urlsafe_b64decode(data).decode("utf-8", errors="replace")
        
        # Handle multi-part messages
        if "parts" in payload:
            for part in payload["parts"]:
                extract_parts(part)

        return plain_body, html_body

    def fetch_emails(
        self,
        from_email: Optional[str] = None,
        subject_contains: Optional[str] = None,
        after_date: Optional[datetime] = None,
        max_results: int = 10,
        unread_only: bool = False,
    ) -> list[EmailDTO]:
        """
        Fetch emails from Gmail with optional filters.
        
        Args:
            from_email: Filter by sender email address
            subject_contains: Filter by subject containing text
            after_date: Only return emails after this date
            max_results: Maximum number of emails to return
            unread_only: Only return unread emails
            
        Returns:
            List of EmailDTO objects
        """
        service = self._get_service()
        
        # Build search query
        query_parts = []
        if from_email:
            query_parts.append(f"from:{from_email}")
        if subject_contains:
            query_parts.append(f"subject:{subject_contains}")
        if after_date:
            query_parts.append(f"after:{after_date.strftime('%Y/%m/%d')}")
        if unread_only:
            query_parts.append("is:unread")
        
        query = " ".join(query_parts) if query_parts else None
        
        logger.info(f"Fetching emails with query: {query or 'all'}")

        try:
            # List messages
            results = (
                service.users()
                .messages()
                .list(userId="me", q=query, maxResults=max_results)
                .execute()
            )
            
            messages = results.get("messages", [])
            logger.info(f"Found {len(messages)} emails")

            emails = []
            for msg in messages:
                # Get full message details
                msg_data = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg["id"], format="full")
                    .execute()
                )
                
                payload = msg_data.get("payload", {})
                headers = self._parse_email_headers(payload.get("headers", []))
                
                # Parse from header
                from_name, from_addr = self._parse_from_header(headers.get("from", ""))
                
                # Parse date
                date_str = headers.get("date", "")
                try:
                    date = parsedate_to_datetime(date_str) if date_str else None
                except Exception:
                    date = None
                
                # Get body
                plain_body, html_body = self._get_email_body(payload)
                
                # Check labels for unread status
                labels = msg_data.get("labelIds", [])
                is_unread = "UNREAD" in labels
                
                email = EmailDTO(
                    id=msg_data["id"],
                    thread_id=msg_data.get("threadId", ""),
                    subject=headers.get("subject", ""),
                    from_email=from_addr,
                    from_name=from_name,
                    to_email=headers.get("to", ""),
                    body=plain_body,
                    html_body=html_body,
                    date=date,
                    snippet=msg_data.get("snippet", ""),
                    is_unread=is_unread,
                    labels=labels,
                )
                emails.append(email)

            return emails

        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            raise

    def mark_as_read(self, message_id: str) -> bool:
        """
        Mark an email as read.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful
        """
        service = self._get_service()
        
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"removeLabelIds": ["UNREAD"]},
            ).execute()
            logger.info(f"Marked email {message_id} as read")
            return True
        except Exception as e:
            logger.error(f"Error marking email as read: {e}")
            raise

    def mark_as_unread(self, message_id: str) -> bool:
        """
        Mark an email as unread.
        
        Args:
            message_id: Gmail message ID
            
        Returns:
            True if successful
        """
        service = self._get_service()
        
        try:
            service.users().messages().modify(
                userId="me",
                id=message_id,
                body={"addLabelIds": ["UNREAD"]},
            ).execute()
            logger.info(f"Marked email {message_id} as unread")
            return True
        except Exception as e:
            logger.error(f"Error marking email as unread: {e}")
            raise
