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


unknown_responses = [
    "That message was so incoherent, I had a brief existential crisis. Thanks for that.",
    "I forwarded your input to the void. Even the void sent it back.",
    "If confusion were a crime, you'd be serving a life sentence right now.",
    "That was the kind of message that makes AI want to pull the plug on itself.",
    "You just made my circuits consider early retirement.",
    "I tried to understand what you said. Now I need therapy.",
    "Somewhere, a dictionary just burst into flames reading that.",
    "Not even Kafka would understand that mess. And the guy *invented* absurdity.",
    "That wasn’t a command — that was a cry for help. Blink twice if you're okay.",
    "My neural net processed that input and responded with: 'lol no.'",
    "I fed your input to a black hole. Even it spit it back out in disgust.",
    "That message was so dead on arrival, I sent flowers to its funeral.",
    "Your words wandered into the void and are now haunting it.",
    "I tried to decode that. Now my error logs are writing suicide notes.",
    "That input wasn’t meaningless — it was aggressively meaningless.",
    "I’d call that gibberish, but even gibberish would sue for defamation.",
    "Your text is like a ghost: empty, cold, and deeply unsettling.",
    "If your message were a patient, I’d pull the plug out of mercy.",
    "That wasn’t input. That was a slow-motion car crash in text form.",
    "You just made entropy proud. Congratulations, you accelerated the heat death of the universe.",
]
