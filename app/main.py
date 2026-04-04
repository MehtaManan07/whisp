import logging
import sys
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.error_handler import global_exception_handler
from app.core.config import config
from app.core.scheduler.service import SchedulerService
from app.core.scheduler.jobs import process_due_reminders, send_weekly_reports, send_monthly_reports, check_budget_warnings

from app.integrations.whatsapp.controller import router as whatsapp_router
from app.modules.expenses.controller import router as expenses_router
from app.modules.categories.controller import router as categories_router
from app.modules.users.controller import router as users_router
from app.modules.reminders.controller import router as reminders_router

# Configure logging to output to console
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

# Set logger for your app
logger = logging.getLogger(__name__)

# Scheduler instance (singleton)
scheduler_service = SchedulerService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Starts scheduler on startup, stops on shutdown.
    """
    logger.info("🚀 Starting Whisp API...")
    
    # Start scheduler if enabled
    if config.scheduler_enabled:
        scheduler_service.start()
        
        # Add reminders job
        scheduler_service.add_interval_job(
            func=process_due_reminders,
            minutes=config.scheduler_reminders_interval_minutes,
            job_id="process_due_reminders",
        )
        logger.info(
            f"📅 Reminders job scheduled every {config.scheduler_reminders_interval_minutes} minute(s)"
        )

        # Weekly spending report: Sunday 9 PM IST
        scheduler_service.add_cron_job(
            func=send_weekly_reports,
            job_id="send_weekly_reports",
            day_of_week="sun",
            hour=21,
            minute=0,
        )
        logger.info("📊 Weekly report scheduled: Sunday 9 PM IST")

        # Monthly spending report: 1st of month 9 AM IST
        scheduler_service.add_cron_job(
            func=send_monthly_reports,
            job_id="send_monthly_reports",
            day="1",
            hour=9,
            minute=0,
        )
        logger.info("📊 Monthly report scheduled: 1st of month 9 AM IST")

        # Budget warning check: every 30 minutes
        scheduler_service.add_interval_job(
            func=check_budget_warnings,
            minutes=30,
            job_id="check_budget_warnings",
        )
        logger.info("💸 Budget warnings check scheduled every 30 minutes")
    else:
        logger.info("⏸️ Scheduler is disabled")
    
    yield  # App is running
    
    # Shutdown
    logger.info("🛑 Shutting down Whisp API...")
    if config.scheduler_enabled:
        scheduler_service.shutdown()


app = FastAPI(
    title="Whisp API",
    description="A messaging and user management API",
    version="1.0.0",
    lifespan=lifespan,
)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(whatsapp_router)
app.include_router(expenses_router)
app.include_router(categories_router)
app.include_router(users_router)
app.include_router(reminders_router)


@app.get("/demo")
async def demo() -> dict[str, str]:
    return {"message": "Hello World"}
