"""
Centralized dependency management
Singletons for stateless services, per-request for DB sessions
"""

from functools import lru_cache
from typing import Annotated

from fastapi import Depends

from app.core.config import config
from app.core.cache.sqlalchemy_cache_client import SQLAlchemyCacheClient
from app.core.cache.service import CacheService
from app.integrations.llm.service import LLMService
from app.integrations.telegram.service import TelegramService
from app.modules.expenses.service import ExpensesService
from app.modules.users.service import UsersService
from app.modules.reminders.service import ReminderService
from app.modules.categories.service import CategoriesService
from app.intelligence.intent.classifier import IntentClassifier
from app.intelligence.categorization.classifier import CategoryClassifier
from app.core.orchestrator import MessageOrchestrator


# ============================================================================
# SINGLETON DEPENDENCIES (One instance for entire app lifetime)
# ============================================================================


@lru_cache()
def get_cache_client():
    """SQLAlchemy cache client - SINGLETON"""
    return SQLAlchemyCacheClient()


@lru_cache()
def get_cache_service():
    """Cache service - SINGLETON"""
    cache_client = get_cache_client()
    return CacheService(cache_client)


@lru_cache()
def get_llm_service():
    """LLM service - SINGLETON (stateless)"""
    return LLMService(api_key=config.gemini_key)


@lru_cache()
def get_telegram_service():
    """Telegram client - SINGLETON"""
    orchestrator = get_orchestrator()
    return TelegramService(orchestrator=orchestrator)


# ============================================================================
# SERVICE LAYER (Singletons that self-manage DB sessions)
# ============================================================================


@lru_cache()
def get_expense_service():
    return ExpensesService()


@lru_cache()
def get_user_service():
    return UsersService()


@lru_cache()
def get_category_service():
    return CategoriesService()


@lru_cache()
def get_reminder_service():
    return ReminderService()


# ============================================================================
# INTELLIGENCE LAYER (Singletons)
# ============================================================================


@lru_cache()
def get_intent_classifier():
    from app.intelligence.intent import IntentClassifier

    llm_service = get_llm_service()
    return IntentClassifier(llm_service=llm_service)


@lru_cache()
def get_category_classifier():
    cache_service = get_cache_service()
    llm_service = get_llm_service()
    expenses_service = get_expense_service()
    return CategoryClassifier(
        cache_service=cache_service,
        llm_service=llm_service,
        expenses_service=expenses_service,
    )


# ============================================================================
# ORCHESTRATOR (Singleton that uses all dependencies)
# ============================================================================


@lru_cache()
def get_orchestrator():
    return MessageOrchestrator(
        users_service=get_user_service(),
        intent_classifier=get_intent_classifier(),
        llm_service=get_llm_service(),
        category_classifier=get_category_classifier(),
    )


# ============================================================================
# FASTAPI DEPENDENCY TYPE ALIASES
# ============================================================================

IntentClassifierDep = Annotated[IntentClassifier, Depends(get_intent_classifier)]
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
TelegramServiceDep = Annotated[TelegramService, Depends(get_telegram_service)]
ExpenseServiceDep = Annotated[ExpensesService, Depends(get_expense_service)]
UserServiceDep = Annotated[UsersService, Depends(get_user_service)]
CategoryServiceDep = Annotated[CategoriesService, Depends(get_category_service)]
ReminderServiceDep = Annotated[ReminderService, Depends(get_reminder_service)]
CategoryClassifierDep = Annotated[CategoryClassifier, Depends(get_category_classifier)]
OrchestratorDep = Annotated[MessageOrchestrator, Depends(get_orchestrator)]

CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]
