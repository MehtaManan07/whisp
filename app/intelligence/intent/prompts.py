from app.intelligence.intent.types import IntentType


INTENT_PATTERNS = {
    # Expense logging - most common (60-70% of messages)
    # More flexible pattern that handles both orders
    r"(\b(spent|paid|bought|cost|purchase|expense|bill)\b.*\d+|\d+.*\b(spent|paid|bought|cost|purchase|expense|bill)\b)": "LOG_EXPENSE",
    r"\b(spent|paid|bought|cost|purchase|expense|bill)\b.*\d+": "LOG_EXPENSE",
    # Queries - second most common (20-30%)
    r"\b(how much|total|show|list|view|display)\b": "VIEW_EXPENSES",
    r"\b(spending|spent).*\b(this|last|current)\s+(week|month|year)": "VIEW_EXPENSES",
    # Budget management
    r"\b(set|create|add|make)\s+(a\s+)?budget\b": "SET_BUDGET",
    r"\b(check|view|show|get)\s+(my\s+)?budget": "VIEW_BUDGET",
    # Goals
    r"\b(set|create)\s+(a\s+)?goal\b": "SET_GOAL",
    r"\b(view|show|check)\s+(my\s+)?goals?\b": "VIEW_GOALS",
    # Reminders
    r"\bremind\s+me\b": "SET_REMINDER",
    # Commands (instant classification)
    r"^/help": "HELP",
    r"^/report": "REPORT",
    r"^/list": "VIEW_EXPENSES",
}


def build_intent_prompt(message: str) -> str:
    intents = ",".join([f"{intent.value}" for intent in IntentType])
    return f"""
You are an expert assistant that classifies user requests into one of the following intents:
{intents}

Rules:
- Always return a JSON object with exactly one key: "intent".
- Pick the **closest matching intent**. Do not use "unknown" unless the message is clearly unrelated (e.g., casual chat).
- Do not infer parameters, only the intent.

Examples:
"I spent 500 on groceries today." → {{"intent": "log_expense"}}
"Show me my expenses for last week." → {{"intent": "view_expenses"}}
"Set my food budget to 10000." → {{"intent": "set_budget"}}
"Remind me to pay rent on 1st." → {{"intent": "set_reminder"}}

User message:
{message}
    """
