from datetime import datetime
from app.intelligence.intent.types import INTENT_TO_DTO, IntentType


def build_dto_prompt(message: str, intent: IntentType, user_id: int) -> str:
    request_dto = INTENT_TO_DTO[intent]
    schema = request_dto.model_json_schema()
    fields = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    defs = schema.get("$defs", {})

    # --- Helper to summarize a field's type and constraints ---
    def summarize_field(info):
        # Handle $ref to resolve enum or nested definitions
        if "$ref" in info:
            ref_path = info["$ref"].split("/")[-1]
            if ref_path in defs:
                ref_info = defs[ref_path]
                if "enum" in ref_info:
                    return f"constrained values: {ref_info['enum']}"
                return summarize_field(ref_info)

        # Handle enums
        constrained = info.get("enum") or []
        if isinstance(constrained, (str, int)):
            constrained = [constrained]

        type_info = info.get("type")

        # Handle anyOf / oneOf / allOf (union types)
        for union_key in ["anyOf", "oneOf", "allOf"]:
            if union_key in info:
                types, values = [], []
                for option in info[union_key]:
                    if "$ref" in option:
                        ref_path = option["$ref"].split("/")[-1]
                        if ref_path in defs and "enum" in defs[ref_path]:
                            values += defs[ref_path]["enum"]
                    elif "enum" in option:
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
            return f"constrained values: {constrained}"
        elif type_info:
            return type_info
        return "unknown"

    # --- Helper to recursively extract field descriptions ---
    def describe_fields(properties: dict, required: set, parent: str = ""):
        lines = []
        for field, info in properties.items():
            # Skip category fields — handled separately
            if field in {"category_name", "subcategory_name"}:
                continue

            field_type = summarize_field(info)
            required_note = "required" if field in required else "optional"
            description = info.get("description", "No description provided")

            full_field = f"{parent}{field}"
            lines.append(
                f"- {full_field}: {field_type} ({required_note}) — {description}"
            )

            # Handle nested object schemas (e.g., recurrence_config)
            if info.get("type") == "object" and "properties" in info:
                nested_props = info["properties"]
                nested_required = set(info.get("required", []))
                nested_lines = describe_fields(
                    nested_props, nested_required, parent=f"{field}."
                )
                lines.extend(nested_lines)

        return lines

    dto_lines = describe_fields(fields, required_fields)
    dto_description = "\n".join(dto_lines)

    # --- Current time for relative parsing ---
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")

    # --- Include examples if available ---
    examples = schema.get("examples", [])
    examples_text = ""
    if examples:
        import json

        examples_text = "\n\n### Examples:\n" + "\n".join(
            f"```json\n{json.dumps(ex, indent=2)}\n```" for ex in examples[:3]
        )

    # --- Budget-specific guidance ---
    budget_guidance = ""
    if intent in [IntentType.SET_BUDGET, IntentType.UPDATE_BUDGET, IntentType.DELETE_BUDGET, IntentType.VIEW_BUDGET, IntentType.VIEW_BUDGET_PROGRESS]:
        budget_guidance = """
### Budget Extraction Guidance:
- **period**: Extract time period from keywords like "daily", "weekly", "monthly", "yearly". Default to "monthly" if not specified.
- **amount**: Extract numeric amount. Can be written as "50000", "50k", "50,000", etc.
- **category_name**: Extract category if mentioned (e.g., "food budget", "entertainment budget"). Set to null for overall budgets.
- **For UPDATE_BUDGET**: Extract budget_id from context or set to null if not explicitly mentioned.
- **For DELETE_BUDGET**: Extract budget_id from context or set to null if not explicitly mentioned.

### Examples:
- "set monthly budget to 50000" → {"user_id": 1, "period": "monthly", "amount": 50000, "category_name": null}
- "set 5000 food budget for this week" → {"user_id": 1, "period": "weekly", "amount": 5000, "category_name": "food"}
- "set daily budget of 2000" → {"user_id": 1, "period": "daily", "amount": 2000, "category_name": null}
- "show my food budget" → {"user_id": 1, "category_name": "food"}
- "what's my budget status" → {"user_id": 1}
"""

    # --- Final prompt string ---
    return f"""
You are an expert assistant that converts user messages into a JSON object that matches a predefined data structure (DTO).

### Your task:
- Strictly return a valid JSON object based on the DTO definition below.
- Do **NOT** add any fields that are not defined in the DTO.
- Only extract fields that are **explicitly stated** or **clearly implied** in the message (e.g., brand names, dates, or vendors).
- You may omit optional fields if the information is not available or implied.
- Do **NOT** guess or fabricate values.
- Do **NOT** include any explanation or text outside the JSON object.
- Do **NOT** attempt to categorize expenses
- All date-related fields must be parsed into **ISO 8601 datetime format** (e.g., `2025-08-24T00:00:00`). You might get a relative date, so you need to parse it and do the math yourself. Today's date and time is {current_time}.
- **CRITICAL**: Always include the `user_id` field in your JSON response with the value: {user_id}
- **IMPORTANT**: If recurrence_type is NOT "once", then recurrence_config MUST be provided with at least a "time" field (HH:MM format).
{budget_guidance}

---

### DTO: `{request_dto.__name__}`

Fields:
{dto_description}

### User Intent:
{intent.value}

### User Message:
{message}

### Provided Values:
- user_id: {user_id} (MUST be included in JSON)
{examples_text}

### Return only this:
A valid JSON object matching the `{request_dto.__name__}` DTO, including the user_id field.
"""
