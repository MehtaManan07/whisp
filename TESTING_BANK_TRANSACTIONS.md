# Bank Transaction Feature - Manual Testing Guide

## Prerequisites
1. Make sure migrations are applied: `make migrate`
2. Start the server: `make run`
3. Ensure WhatsApp number is configured in `.env`: `BANK_TRANSACTIONS_WHATSAPP_NUMBER=919328483009`
4. Gmail credentials should be set up (credentials.json and token.json)

## Testing Strategy

### 1. Test Email Parsing (Standalone)

Create a test script to verify parsers work correctly with your real emails:

```python
# test_parser.py
import asyncio
from app.integrations.gmail.service import GmailService
from app.modules.bank_transactions.parser import parse_bank_transaction_email
from app.core.config import config

async def test_email_parsing():
    gmail = GmailService(
        credentials_path=config.gmail_credentials_path,
        token_path=config.gmail_token_path
    )
    
    # Fetch recent emails
    emails = gmail.fetch_emails(max_results=20)
    
    print(f"\n📧 Found {len(emails)} emails\n")
    
    for email in emails:
        parsed = parse_bank_transaction_email(email)
        if parsed:
            print(f"✅ PARSED TRANSACTION:")
            print(f"   Bank: {parsed.bank}")
            print(f"   Amount: ₹{parsed.amount}")
            print(f"   Merchant: {parsed.merchant}")
            print(f"   Date: {parsed.transaction_date}")
            print(f"   From: {email.from_email}")
            print(f"   Subject: {email.subject}\n")

if __name__ == "__main__":
    asyncio.run(test_email_parsing())
```

Run: `python test_parser.py`

### 2. Test Manual Job Trigger

The easiest way to test the full flow without waiting for the scheduler:

**Option A: Via API Endpoint**
```bash
# Trigger the job manually
curl -X POST http://localhost:8001/bank-transactions/process
```

**Option B: Via Python Script**
```python
# test_job.py
import asyncio
from app.core.scheduler.jobs import process_bank_transaction_emails

async def run():
    result = await process_bank_transaction_emails()
    print(f"\n📊 Job Results:")
    print(f"   Processed: {result['processed']}")
    print(f"   Sent: {result['sent']}")
    print(f"   Errors: {result['errors']}")

if __name__ == "__main__":
    asyncio.run(run())
```

Run: `python test_job.py`

### 3. Test Full WhatsApp Flow (End-to-End)

#### Step 1: Trigger Transaction Detection
1. Run the manual job trigger (Option A or B above)
2. Check your WhatsApp for a message like:
   ```
   Hey! I noticed a transaction of ₹150.00 at NITISHA RAJEN MEHTA on 28 Feb 
   from your HDFC account.
   
   Should I log this as an expense? Just reply with yes or no 👍
   ```

#### Step 2: Test Confirmation Flow
Reply to the WhatsApp message with:
- "yes" or "haan" or "yep" → Should ask for category confirmation
- "no" or "nahi" or "skip" → Should dismiss the expense

#### Step 3: Test Category Confirmation
After saying yes, you should receive:
```
Cool! I think this ₹150.00 expense at NITISHA RAJEN MEHTA belongs to 
*Food & Dining > Restaurants*.

Does that sound right? Reply with yes, or tell me the correct category 😊
```

Reply with:
- "yes" → Creates expense with suggested category
- "groceries" → Re-classifies and creates expense

#### Step 4: Verify Database
Check that the expense was created:
```bash
# Connect to Turso and check
sqlite3 # or use Turso CLI

SELECT * FROM processed_bank_transactions ORDER BY created_at DESC LIMIT 5;
SELECT * FROM expenses ORDER BY created_at DESC LIMIT 5;
```

### 4. Test Scheduler (Automatic Polling)

The scheduler should run automatically every 5 minutes. To verify:

1. Check server logs for:
   ```
   💳 Bank transaction job scheduled every 5 minute(s)
   Starting bank transaction email processing job
   ```

2. Monitor the logs:
   ```bash
   tail -f # watch server output for scheduled runs
   ```

