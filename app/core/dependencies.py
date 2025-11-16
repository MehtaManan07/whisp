"""
Centralized dependency management
Singletons for stateless services, per-request for DB sessions
"""

from functools import lru_cache
from typing import AsyncGenerator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends


from app.core.config import config
from app.core.cache.redis_client import RedisClient
from app.core.cache.service import CacheService
from app.core.db.engine import get_db_util
from app.integrations.llm.key_manager import APIKeyManager
from app.integrations.llm.service import LLMService
from app.integrations.whatsapp.service import WhatsAppService
from app.modules.expenses.service import ExpensesService
from app.modules.reminders.scheduler import ReminderScheduler
from app.modules.users.service import UsersService
from app.modules.reminders.service import ReminderService
from app.modules.categories.service import CategoriesService
from app.intelligence.intent.classifier import IntentClassifier
from app.intelligence.categorization.classifier import CategoryClassifier
from app.core.orchestrator import MessageOrchestrator
from app.core.cron.service import CronService


# ============================================================================
# PER-REQUEST DEPENDENCIES (New instance per request)
# ============================================================================


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Database session - NEW per request
    Automatically commits/rollbacks and closes
    """
    async for session in get_db_util():
        yield session


# ============================================================================
# SINGLETON DEPENDENCIES (One instance for entire app lifetime)
# ============================================================================


@lru_cache()
def get_redis():
    """Redis client - SINGLETON"""
    return RedisClient()


@lru_cache()
def get_cache_service():
    """Cache service - SINGLETON"""
    redis_client = get_redis()
    return CacheService(redis_client)


@lru_cache()
def get_api_key_manager(keys: str = "", key_prefix: str = "llm_usage:"):
    """API Key Manager - SINGLETON"""
    from app.core.config import config

    cache_service = get_cache_service()
    return APIKeyManager(
        cache_service,
        keys=keys,
        key_prefix=key_prefix,
    )


@lru_cache()
def get_llm_service():
    """LLM service - SINGLETON (stateless)"""
    api_key_manager = get_api_key_manager(
        keys=config.gemini_key, key_prefix="llm_usage:"
    )
    return LLMService(api_key_manager=api_key_manager)


@lru_cache()
def get_whatsapp_service():
    """WhatsApp client - SINGLETON"""
    orchestrator = get_orchestrator()
    return WhatsAppService(orchestrator=orchestrator)


# ============================================================================
# SERVICE LAYER (Singletons that accept DB session)
# ============================================================================


@lru_cache()
def get_expense_service():
    """
    Expense service - SINGLETON
    Takes DB session as method parameter, not in constructor
    """
    return ExpensesService()


@lru_cache()
def get_user_service():
    """User service - SINGLETON"""
    return UsersService()


# @lru_cache()
# def get_budget_service():
#     """Budget service - SINGLETON"""
#     return BudgetsService()


@lru_cache()
def get_category_service():
    """Category service - SINGLETON"""
    return CategoriesService()


@lru_cache()
def get_cron_service():
    """Cron service - SINGLETON"""
    api_key_manager = get_api_key_manager(
        keys=config.cron_keys, key_prefix="cron_usage:"
    )
    return CronService(api_key_manager=api_key_manager)


@lru_cache()
def get_reminder_service():
    """Reminder service - SINGLETON"""
    cron_service = get_cron_service()
    reminder_scheduler = ReminderScheduler(cron_service=cron_service)
    return ReminderService(
        cron_service=cron_service, reminder_scheduler=reminder_scheduler
    )


# ============================================================================
# INTELLIGENCE LAYER (Singletons)
# ============================================================================


@lru_cache()
def get_intent_classifier():
    """Intent classifier - SINGLETON"""
    from app.intelligence.intent import IntentClassifier

    llm_service = get_llm_service()
    return IntentClassifier(llm_service=llm_service)


@lru_cache()
def get_category_classifier():
    """Category classifier - SINGLETON"""
    cache_service = get_cache_service()
    llm_service = get_llm_service()
    return CategoryClassifier(cache_service=cache_service, llm_service=llm_service)


# ============================================================================
# ORCHESTRATOR (Singleton that uses all dependencies)
# ============================================================================


@lru_cache()
def get_orchestrator():
    """
    Message orchestrator - SINGLETON
    Coordinates all services
    """
    return MessageOrchestrator(
        users_service=get_user_service(),
        intent_classifier=get_intent_classifier(),
        llm_service=get_llm_service(),
        category_classifier=get_category_classifier(),
    )


# ============================================================================
# FASTAPI DEPENDENCY TYPE ALIASES
# ============================================================================

# Database dependencies
DatabaseDep = Annotated[AsyncSession, Depends(get_db)]

# Service dependencies
IntentClassifierDep = Annotated[IntentClassifier, Depends(get_intent_classifier)]
LLMServiceDep = Annotated[LLMService, Depends(get_llm_service)]
WhatsAppServiceDep = Annotated[WhatsAppService, Depends(get_whatsapp_service)]
ExpenseServiceDep = Annotated[ExpensesService, Depends(get_expense_service)]
UserServiceDep = Annotated[UsersService, Depends(get_user_service)]
CategoryServiceDep = Annotated[CategoriesService, Depends(get_category_service)]
ReminderServiceDep = Annotated[ReminderService, Depends(get_reminder_service)]
CategoryClassifierDep = Annotated[CategoryClassifier, Depends(get_category_classifier)]
OrchestratorDep = Annotated[MessageOrchestrator, Depends(get_orchestrator)]

# Cache dependencies
CacheServiceDep = Annotated[CacheService, Depends(get_cache_service)]

# Cron dependencies
CronServiceDep = Annotated[CronService, Depends(get_cron_service)]
