import json
from app.integrations.llm.service import LLMService
from app.intelligence.categorization.classifier import CategoryClassifier
from app.intelligence.extraction.prompts import build_dto_prompt
from app.intelligence.intent.types import DTO_UNION, INTENT_TO_DTO, IntentType


class Extractor:
    def __init__(
        self, llm_service: LLMService, category_classifier: CategoryClassifier
    ):
        self.llm_service = llm_service
        self.category_classifier = category_classifier

    async def extract(
        self, message: str, intent: IntentType, user_id: int
    ) -> DTO_UNION:
        prompt = build_dto_prompt(message, intent, user_id)
        extraction_response = await self.llm_service.complete(
            prompt=prompt,
            max_tokens=500,
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
            classification_result = await self.category_classifier.classify(
                original_message=message, dto_instance=dto_instance, user_id=user_id
            )

            # Set the classified categories
            if hasattr(dto_instance, "category_name"):
                dto_instance.category_name = classification_result["category"]
            if hasattr(dto_instance, "subcategory_name"):
                dto_instance.subcategory_name = classification_result["subcategory"]

        return dto_instance
