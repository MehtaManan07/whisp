# Whisp — Feature Roadmap

Vision: A personal financial intelligence system that learns your spending nature,
proactively helps you save, and keeps you on track toward financial goals.
Interface: WhatsApp.

---

## Phase 1: Know Where Your Money Goes

### Weekly & Monthly Reports
- [x] Weekly spending summary auto-sent every Sunday night via WhatsApp
- [x] Monthly report on the 1st of each month
- [x] Category-wise breakdown with amounts and transaction counts
- [x] Comparison vs previous period (week-over-week, month-over-month)
- [x] Top vendors by frequency and spend
- [x] Day-of-week and time-of-day patterns
- [x] On-demand: "how did I spend this week/month" via chat

### Better Insights (on-demand)
- [ ] "How much did I spend on X?" — natural language queries
- [x] "Compare this month vs last month"
- [x] "What's my average daily spend?"
- [ ] Trend detection: "Your restaurant spending is up 40% this month"

---

## Phase 2: Set Limits, Get Warned

### Budget Limits & Alerts
- [ ] Set budget per category: "max 5k on restaurants this month"
- [ ] Set overall monthly budget
- [ ] Alert at 50%, 80%, 100% of budget via WhatsApp
- [ ] Daily/weekly budget pacing: "You've used 60% of your food budget and we're only halfway through the month"
- [ ] Budget rollover or reset options (monthly)

### Spending Pattern Alerts (Proactive)
- [ ] Detect unusual spending velocity: "3.2k on Swiggy in 8 days, 2x your usual"
- [ ] Weekend splurge detection
- [ ] Frequency alerts: "4th Rapido ride today"
- [ ] High-amount outlier detection for a category

---

## Phase 3: Stop Impulsive Spending

### Smart Nudges
- [ ] When logging an expense in a high-frequency category, nudge: "That's your Nth order this week"
- [ ] When a single expense exceeds category average by 2x+, flag it
- [ ] Cool-down suggestions: "You've been ordering Swiggy daily — try cooking tonight?"
- [ ] Weekly impulse score: how much of your spend was habitual vs planned

### Spending Friction (opt-in)
- [ ] "Confirm before logging" mode for specific categories
- [ ] 24-hour expense regret check: "You logged 2k at Zara yesterday — still feel good about it?"

---

## Phase 4: Financial Goals

### Goal Tracking
- [ ] Create goals: "Save 50k for a watch by August"
- [ ] Track surplus each month (income - expenses)
- [ ] Goal progress updates: "You're 35% there, on track to hit it by July"
- [ ] Goal at risk alerts: "At current pace, you'll miss your bike fund by 2 months"
- [ ] Multiple concurrent goals with priority

### Income Tracking
- [ ] Log income/salary
- [ ] Net savings calculation: income - total expenses
- [ ] Savings rate tracking over time

---

## Phase 5: Learn & Predict

### Spending Intelligence
- [ ] Monthly spending forecast based on historical patterns
- [ ] Recurring expense detection (rent, subscriptions, insurance)
- [ ] Auto-tag recurring vs one-time expenses
- [ ] "If you cut Swiggy by half, you'd save 2.5k/month"
- [ ] Personalized saving tips based on actual data

### Category Intelligence
- [ ] Auto-suggest better categories based on past behavior
- [ ] Merge/split category suggestions
- [ ] "Uncategorized" cleanup prompts

---

## Infrastructure (build as needed)

- [x] Scheduled WhatsApp message delivery (for reports, alerts, nudges)
- [x] Analytics query layer (reusable aggregations over expenses)
- [ ] User preferences store (budgets, goals, notification settings)
- [ ] LLM-powered insight generation (natural language summaries of data)
