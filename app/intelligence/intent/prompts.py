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
    # Budget management
    r"\b(budget|limit|max|cap)\b.*\d+": "SET_BUDGET",
    r"\d+.*\b(budget|limit|max|cap)\b": "SET_BUDGET",
    r"\b(limit|max|cap)\b.*\b(on|for)\b": "SET_BUDGET",
    r"\b(remove|delete|cancel|stop|disable)\b.*\bbudget": "DELETE_BUDGET",
    r"\bbudget\b.*(remove|delete|cancel|stop)": "DELETE_BUDGET",
    r"\b(remove|delete|cancel)\b.*\b(limit|cap)\b": "DELETE_BUDGET",
    r"\b(clear|reset)\b.*\bbudget": "DELETE_BUDGET",
    r"\b(show|view|list|check|see|what)\b.*\bbudget": "VIEW_BUDGETS",
    r"\bbudget\b.*(show|view|list|check)": "VIEW_BUDGETS",
    r"\bwhat.*(limit|cap|budget)": "VIEW_BUDGETS",
    r"\b(my|the)\s+budget": "VIEW_BUDGETS",
    # Insights / reports (check BEFORE general view_expenses)
    r"\b(insight|report|analysis|pattern|trend|overview|breakdown)\b": "GET_INSIGHTS",
    r"\bhow did i spend\b": "GET_INSIGHTS",
    r"\bwhere.*(money|spend|penny|rupee).*go": "GET_INSIGHTS",
    r"\b(weekly|monthly)\s+(report|summary|recap)\b": "GET_INSIGHTS",
    r"\bspending\s+(pattern|habit|trend|summary)\b": "GET_INSIGHTS",
    r"\bcompare.*(month|week)\b": "GET_INSIGHTS",
    # Queries - second most common (20-30%)
    r"\b(how much|total|show|list|view|display)\b.*(expense|spending|spent)": "VIEW_EXPENSES",
    r"\b(spending|spent).*\b(this|last|current)\s+(week|month|year)": "VIEW_EXPENSES",
    # Goals
    r"\b(set|create)\s+(a\s+)?goal\b": "SET_GOAL",
    r"\b(view|show|check)\s+(my\s+)?goals?\b": "VIEW_GOALS",
    # Workout logging (fitness) — set notation & session keywords
    r"\blogged with hevy\b": "LOG_WORKOUT",
    r"\d+\s*kg\s*[x×]\s*\d+": "LOG_WORKOUT",
    r"\b(did|logged|trained|finished|completed|smashed)\b.*\b(workout|leg day|legs|push day|pull day|upper( body)?|lower( body)?|chest( day)?|back( day)?|shoulders?|arm day|gym session)\b": "LOG_WORKOUT",
    r"\b(squat|bench|deadlift|overhead press|ohp|lat pulldown|pulldown|row|curl|lunge|leg press|hip thrust|calf raise|dip)\b.*\d+\s*[x×]\s*\d+": "LOG_WORKOUT",
    # Workout viewing (fitness)
    r"\b(show|view|list|see|check|last|recent)\b.*\b(workout|workouts|leg day|training session|gym session|lifting session)\b": "VIEW_WORKOUTS",
    r"\b(workout|training)\s+(history|log|sessions?|record)\b": "VIEW_WORKOUTS",
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
"How did I spend this week?" → {{"intent": "get_insights"}}
"Monthly summary" → {{"intent": "get_insights"}}
"Compare this month vs last month" → {{"intent": "get_insights"}}
"Where is my money going?" → {{"intent": "get_insights"}}
"Show me my spending patterns" → {{"intent": "get_insights"}}
"Set a budget of 5000 for food per month" → {{"intent": "set_budget"}}
"Max 3k on restaurants weekly" → {{"intent": "set_budget"}}
"Limit food delivery to 5000" → {{"intent": "set_budget"}}
"Show my budgets" → {{"intent": "view_budgets"}}
"What are my spending limits?" → {{"intent": "view_budgets"}}
"Remove food budget" → {{"intent": "delete_budget"}}
"Delete my transport limit" → {{"intent": "delete_budget"}}
"Did legs today - squat 35x8, 35x8, 35x9 and leg curls" → {{"intent": "log_workout"}}
"Logged with Hevy. Squat (Barbell) 35 kg x 8" → {{"intent": "log_workout"}}
"Just finished upper A, bench 40x8, 40x7" → {{"intent": "log_workout"}}
"Show my last leg workout" → {{"intent": "view_workouts"}}
"What did I do last chest day?" → {{"intent": "view_workouts"}}
"My workout history" → {{"intent": "view_workouts"}}

User message:
{message}
    """
