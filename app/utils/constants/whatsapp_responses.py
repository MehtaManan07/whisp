class HELP_MESSAGES:
    @staticmethod
    def help(name: str) -> str:
        return f"""
👋 Hey {name}! I'm your personal finance assistant. Here’s what I can help you with:

💸 *Expense Tracking*
- Log an expense: `Spent 250 on groceries`
- View recent expenses: `/expenses`
- View today's summary: `/today`
- Monthly summary: `/month`

📊 *Budgets*
- Set a budget: `/budget Food 5000`
- View budgets: `/budgets`
- Edit a budget: `/editbudget Food 6000`

🎯 *Goals & Saving*
- Set a goal: `/goal Save 20000 by December`
- View goals: `/goals`

⏰ *Reminders*
- Set a reminder: `/remind Pay rent on 1st`
- View all reminders: `/reminders`

🔍 *Insights & Analysis*
- Ask: `How much did I spend on food last week?`
- Compare months: `Compare June and July`

📚 *Financial Help*
- Ask anything: `What’s an ELSS fund?`
- Tax help: `How can I save tax as a freelancer?`

🛠️ *Settings & Help*
- `/help` – Show this menu
- `/export` – Export your data
- `/reset` – Clear all my data
- `/feedback` – Send feedback

---

Tip: You can also just *type naturally!* Try:
➡️ "Did I spend more on eating out this month?"
➡️ "Remind me to check my credit card bill"


"""