3. Check cache for pointer date:
   ```sql
   SELECT * FROM cache WHERE key = 'bank_transactions:last_processed_date';
   ```

### 5. Test Edge Cases

#### A. Already Processed Email
- Trigger the job twice
- Second run should skip already processed emails
- Check logs for: "Skipping already processed transaction"

#### B. Multiple Transactions
- If you have multiple unread bank emails
- All should be detected and sent to WhatsApp
- Each gets its own confirmation flow

#### C. Timeout/Expiry
- Wait 24 hours without responding
- Pending confirmation should expire from cache

#### D. Non-Bank Email
- Should be ignored by parser
- No WhatsApp message sent
- Check logs: "Not a recognized bank transaction email"

### 6. Test Different Banks

Send test emails or use existing ones:

**ICICI Test Pattern:**
- Subject: "Transaction alert for your ICICI Bank Credit Card"
- From: credit_cards@icicibank.com
- Amount: "transaction of INR X.XX"
- Merchant: "Info: MERCHANT_NAME"

**HDFC Test Pattern:**
- Subject: "You have done a UPI txn"
- From: alerts@hdfcbank.bank.in
- Amount: "Rs.X.XX has been debited"
- Merchant: "to VPA ... NAME"

### 7. Quick Debugging Checklist

If WhatsApp messages aren't arriving:
- [ ] Check `BANK_TRANSACTIONS_WHATSAPP_NUMBER` in .env
- [ ] Check WhatsApp service is working: `curl -X POST http://localhost:8001/whatsapp/send-text`
- [ ] Check Gmail auth: Run the email parsing test above
- [ ] Check logs for errors during job execution

If expenses aren't created:
- [ ] Check orchestrator logs for state handling
- [ ] Verify cache keys: `bank_transactions:pending:*` and `bank_transactions:category_suggestion:*`
- [ ] Check expense service isn't throwing errors

### 8. Production Testing Tips

Before going live:
1. Set scheduler interval to 10-15 minutes initially: `SCHEDULER_BANK_TRANSACTIONS_INTERVAL_MINUTES=15`
2. Monitor for 24 hours
3. Check false positives (non-expense emails being detected)
4. Adjust parser patterns if needed
5. Gradually reduce interval to 5 minutes

### 9. Monitoring Commands

```bash
# Check pending confirmations
SELECT * FROM cache WHERE key LIKE 'bank_transactions:pending:%';

# Check processed transactions
SELECT 
    bank, 
    amount, 
    merchant, 
    user_action, 
    whatsapp_sent,
    created_at 
FROM processed_bank_transactions 
ORDER BY created_at DESC 
LIMIT 20;

# Check expenses created from transactions
SELECT 
    e.amount,
    e.vendor,
    c.full_name as category,
    e.created_at
FROM expenses e
LEFT JOIN categories c ON e.category_id = c.id
WHERE e.note LIKE '%transaction%'
ORDER BY e.created_at DESC
LIMIT 20;
```

## Expected Flow Summary

1. **Email arrives** → Gmail inbox
2. **Scheduler runs** (every 5 min) → Fetches new emails
3. **Parser detects** → HDFC/ICICI transaction
4. **DB check** → Not already processed
5. **WhatsApp sent** → "Should I log this?"
6. **Cache stores** → Pending confirmation
7. **User replies "yes"** → Orchestrator catches it
8. **Category suggested** → Via LLM classifier
9. **User confirms** → "yes" or corrects
10. **Expense created** → Via existing service
11. **DB updated** → Transaction marked as confirmed
12. **Cache cleared** → Confirmation state removed

## Quick Test Sequence

```bash
# 1. Start server
make run

# 2. In another terminal, trigger job
curl -X POST http://localhost:8001/bank-transactions/process

# 3. Check WhatsApp on your phone

# 4. Reply to the message

# 5. Check database
# Connect and run: SELECT * FROM expenses ORDER BY created_at DESC LIMIT 1;

# 6. Verify in logs
# Look for: "✅ Got it! Logged ₹X.XX..."
```

That's it! The feature is working if you complete this sequence successfully.
