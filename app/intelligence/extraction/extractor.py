import json
from app.integrations.llm.service import LLMService
from app.intelligence.categorization.classifier import CategoryClassifier
from app.intelligence.extraction.prompts import build_dto_prompt
from app.intelligence.intent.types import DTO_UNION, INTENT_TO_DTO, IntentType


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

    # Always run categorization for expense DTOs since LLM no longer handles categories
    if hasattr(dto_instance, "category_name") or hasattr(
        dto_instance, "subcategory_name"
    ):
        classification_result = await category_classifier.classify(
            original_message=message, dto_instance=dto_instance, user_id=user_id
        )

        # Set the classified categories (can be None for non-transactional queries)
        if hasattr(dto_instance, "category_name"):
            dto_instance.category_name = classification_result["category"]  # type: ignore
        if hasattr(dto_instance, "subcategory_name"):
            dto_instance.subcategory_name = classification_result["subcategory"]  # type: ignore
        
        # Set classification metadata for handlers to use
        if hasattr(dto_instance, "classification_confidence"):
            dto_instance.classification_confidence = classification_result.get("confidence")  # type: ignore
        if hasattr(dto_instance, "classification_method"):
            dto_instance.classification_method = classification_result.get("method")  # type: ignore
        if hasattr(dto_instance, "classification_reasoning"):
            dto_instance.classification_reasoning = classification_result.get("reasoning")  # type: ignore

    return dto_instance
