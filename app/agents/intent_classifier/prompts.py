from datetime import datetime

from app.agents.intent_classifier.types import INTENT_TO_DTO, IntentType


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


def build_dto_prompt(message: str, intent: IntentType, user_id: int) -> str:
    request_dto = INTENT_TO_DTO[intent]
    schema = request_dto.model_json_schema()
    fields = schema.get("properties", {})
    required_fields = set(schema.get("required", []))

    def summarize_field(info):
        # Handle constrained values (like enum)
        constrained = info.get("enum") or []
        if isinstance(constrained, (str, int)):
            constrained = [constrained]

        type_info = info.get("type")

        # Handle combined types (e.g., oneOf, anyOf, etc.)
        for union_key in ["anyOf", "oneOf", "allOf"]:
            if union_key in info:
                types = []
                values = []
                for option in info[union_key]:
                    if "enum" in option:
                        values += option["enum"]
                    elif "type" in option:
                        types.append(option["type"])
                values = list(dict.fromkeys(values))
                types = list(dict.fromkeys(types))
                if values:
                    constrained = values
                if types:
                    type_info = " / ".join(types)

        if constrained:
            if type_info and not all(isinstance(v, str) for v in constrained):
                return f"constrained values: {constrained} or {type_info}"
            return f"constrained values: {constrained}"
        elif type_info:
            return type_info
        return "unknown"

    dto_lines = []
    for field, info in fields.items():
        desc = summarize_field(info)
        required_note = "required" if field in required_fields else "optional"
        dto_lines.append(f"- {field}: {desc} ({required_note})")

    dto_description = "\n".join(dto_lines)
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    return f"""
You are an expert assistant that converts user messages into a JSON object that matches a predefined data structure (DTO).

### Your task:
- Strictly return a valid JSON object based on the DTO definition below.
- Do **NOT** add any fields that are not defined in the DTO.
- Only extract fields that are **explicitly stated** or **clearly implied** in the message (e.g., brand names, dates, or vendors).
- You may omit optional fields if the information is not available or implied.
- Do **NOT** guess or fabricate values.
- Do **NOT** include any explanation or text outside the JSON object.
- All date-related fields must be parsed into **ISO 8601 datetime format** (e.g., `2025-08-24T00:00:00`). You might get a relative date, so you need to parse it and do the math yourself. Today's date and time is {current_time}.
- Always include the provided `user_id` value.

---

### DTO: `{request_dto.__name__}`

Fields:
{dto_description}

### User Intent:
{intent.value}

### User Message:
{message}

### Provided Values:
- user_id: {user_id}

### Return only this:
A valid JSON object matching the `{request_dto.__name__}` DTO.
"""
