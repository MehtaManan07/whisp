"""Email parsers for HDFC and ICICI bank transaction emails."""

import re
import logging
from datetime import datetime
from typing import Optional
from bs4 import BeautifulSoup

from app.integrations.gmail.dto import EmailDTO
from app.modules.bank_transactions.dto import ParsedTransactionData

logger = logging.getLogger(__name__)


def parse_icici_transaction(email: EmailDTO) -> Optional[ParsedTransactionData]:
    """
    Parse ICICI Credit Card transaction alert email.
    
    Example pattern:
    Your ICICI Bank Credit Card XX4001 has been used for a transaction of INR 2.01 
    on Feb 28, 2026 at 02:43:00. Info: MAXLIFEINSUR.
    """
    try:
        html_content = email.html_body or email.body or ""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(" ", strip=True)
        
        # Match amount pattern: "transaction of INR <amount>"
        amount_match = re.search(r'transaction of INR\s+([\d,]+\.?\d*)', text, re.IGNORECASE)
        if not amount_match:
            logger.debug(f"ICICI: No amount found in email {email.id}")
            return None
        
        amount_str = amount_match.group(1).replace(',', '')
        amount = float(amount_str)
        
        # Match date pattern: "on <date> at <time>"
        date_match = re.search(r'on\s+([A-Za-z]+\s+\d+,\s+\d{4})\s+at\s+(\d{2}:\d{2}:\d{2})', text)
        transaction_date = None
        if date_match:
            try:
                date_str = f"{date_match.group(1)} {date_match.group(2)}"
                transaction_date = datetime.strptime(date_str, "%b %d, %Y %H:%M:%S")
            except ValueError:
                logger.warning(f"ICICI: Could not parse date: {date_match.group(0)}")
        
        # Match merchant: "Info: <merchant>"
        merchant_match = re.search(r'Info:\s*([A-Z0-9\s]+)', text)
        merchant = merchant_match.group(1).strip() if merchant_match else None
        
        # Match card last 4 digits: "Credit Card XX<digits>"
        card_match = re.search(r'Credit Card XX(\d{4})', text)
        card_last4 = card_match.group(1) if card_match else None
        
        return ParsedTransactionData(
            amount=amount,
            merchant=merchant,
            transaction_date=transaction_date,
            card_last4=card_last4,
            bank="ICICI",
            raw_info=text[:500]  # Store first 500 chars for debugging
        )
        
    except Exception as e:
        logger.error(f"Error parsing ICICI email {email.id}: {e}")
        return None


def parse_hdfc_transaction(email: EmailDTO) -> Optional[ParsedTransactionData]:
    """
    Parse HDFC Bank transaction alert emails (UPI and Credit Card).

    Supported patterns:
      UPI:  Rs.150.00 has been debited from account 1771 to VPA nitisha.mehta3028@oksbi
            NITISHA RAJEN MEHTA on 28-02-26.
            Your UPI transaction reference number is 605965098644.
      CC:   Rs.350.00 is debited from your HDFC Bank Credit Card ending 0254
            towards PYU*Swiggy Food on 15 Mar, 2026 at 15:59:47.
    """
    try:
        html_content = email.html_body or email.body or ""
        soup = BeautifulSoup(html_content, "html.parser")
        text = soup.get_text(" ", strip=True)

        # Match amount: "Rs.<amount> has been debited" OR "Rs.<amount> is debited"
        amount_match = re.search(
            r'Rs\.\s*([\d,]+\.?\d*)\s+(?:has been|is) debited', text, re.IGNORECASE
        )
        if not amount_match:
            logger.debug(f"HDFC: No debit amount found in email {email.id}")
            return None

        amount_str = amount_match.group(1).replace(',', '')
        amount = float(amount_str)

        # --- Merchant ---
        merchant = None
        # Credit Card pattern: "towards <merchant> on"
        cc_merchant_match = re.search(r'towards\s+(.+?)\s+on\s+\d', text)
        if cc_merchant_match:
            merchant = cc_merchant_match.group(1).strip()
        else:
            # UPI pattern: "to VPA <vpa> <NAME> on"
            upi_merchant_match = re.search(r'to VPA\s+[\w.@]+\s+([A-Z\s]+)\s+on', text)
            if upi_merchant_match:
                merchant = upi_merchant_match.group(1).strip()

        # --- Date ---
        transaction_date = None
        # Credit Card pattern: "on 15 Mar, 2026 at 15:59:47"
        cc_date_match = re.search(
            r'on\s+(\d{1,2}\s+[A-Za-z]+,?\s+\d{4})\s+at\s+(\d{2}:\d{2}:\d{2})', text
        )
        if cc_date_match:
            raw_date = cc_date_match.group(1).replace(',', '')
            raw_time = cc_date_match.group(2)
            for fmt in ("%d %b %Y %H:%M:%S", "%d %B %Y %H:%M:%S"):
                try:
                    transaction_date = datetime.strptime(f"{raw_date} {raw_time}", fmt)
                    break
                except ValueError:
                    continue
        if not transaction_date:
            # UPI pattern: "on DD-MM-YY"
            upi_date_match = re.search(r'on\s+(\d{2}-\d{2}-\d{2})', text)
            if upi_date_match:
                try:
                    transaction_date = datetime.strptime(upi_date_match.group(1), "%d-%m-%y")
                except ValueError:
                    logger.warning(f"HDFC: Could not parse date: {upi_date_match.group(0)}")

        # --- Reference number (UPI only) ---
        ref_match = re.search(r'reference number is\s+(\d+)', text)
        reference_number = ref_match.group(1) if ref_match else None

        # --- Card / account last 4 digits ---
        card_last4 = None
        cc_card_match = re.search(r'(?:Credit Card|Card) ending\s+(\d{4})', text)
        if cc_card_match:
            card_last4 = cc_card_match.group(1)
        else:
            acct_match = re.search(r'from account\s+(\d{4})', text)
            if acct_match:
                card_last4 = acct_match.group(1)

        return ParsedTransactionData(
            amount=amount,
            merchant=merchant,
            transaction_date=transaction_date,
            reference_number=reference_number,
            card_last4=card_last4,
            bank="HDFC",
            raw_info=text[:500],
        )

    except Exception as e:
        logger.error(f"Error parsing HDFC email {email.id}: {e}")
        return None


def parse_bank_transaction_email(email: EmailDTO) -> Optional[ParsedTransactionData]:
    """
    Detect bank and parse transaction email.
    
    Returns ParsedTransactionData if this is a recognized bank transaction email,
    None otherwise.
    """
    # Check ICICI
    if 'icicibank.com' in email.from_email.lower():
        if 'transaction alert' in email.subject.lower():
            return parse_icici_transaction(email)
    
    # Check HDFC
    if 'hdfcbank' in email.from_email.lower():
        # HDFC sends various transaction alerts
        return parse_hdfc_transaction(email)
    
    return None
