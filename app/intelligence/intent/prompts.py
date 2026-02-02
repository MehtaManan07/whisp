from app.intelligence.intent.types import IntentType


INTENT_PATTERNS = {
    # Expense logging - most common (60-70% of messages)
    # More flexible pattern that handles both orders
    r"(\b(spent|paid|bought|cost|purchase|expense|bill)\b.*\d+|\d+.*\b(spent|paid|bought|cost|purchase|expense|bill)\b)": "LOG_EXPENSE",
    r"\b(spent|paid|bought|cost|purchase|expense|bill)\b.*\d+": "LOG_EXPENSE",
    # Expense correction - check before other expense patterns
    r"\b(change|correct|fix|update|wrong)\b.*\b(category|categor)": "CORRECT_EXPENSE",
    r"\b(should\s+be|actually|no,?\s+it'?s?|that'?s?\s+wrong)\b.*\b(category|categor)": "CORRECT_EXPENSE",
    r"\b(no|wrong|incorrect)\b.*\b(this\s+is|it'?s?|should\s+be)\b": "CORRECT_EXPENSE",
    # Reminder actions - check FIRST (most specific)
    r"\b(done|completed?|finished|mark\s+complete)\b": "COMPLETE_REMINDER",
    r"\bsnooze\s*(\d+\s*(h|hour|hours?|m|min|minutes?))?\b": "SNOOZE_REMINDER",
    # Reminders - check BEFORE general queries (more specific patterns first)
    r"\b(show|list|view|display|get|check|see)\b.*(my\s+)?reminders?\b": "VIEW_REMINDERS",
    r"\breminders?\b.*(show|list|view|display)": "VIEW_REMINDERS",
    r"\bremind\s+me\b": "SET_REMINDER",
    # Queries - second most common (20-30%)
    r"\b(how much|total|show|list|view|display)\b.*(expense|spending|spent)": "VIEW_EXPENSES",
    r"\b(spending|spent).*\b(this|last|current)\s+(week|month|year)": "VIEW_EXPENSES",
    # Goals
    r"\b(set|create)\s+(a\s+)?goal\b": "SET_GOAL",
    r"\b(view|show|check)\s+(my\s+)?goals?\b": "VIEW_GOALS",
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
"Change category to Business" → {{"intent": "correct_expense"}}
"No, that's wrong. It should be Entertainment" → {{"intent": "correct_expense"}}
"Remind me to pay rent on 1st." → {{"intent": "set_reminder"}}
"Show me all my reminders." → {{"intent": "view_reminders"}}

User message:
{message}
    """
