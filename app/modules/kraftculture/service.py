import logging
import re
from datetime import datetime, timedelta
from typing import Optional

from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.integrations.gmail.service import GmailService
from app.integrations.gmail.dto import EmailDTO
from app.integrations.whatsapp.service import WhatsAppService
from app.core.cache.service import CacheService
from app.modules.kraftculture.dto import ParsedEmailData, ProcessEmailsResponse
from app.modules.kraftculture.models import DeodapOrderEmail

logger = logging.getLogger(__name__)

# Cache key for storing the last processed email date
LAST_PROCESSED_DATE_KEY = "kraftculture:last_processed_date"

# Default lookback period if no pointer date is set
DEFAULT_LOOKBACK_DAYS = 7


def parse_webkul_order_email(html: str) -> dict:
    """Parse Webkul order email HTML into structured data."""
    soup = BeautifulSoup(html, "html.parser")

    data = {}

    # --- Order table ---
    table = soup.find("table")
    if not table:
        return {}

    rows = table.find_all("tr")

    # First product row
    product_row = None
    for row in rows:
        tds = row.find_all("td")
        if len(tds) >= 8:
            product_row = tds
            break

    if product_row:
        data["order_id"] = product_row[0].get_text(strip=True)
        data["order_name"] = product_row[1].get_text(strip=True)
        data["product_name"] = product_row[3].get_text(strip=True)
        data["sku"] = product_row[4].get_text(strip=True)
        data["price"] = product_row[5].get_text(strip=True)
        data["quantity"] = product_row[6].get_text(strip=True)

    # --- Order total & payment status ---
    for row in rows:
        text = row.get_text(" ", strip=True).lower()
        if "payment status" in text:
            match = re.search(r"payment status\s*-\s*(\w+)", text)
            if match:
                data["payment_status"] = match.group(1).capitalize()

    # --- Customer & address ---
    customer_block = soup.find("div", style=re.compile("text-transform:capitalize"))
    if customer_block:
        lines = [p.get_text(strip=True) for p in customer_block.find_all(["h3", "p"])]

        if lines:
            data["customer_name"] = lines[0]

        if len(lines) >= 2:
            data["address_line"] = lines[1]

        if len(lines) >= 3:
            data["city_state_pincode"] = lines[2]

        if len(lines) >= 4:
            data["country"] = lines[3]

    return data


