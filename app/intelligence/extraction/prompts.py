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

    # --- Expense query guidance ---
    expense_query_guidance = ""
    if intent == IntentType.VIEW_EXPENSES:
        expense_query_guidance = """
### Expense Query Guidance:
- **CRITICAL**: Category/subcategory names (like "salon", "groceries", "food", "transport", etc.) should NEVER be put in the `note` field. Categories are handled separately by the system.
- **CRITICAL**: Do NOT include `category_name` or `subcategory_name` in output. They are resolved by a separate deterministic classifier.
- **note**: ONLY extract text as `note` when the user explicitly uses phrases like "with note", "note says", "note containing", or "notes about".
- When a user says "show me X expenses" where X is a category/subcategory name, do NOT put X in the note field - leave note as null.
- **Examples**:
  - "show me all salon expenses" → {"user_id": 1} (note: null, categories handled separately)
  - "show grocery expenses" → {"user_id": 1} (note: null, categories handled separately)
  - "show me all food expenses in last 5 days" → {"user_id": 1, "start_date": "...", "end_date": "..."} (note: null, categories handled separately)
  - "show expenses with note 'dinner'" → {"user_id": 1, "note": "dinner"}
  - "find expenses where note contains uber" → {"user_id": 1, "note": "uber"}
  - "expenses with note about birthday gift" → {"user_id": 1, "note": "birthday gift"}
  - "show food expenses with note lunch meeting" → {"user_id": 1, "note": "lunch meeting"} (note explicitly mentioned)
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
{expense_query_guidance}

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
