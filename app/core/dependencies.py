"""
Centralized dependency management
Singletons for stateless services, per-request for DB sessions
"""

from functools import lru_cache
from typing import AsyncGenerator, Annotated
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends
from contextlib import asynccontextmanager


from app.core.config import config
from app.core.cache.sqlalchemy_cache_client import SQLAlchemyCacheClient
from app.core.cache.service import CacheService
from app.core.db.engine import get_db_util, AsyncSessionLocal
from app.integrations.llm.key_manager import APIKeyManager
from app.integrations.llm.service import LLMService
from app.integrations.whatsapp.service import WhatsAppService
from app.integrations.gmail.service import GmailService
from app.modules.expenses.service import ExpensesService
from app.modules.kraftculture.service import KraftcultureService
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


@asynccontextmanager
async def get_cache_db_session():
    """Create a new database session for cache operations."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@lru_cache()
def get_cache_client():
    """SQLAlchemy cache client - SINGLETON"""
    return SQLAlchemyCacheClient(db_session_factory=get_cache_db_session)


@lru_cache()
def get_cache_service():
    """Cache service - SINGLETON"""
    cache_client = get_cache_client()
    return CacheService(cache_client)


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
    return LLMService(api_key=config.gemini_key)


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


@lru_cache()
def get_gmail_service():
    """Gmail service - SINGLETON"""
    return GmailService(
        credentials_path=config.gmail_credentials_path,
        token_path=config.gmail_token_path,
    )


@lru_cache()
def get_kraftculture_service():
    """Kraftculture service - SINGLETON"""
    gmail_service = get_gmail_service()
    whatsapp_service = get_whatsapp_service()
    cache_service = get_cache_service()
    
    # Parse WhatsApp numbers from comma-separated config
    whatsapp_numbers = [
        n.strip() 
        for n in config.kraftculture_whatsapp_numbers.split(",") 
        if n.strip()
    ]
    
    return KraftcultureService(
        gmail_service=gmail_service,
        whatsapp_service=whatsapp_service,
        cache_service=cache_service,
        default_sender_email=config.kraftculture_sender_email,
        whatsapp_numbers=whatsapp_numbers,
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

# Gmail dependencies
GmailServiceDep = Annotated[GmailService, Depends(get_gmail_service)]

# Kraftculture dependencies
KraftcultureServiceDep = Annotated[KraftcultureService, Depends(get_kraftculture_service)]
