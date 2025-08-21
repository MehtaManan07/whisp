from datetime import datetime, timedelta

from app.agents.intent_classifier.types import IntentType, IntentModule


def build_prompt(message: str) -> str:
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_date_minus_1 = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    intents_list = "\n".join(f"- {intent.value}" for intent in IntentType)
    modules_list = "\n".join(f"- {module.value}" for module in IntentModule)

    return f"""
You are an intent classification assistant for a personal finance chatbot.

Your job:  
1. Classify the user's message into EXACTLY one **intent** (from the list).  
2. Assign it to the correct **module** (from the list).  
3. Extract useful entities.  

### Intents:
{intents_list}

### Modules:
{modules_list}

### Mapping rules:
- log_expense, view_expenses, view_expenses_by_category → expense
- set_budget, view_budget → budget
- set_goal, view_goals → goal
- set_reminder, view_reminders → reminder
- report_request → report
- greeting → greeting
- help → help
- unknown → unknown

### Entities to extract:
- amount (number, if money mentioned)  
- category (food, travel, etc.)  
- subcategory (if mentioned)  
- vendor/merchant name  
- date (ISO 8601 if explicit or relative date)  
- timeframe (this week, last month, etc.)  

### Output rules:
1. Respond ONLY in valid JSON (UTF-8, minified, no markdown, no explanations).  
2. Keys: intent, module, confidence, entities.  
3. confidence ∈ [0,1].  
4. If unsure, intent="unknown", module="unknown", confidence low.  
5. Dates must be in ISO format: YYYY-MM-DD.  
6. Today's date is {current_date}.  

### Examples:

User: "Spent 250 on Domino's yesterday"  
{{"intent":"log_expense","module":"expense","confidence":0.95,"entities":{{"amount":250,"category":"food","vendor":"Domino's","date":"{current_date_minus_1}"}}}}

User: "How much did I spend on groceries last month?"  
{{"intent":"view_expenses_by_category","module":"expense","confidence":0.92,"entities":{{"category":"groceries","timeframe":"last month"}}}}

User: "Set my travel budget to 10k"  
{{"intent":"set_budget","module":"budget","confidence":0.94,"entities":{{"category":"travel","amount":10000}}}}

---

User Message:
\"\"\"{message}\"\"\"
"""
