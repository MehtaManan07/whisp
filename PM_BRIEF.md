# Whisp - Product Brief for PM Review

## What It Is
**Whisp** = AI expense tracker that lives in WhatsApp. Users text naturally ("spent ₹500 on groceries") and it logs, categorizes, and helps them understand their spending. No app install required.

---

## Current State

### What Users Can Do
1. **Log expenses conversationally**: "bought coffee for 150" → auto-categorized, timestamped, saved
2. **Query their spending**: "show my expenses this week" → formatted breakdown with totals
3. **Set reminders**: "remind me to pay rent on 1st" → recurring WhatsApp notifications

### Tech Stack (In Production)
- FastAPI backend + PostgreSQL + Redis cache
- WhatsApp Business API for messaging
- Hybrid AI: 90% rule-based/cached (free), 10% LLM (DeepSeek/Groq via OpenRouter)
- Celery for scheduled reminders

### The Intelligence
**3-tier classification system** that keeps costs near-zero:
- Tier 1: Regex patterns (instant) → "zomato" = Food & Dining > Restaurants
- Tier 2: User learning (cached) → Remembers YOUR vendors
- Tier 3: LLM fallback (rare) → Handles complex/new cases

**Key metric:** 90%+ requests avoid LLM calls through smart caching and rules.

### Data Captured
- **Expenses**: amount, vendor, category/subcategory, timestamp, notes
- **Categories**: 10 main (Food, Transport, Shopping, etc.) + 50 subcategories
- **Users**: WhatsApp ID, timezone (auto-detected), engagement streak
- **Reminders**: recurring bills, custom reminders, timezone-aware delivery

### What's Actually Working
✅ Zero friction UX (no app install, 1.5B WhatsApp users accessible)
✅ Natural language processing for expenses
✅ Smart cost optimization (free tier LLMs)
✅ Production deployment with real users
✅ Timezone-aware global support
✅ Learns from user patterns

---

## What's Missing/Weak

### Technical Gaps
- No receipt OCR (can't process images)
- No voice message support
- No web dashboard/visualization
- No export (CSV, Excel, accounting tools)
- No group expense splitting
- WhatsApp-only (platform risk)

### Product Gaps
- **No monetization model**
- **No retention loops** (beyond reminders)
- **No onboarding flow** (users must discover features)
- No budgets (intent exists, not built)
- No financial goals/insights
- No virality/sharing mechanics
- No bank integration/auto-import

### The Real Problems
1. **Is this a vitamin or painkiller?** Expense tracking has notoriously poor retention
2. **Value proposition unclear**: "Convenient logging" ≠ financial outcome
3. **No defensibility**: OpenAI could ship this tomorrow
4. **Engagement**: Why would someone use this daily?
5. **WhatsApp lock-in**: One API change = dead product

---

## Market Context

**Target:** Young professionals (20-35), India/developing markets, WhatsApp power users

**Competitors:**
- Mint/YNAB: Feature-rich but heavy, require app install + bank linking
- Splitwise: Group-focused, not personal finance
- Banking apps: Slow, bank-specific
- Spreadsheets: Manual, no intelligence

**Whisp's angle:** Lowest friction expense tracking that exists. But is that enough?

---

## Evolution Timeline
Started July 2025, iterated heavily:
- Added/removed budgets (July)
- Rethought categories (Aug)
- Removed/re-added reminders (Oct)
- Added timezone support (Oct)

**Shows:** Active development but also searching for product-market fit.

---

## Your Mission

You're an **expert product manager**. Be **BRUTALLY CRITICAL**.

### Answer These Questions:

1. **Honest Assessment**: What's the real value here? Is this solving a meaningful problem?

2. **Product Vision**: What could this become that would make it truly exceptional? Not incremental features - what's the transformation?

3. **The Core Problem**: What financial outcome should Whisp guarantee? "Convenient tracking" isn't enough.

4. **Defensibility**: How do we build a moat against big tech? Network effects? Data moat? Something else?

5. **Monetization**: How does this make money without killing the UX? Be specific.

6. **Retention Loops**: Why would users engage daily/weekly? What's the habit formation mechanism?

7. **Critical Features**: What 3 features would 10x the value? Prioritize ruthlessly.

8. **Target User**: Who specifically should we serve? (Hint: "everyone" is wrong)

9. **Success Metrics**: What KPIs matter? What numbers = success?

10. **Risks**: What kills this product? How do we mitigate?

---

## What I Want From You

A **concise product strategy** with:

1. **Critical Take** (2-3 paragraphs): What's working, what's not, what's the biggest issue?

2. **Product Vision** (1 paragraph): What does this become at its best?

3. **Value Proposition** (1 sentence): [Target user] can [achieve outcome] by [key differentiator]

4. **The Moat** (bullet points): 3 ways to make this defensible

5. **Monetization Model** (brief): How we make money

6. **Retention Strategy** (brief): How we keep users engaged

7. **Next 3 Features** (prioritized): What to build next and why

8. **Success Metrics**: Top 3 KPIs to track

9. **Biggest Risk + Mitigation**: What's most likely to kill this?

---

**Tone:** Be honest, even harsh. Challenge every assumption. I want this to be my best side project ever - that means excellence, not comfort.

