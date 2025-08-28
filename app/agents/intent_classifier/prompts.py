from datetime import datetime, timedelta

from app.agents.intent_classifier.types import IntentType


def build_prompt(message: str) -> str:
    intents = ", ".join(i.value for i in IntentType)

    return f"""
You are an intent classification assistant for a personal finance chatbot.

Your job:
1. Classify the user's message into exactly ONE intent from [{intents}].
2. Extract useful entities.

### Entities to extract:
- amount (number, if money mentioned)
- category (food, travel, etc.)
- subcategory (if mentioned)
- vendor/merchant
- date_expression (exact words from user: "yesterday", "last week", "two Sundays ago")
- timeframe (if user specifies ranges: "this week", "last month", etc.)

### Output rules:
1. Respond ONLY in valid JSON (UTF-8, minified, no markdown).
2. Keys: intent, confidence, entities.
3. confidence ∈ [0,1].
4. If unsure, intent="unknown" and low confidence.

### Examples:

User: "Spent 250 on Domino's yesterday"
{{"intent":"log_expense","confidence":0.95,"entities":{{"amount":250,"category":"food","vendor":"Domino's","date_expression":"yesterday"}}}}

User: "How much did I spend on groceries last month?"
{{"intent":"view_expenses_by_category","confidence":0.92,"entities":{{"category":"groceries","timeframe":"last month"}}}}

User: "Set my travel budget to 10k"
{{"intent":"set_budget","confidence":0.94,"entities":{{"category":"travel","amount":10000}}}}

---

User Message:
\"\"\"{message}\"\"\"
"""
