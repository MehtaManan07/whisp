import json
from app.integrations.llm.service import LLMService
from app.intelligence.categorization.classifier import CategoryClassifier
from app.intelligence.extraction.prompts import build_dto_prompt
from app.intelligence.intent.types import DTO_UNION, INTENT_TO_DTO, IntentType
from app.modules.expenses.dto import CreateExpenseModel, GetAllExpensesModel


async def extract_dto(
    message: str,
    intent: IntentType,
    user_id: int,
    llm_service: LLMService,
    category_classifier: CategoryClassifier,
) -> DTO_UNION:
    """
    Extract structured data from user message based on intent.
    
    Args:
        message: The user's message text
        intent: The classified intent type
        user_id: The user's ID
        llm_service: LLM service instance for extraction
        category_classifier: Category classifier for expense categorization
        
    Returns:
        Structured DTO instance based on the intent
    """
    prompt = build_dto_prompt(message, intent, user_id)
    extraction_response = await llm_service.complete(
        prompt=prompt,
        temperature=0,
        call_stack="extraction",
    )
    parsed_dto = json.loads(extraction_response.content)

    # Ensure user_id is always included in the parsed data
    parsed_dto["user_id"] = user_id

    # Create DTO instance from LLM extraction
    dto_instance = INTENT_TO_DTO[intent](**parsed_dto)

    # Transaction category classification is only for log-expense flow.
    if intent == IntentType.LOG_EXPENSE and isinstance(dto_instance, CreateExpenseModel):
        classification_result = await category_classifier.classify(
            original_message=message, dto_instance=dto_instance, user_id=user_id
        )

        dto_instance.category_name = classification_result["category"]
        dto_instance.subcategory_name = classification_result["subcategory"]
        dto_instance.classification_confidence = classification_result.get("confidence")
        dto_instance.classification_method = classification_result.get("method")
        dto_instance.classification_reasoning = classification_result.get("reasoning")

    # Query filter classification uses deterministic-first pipeline and
    # keeps category/subcategory as separate confidence decisions.
    if intent == IntentType.VIEW_EXPENSES and isinstance(dto_instance, GetAllExpensesModel):
        query_filter_result = await category_classifier.classify_query_filters(
            message=message,
            vendor=dto_instance.vendor,
        )
        dto_instance.category_name = query_filter_result["category_name"]
        dto_instance.subcategory_name = query_filter_result["subcategory_name"]

    return dto_instance
