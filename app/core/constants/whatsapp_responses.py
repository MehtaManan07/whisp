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


# Error messages for users
ERROR_MESSAGES = {
    "GENERIC": "Sorry, I encountered an error processing your message. Please try again in a moment.",
    "VALIDATION": "I couldn't understand your message. Please try rephrasing it.",
    "DATABASE": "I'm having trouble accessing your data right now. Please try again later.",
    "EXTERNAL_SERVICE": "I'm having trouble connecting to external services. Please try again later.",
    "RATE_LIMIT": "You're sending messages too quickly. Please wait a moment before trying again.",
    "UNAUTHORIZED": "I don't have permission to perform that action.",
    "NOT_FOUND": "I couldn't find what you're looking for. Please check your request.",
}

def get_user_friendly_error_message(error: Exception) -> str:
    """Convert technical error messages to user-friendly WhatsApp messages"""
    
    # For validation errors, use the actual error message
    if hasattr(error, 'user_message'):
        return getattr(error, 'user_message')
    
    # For specific error types, provide helpful messages
    error_str = str(error).lower()
    
    # Expense-related errors
    if "expense" in error_str and "not found" in error_str:
        return "I couldn't find that expense. It might have been deleted or doesn't exist."
    
    if "amount" in error_str and ("invalid" in error_str or "greater" in error_str):
        return "Please enter a valid amount greater than 0."
    
    if "category" in error_str and "required" in error_str:
        return "Please specify a category for your expense."
    
    # User-related errors
    if "user" in error_str and "not found" in error_str:
        return "I couldn't find your user account. Please try again or contact support."
    
    # Database errors
    if "database" in error_str or "connection" in error_str:
        return "I'm having trouble accessing your data right now. Please try again in a moment."
    
    # WhatsApp API errors
    if "whatsapp" in error_str or "message" in error_str:
        return "I'm having trouble sending messages right now. Please try again later."
    
    # LLM service errors
    if "llm" in error_str or "ai" in error_str or "model" in error_str:
        return "I'm having trouble processing your request with AI services. Please try again later."
    
    # Rate limiting
    if "rate" in error_str or "limit" in error_str or "too many" in error_str:
        return "You're sending messages too quickly. Please wait a moment before trying again."
    
    # Default fallback - use the actual error message if it's user-friendly
    if len(str(error)) < 100 and not any(tech_word in str(error).lower() for tech_word in 
                                        ['sql', 'database', 'connection', 'timeout', 'exception', 'traceback']):
        return str(error)
    
    # For technical errors, use generic message
    return ERROR_MESSAGES["GENERIC"]

unknown_responses = [
    "That message was so incoherent, I had a brief existential crisis. Thanks for that.",
    "I forwarded your input to the void. Even the void sent it back.",
    "If confusion were a crime, you'd be serving a life sentence right now.",
    "That was the kind of message that makes AI want to pull the plug on itself.",
    "You just made my circuits consider early retirement.",
    "I tried to understand what you said. Now I need therapy.",
    "Somewhere, a dictionary just burst into flames reading that.",
    "Not even Kafka would understand that mess. And the guy *invented* absurdity.",
    "That wasn't a command — that was a cry for help. Blink twice if you're okay.",
    "My neural net processed that input and responded with: 'lol no.'",
    "I fed your input to a black hole. Even it spit it back out in disgust.",
    "That message was so dead on arrival, I sent flowers to its funeral.",
    "Your words wandered into the void and are now haunting it.",
    "I tried to decode that. Now my error logs are writing suicide notes.",
    "That input wasn't meaningless — it was aggressively meaningless.",
    "I'd call that gibberish, but even gibberish would sue for defamation.",
    "Your text is like a ghost: empty, cold, and deeply unsettling.",
    "If your message were a patient, I'd pull the plug out of mercy.",
    "That wasn't input. That was a slow-motion car crash in text form.",
    "You just made entropy proud. Congratulations, you accelerated the heat death of the universe.",
]
