from datetime import datetime, timedelta

from app.agents.intent_classifier.types import INTENT_TO_DTO, IntentType


def build_intent_prompt(message: str) -> str:
    intents = ",".join([f"{intent.value}" for intent in IntentType])
    return f"""

You are an expert mastermind assistant that classifies user requests into one of the following intents:
{intents}

Strictly return a JSON with the "intent" field. Do not guess parameters.
For example, if the user says "I spent 500 on groceries today.", the response should be:
{{"intent": "log_expense"}}

Here is the user message:
{message}
    """


def build_dto_prompt(message: str, intent: IntentType, user_id: int) -> str:
    request_dto = INTENT_TO_DTO[intent]
    schema = request_dto.model_json_schema()
    fields = schema["properties"]
    required_fields = schema.get("required", [])

    dto_fields_description = "\n".join(
        [
            f"- {field}: {info.get('type', 'unknown')}"
            + (" (required)" if field in required_fields else " (optional)")
            for field, info in fields.items()
        ]
    )

    return f"""
You are an expert assistant that converts user messages into a JSON object that matches a predefined data structure (DTO).

### Your task:
- Strictly return a valid JSON object based on the DTO definition below.
- Do **NOT** add any fields that are not defined in the DTO.
- Only extract fields that are **explicitly stated** or **clearly implied** in the message (e.g., brand names, dates, or vendors).
- You may omit optional fields if the information is not available or implied.
- Do **NOT** guess or fabricate values.
- Do **NOT** include any explanation or text outside the JSON object.
- All date-related fields must be parsed into **ISO 8601 datetime format** (e.g., `2025-08-24T00:00:00`). You might get a relative date, so you need to parse it and do the math yourself. Today's date and time is {datetime.now().strftime('%A, %B %d, %Y at %I:%M %p')}.
- Always include the provided `user_id` value.

---

### DTO: `{request_dto.__name__}`

Fields:
{dto_fields_description}

### User Intent:
{intent.value}

### User Message:
{message}

### Provided Values:
- user_id: {user_id}

### Return only this:
A valid JSON object matching the `{request_dto.__name__}` DTO.
"""