class KraftcultureService:
    """Service for processing Kraftculture emails and sending WhatsApp notifications."""

    # Maximum characters to send in a WhatsApp message
    MAX_MESSAGE_LENGTH = 4000

    def __init__(
        self,
        gmail_service: GmailService,
        whatsapp_service: WhatsAppService,
        cache_service: CacheService,
        default_sender_email: str = "",
        whatsapp_numbers: list[str] = None,
    ):
        self.gmail_service = gmail_service
        self.whatsapp_service = whatsapp_service
        self.cache_service = cache_service
        self.default_sender_email = default_sender_email
        self.whatsapp_numbers = whatsapp_numbers or ["919328483009"]

    async def _get_pointer_date(self) -> datetime:
        """
        Get the last processed email date from cache.
        Returns default lookback date if not set.
        """
        cached_date = await self.cache_service.get_key(LAST_PROCESSED_DATE_KEY)
        print(f"Cached date: {cached_date}")
        
        if cached_date:
            try:
                return datetime.fromisoformat(cached_date)
            except (ValueError, TypeError):
                logger.warning(f"Invalid cached date format: {cached_date}")
        
        # Default to 7 days ago
        return datetime.now() - timedelta(days=DEFAULT_LOOKBACK_DAYS)

    async def _update_pointer_date(self, new_date: datetime) -> None:
        """Update the last processed email date in cache."""
        await self.cache_service.set_key(
            LAST_PROCESSED_DATE_KEY,
            new_date.isoformat(),
            ttl=None,  # No expiry
        )
        logger.info(f"Updated pointer date to: {new_date.isoformat()}")

    async def _is_email_processed(self, db: AsyncSession, gmail_message_id: str) -> bool:
        """Check if an email has already been processed."""
        result = await db.execute(
            select(DeodapOrderEmail.id).where(
                DeodapOrderEmail.gmail_message_id == gmail_message_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def _save_order_email(
        self,
        db: AsyncSession,
        email: EmailDTO,
        parsed_data: ParsedEmailData,
        whatsapp_sent: bool = False,
    ) -> DeodapOrderEmail:
        """Save a parsed order email to the database."""
        order_email = DeodapOrderEmail(
            gmail_message_id=email.id,
            gmail_thread_id=email.thread_id,
            email_subject=email.subject,
            email_date=email.date,
            email_from=email.from_email,
            order_id=parsed_data.order_id,
            order_name=parsed_data.order_name,
            product_name=parsed_data.product_name,
            sku=parsed_data.sku,
            price=parsed_data.price,
            quantity=parsed_data.quantity,
            payment_status=parsed_data.payment_status,
            customer_name=parsed_data.customer_name,
            address_line=parsed_data.address_line,
            city_state_pincode=parsed_data.city_state_pincode,
            country=parsed_data.country,
            whatsapp_sent=whatsapp_sent,
        )
        
        db.add(order_email)
        await db.flush()
        
        logger.info(f"Saved order email {email.id} to database")
        return order_email

    def parse_email(self, email: EmailDTO) -> ParsedEmailData:
        """
        Parse Webkul order email content into structured data.
        
        Args:
            email: The email DTO to parse
            
        Returns:
            ParsedEmailData with extracted order information
        """
        # Use HTML body for parsing if available, otherwise fall back to plain text
        html_content = email.html_body or email.body or ""
        
        # Parse the Webkul order email
        parsed_data = parse_webkul_order_email(html_content)
        
        return ParsedEmailData(
            order_id=parsed_data.get("order_id"),
            order_name=parsed_data.get("order_name"),
            product_name=parsed_data.get("product_name"),
            sku=parsed_data.get("sku"),
            price=parsed_data.get("price"),
            quantity=parsed_data.get("quantity"),
            payment_status=parsed_data.get("payment_status"),
            customer_name=parsed_data.get("customer_name"),
            address_line=parsed_data.get("address_line"),
            city_state_pincode=parsed_data.get("city_state_pincode"),
            country=parsed_data.get("country"),
        )

    def format_message(self, email: EmailDTO, parsed_data: ParsedEmailData) -> str:
        """
        Format the parsed order data for WhatsApp message.
        
        Args:
            email: The original email DTO
            parsed_data: The parsed email data
            
        Returns:
            Formatted message string (truncated to MAX_MESSAGE_LENGTH)
        """
        parts = []
        
        # Header
        parts.append("🛒 *New Order Received*")
        parts.append("")
        
        # Order details
        if parsed_data.order_id:
            parts.append(f"📋 *Order ID:* {parsed_data.order_id}")
        
        if parsed_data.order_name:
            parts.append(f"🏷️ *Order Name:* {parsed_data.order_name}")
        
        if parsed_data.product_name:
            parts.append(f"📦 *Product:* {parsed_data.product_name}")
        
        if parsed_data.sku:
            parts.append(f"🔖 *SKU:* {parsed_data.sku}")
        
        if parsed_data.price:
            parts.append(f"💰 *Price:* {parsed_data.price}")
        
        if parsed_data.quantity:
            parts.append(f"🔢 *Quantity:* {parsed_data.quantity}")
        
        if parsed_data.payment_status:
            parts.append(f"💳 *Payment:* {parsed_data.payment_status}")
        
        # Customer details
        if parsed_data.customer_name:
            parts.append("")
            parts.append("👤 *Customer Details:*")
            parts.append(f"   {parsed_data.customer_name}")
            
            if parsed_data.address_line:
                parts.append(f"   {parsed_data.address_line}")
            
            if parsed_data.city_state_pincode:
                parts.append(f"   {parsed_data.city_state_pincode}")
            
            if parsed_data.country:
                parts.append(f"   {parsed_data.country}")
        
        # If no parsed data, show warning
        if not any([parsed_data.order_id, parsed_data.product_name, parsed_data.customer_name]):
            parts.append("")
            parts.append("⚠️ Could not parse order details from email.")
        
        message = "\n".join(parts)
        
        # Truncate to max length
        if len(message) > self.MAX_MESSAGE_LENGTH:
            message = message[: self.MAX_MESSAGE_LENGTH - 3] + "..."
        
        return message

    async def process_emails(
        self,
        db: AsyncSession,
        from_email: Optional[str] = None,
        max_results: int = 10,
    ) -> ProcessEmailsResponse:
        """
        Fetch emails, parse them, store in DB, and send to WhatsApp.
        
        Uses date-based filtering with a pointer stored in cache.
        Skips already-processed emails by checking gmail_message_id in DB.
        
        Args:
            db: Database session
            from_email: Sender email to filter (uses default if not provided)
            max_results: Maximum number of emails to fetch
            
        Returns:
            ProcessEmailsResponse with processing results
        """
        sender = from_email or self.default_sender_email
        errors = []
        processed_count = 0
        sent_count = 0
        skipped_count = 0
        latest_email_date: Optional[datetime] = None

        # Get the pointer date (last processed date)
        pointer_date = await self._get_pointer_date()
        
        logger.info(
            f"Processing kraftculture emails from: {sender or 'all'}, "
            f"after: {pointer_date.isoformat()}, max_results: {max_results}"
        )

        try:
            # Fetch emails after pointer date with "Order Placed" subject
            emails = self.gmail_service.fetch_emails(
                from_email=sender if sender else None,
                subject_contains="Order Placed",
                after_date=pointer_date,
                max_results=max_results,
            )
            
            logger.info(f"Fetched {len(emails)} emails to process")

            for email in emails:
                try:
                    # Check if already processed
                    if await self._is_email_processed(db, email.id):
                        logger.debug(f"Skipping already processed email: {email.id}")
                        skipped_count += 1
                        continue
                    
                    # Parse email
                    parsed_data = self.parse_email(email)
                    
                    # Format message
                    message = self.format_message(email, parsed_data)
                    
                    # Send to all WhatsApp numbers
                    whatsapp_sent = False
                    for number in self.whatsapp_numbers:
                        try:
                            await self.whatsapp_service.send_text(number, message)
                            sent_count += 1
                            whatsapp_sent = True
                            logger.info(
                                f"Sent email '{email.subject}' to {number}"
                            )
                        except Exception as e:
                            error_msg = f"Failed to send to {number}: {str(e)}"
                            logger.error(error_msg)
                            errors.append(error_msg)
                    
                    # Save to database
                    await self._save_order_email(db, email, parsed_data, whatsapp_sent)
                    
                    processed_count += 1
                    
                    # Track latest email date for pointer update
                    if email.date:
                        if latest_email_date is None or email.date > latest_email_date:
                            latest_email_date = email.date

                except Exception as e:
                    error_msg = f"Error processing email {email.id}: {str(e)}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            # Commit all changes
            await db.commit()
            
            # Update pointer date if we processed any emails
            if latest_email_date:
                await self._update_pointer_date(latest_email_date)

        except Exception as e:
            await db.rollback()
            error_msg = f"Error fetching emails: {str(e)}"
            logger.error(error_msg)
            errors.append(error_msg)

        logger.info(
            f"Processing complete: {processed_count} processed, "
            f"{skipped_count} skipped, {sent_count} sent, {len(errors)} errors"
        )

        return ProcessEmailsResponse(
            processed_count=processed_count,
            sent_count=sent_count,
            errors=errors,
        )
