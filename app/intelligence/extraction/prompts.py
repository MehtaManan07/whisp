from datetime import datetime
from app.intelligence.intent.types import INTENT_TO_DTO, IntentType


def build_dto_prompt(message: str, intent: IntentType, user_id: int) -> str:
    request_dto = INTENT_TO_DTO[intent]
    schema = request_dto.model_json_schema()
    fields = schema.get("properties", {})
    required_fields = set(schema.get("required", []))
    defs = schema.get("$defs", {})

    def summarize_field(info):
        # Handle $ref to resolve enum definitions
        if "$ref" in info:
            ref_path = info["$ref"].split("/")[-1]  # Get the last part (e.g., "ReminderType")
            if ref_path in defs:
                ref_info = defs[ref_path]
                if "enum" in ref_info:
                    return f"constrained values: {ref_info['enum']}"
                # Recursively summarize the referenced definition
                return summarize_field(ref_info)
        
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
                    # Handle $ref in anyOf/oneOf
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
            if type_info and not all(isinstance(v, str) for v in constrained):
                return f"constrained values: {constrained} or {type_info}"
            return f"constrained values: {constrained}"
        elif type_info:
            return type_info
        return "unknown"

    dto_lines = []
    # Exclude category fields from prompt - let the category classifier handle categorization
    excluded_fields = {'category_name', 'subcategory_name'}
    
    for field, info in fields.items():
        if field in excluded_fields:
            continue  # Skip category fields - classifier will handle these
        desc = summarize_field(info)
        required_note = "required" if field in required_fields else "optional"
        dto_lines.append(f"- {field}: {desc} ({required_note})")

    dto_description = "\n".join(dto_lines)
    current_time = datetime.now().strftime("%A, %B %d, %Y at %I:%M %p")
    
    # Include examples if available
    examples = schema.get("examples", [])
    examples_text = ""
    if examples:
        import json
        examples_text = "\n\n### Examples:\n" + "\n".join(
            f"```json\n{json.dumps(ex, indent=2)}\n```" for ex in examples[:3]
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
- Do **NOT** attempt to categorize expenses
- All date-related fields must be parsed into **ISO 8601 datetime format** (e.g., `2025-08-24T00:00:00`). You might get a relative date, so you need to parse it and do the math yourself. Today's date and time is {current_time}.
- **CRITICAL**: Always include the `user_id` field in your JSON response with the value: {user_id}
- **IMPORTANT**: If recurrence_type is NOT "once", then recurrence_config MUST be provided with at least a "time" field (HH:MM format).

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
