"""
Backfill script to fetch Deodap order emails and store them in the database.

This script:
1. Fetches all "Order Placed" emails from Jan 22, 2026 to today
2. Parses the Webkul order format
3. Stores orders in deodap_order_emails and deodap_order_items tables
4. Skips already-processed emails (by gmail_message_id)

Usage:
    cd /Users/manmehta/code/whisp
    python -m scripts.backfill_deodap_orders
"""

import asyncio
import logging
from datetime import datetime

from sqlalchemy import select, String, DateTime, Boolean, Integer, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from sqlalchemy.pool import StaticPool
from typing import Optional

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


# Standalone Base class to avoid importing the full app models
class Base(DeclarativeBase):
    pass


# Minimal model definitions (matching the real ones but standalone)
class DeodapOrderEmailStandalone(Base):
    __tablename__ = "deodap_order_emails"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    gmail_message_id: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    gmail_thread_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    email_subject: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    email_date: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    email_from: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    order_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    order_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payment_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    customer_name: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    address_line: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    city_state_pincode: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    country: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    whatsapp_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)


class DeodapOrderItemStandalone(Base):
    __tablename__ = "deodap_order_items"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    order_email_id: Mapped[int] = mapped_column(Integer, ForeignKey("deodap_order_emails.id"), nullable=False, index=True)
    product_name: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    sku: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    price: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    quantity: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)


async def backfill_deodap_orders():
    """Fetch and store all Deodap order emails from Jan 22 till today."""
    
    # Import only what we need - avoid importing models that trigger mapper cascade
    from app.core.config import config
    from app.integrations.gmail.service import GmailService
    from app.modules.kraftculture.service import parse_webkul_order_email
    
    # Create standalone engine and session (avoid importing app engine)
    engine = create_async_engine(
        config.db_url,
        echo=False,
        poolclass=StaticPool,
        future=True,
        connect_args={"check_same_thread": False},
    )
    AsyncSessionLocal = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    
    # Initialize Gmail service
    gmail_service = GmailService(
        credentials_path=config.gmail_credentials_path,
        token_path=config.gmail_token_path,
    )
    
    # Date range: Jan 22, 2026 to today
    start_date = datetime(2026, 1, 22)
    sender_email = config.kraftculture_sender_email or None
    
    logger.info(f"Starting backfill from {start_date.date()} to today")
    logger.info(f"Sender filter: {sender_email or 'None (all senders)'}")
    
    # Fetch emails - get up to 500 to ensure we get all of them
    logger.info("Fetching emails from Gmail...")
    emails = gmail_service.fetch_emails(
        from_email=sender_email,
        subject_contains="Order Placed",
        after_date=start_date,
        max_results=500,
    )
    
    logger.info(f"Found {len(emails)} emails to process")
    
    if not emails:
        logger.info("No emails found. Exiting.")
        return
    
    # Process and store emails
    async with AsyncSessionLocal() as db:
        processed_count = 0
        skipped_count = 0
        error_count = 0
        
        for email in emails:
            try:
                # Check if already processed
                result = await db.execute(
                    select(DeodapOrderEmailStandalone.id).where(
                        DeodapOrderEmailStandalone.gmail_message_id == email.id
                    )
                )
                if result.scalar_one_or_none() is not None:
                    logger.debug(f"Skipping already processed: {email.id}")
                    skipped_count += 1
                    continue
                
                # Parse email content
                html_content = email.html_body or email.body or ""
                parsed_data = parse_webkul_order_email(html_content)
                
                # Get items from parsed data
                items = parsed_data.get("items", [])
                
                # Create order email record
                order_email = DeodapOrderEmailStandalone(
                    gmail_message_id=email.id,
                    gmail_thread_id=email.thread_id,
                    email_subject=email.subject,
                    email_date=email.date,
                    email_from=email.from_email,
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
                    whatsapp_sent=False,  # Don't send WhatsApp for backfill
                )
                
                db.add(order_email)
                await db.flush()  # Get the ID
                
                # Create order items
                for item in items:
                    order_item = DeodapOrderItemStandalone(
                        order_email_id=order_email.id,
                        product_name=item.get("product_name"),
                        sku=item.get("sku"),
                        price=item.get("price"),
                        quantity=item.get("quantity"),
                    )
                    db.add(order_item)
                
                processed_count += 1
                logger.info(
                    f"Processed: Order #{parsed_data.get('order_id', 'N/A')} - "
                    f"{parsed_data.get('customer_name', 'Unknown')} - "
                    f"{len(items)} items - "
                    f"Date: {email.date}"
                )
                
            except Exception as e:
                logger.error(f"Error processing email {email.id}: {e}")
                error_count += 1
                continue
        
        # Commit all changes
        await db.commit()
        
        logger.info("=" * 50)
        logger.info("BACKFILL COMPLETE")
        logger.info(f"  Processed: {processed_count}")
        logger.info(f"  Skipped (already exists): {skipped_count}")
        logger.info(f"  Errors: {error_count}")
        logger.info("=" * 50)


if __name__ == "__main__":
    asyncio.run(backfill_deodap_orders())
