from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.core.middleware.request_id_middleware import RequestIDMiddleware
from app.core.error_handler import global_exception_handler

from app.integrations.whatsapp.controller import router as whatsapp_router
from app.modules.expenses.controller import router as expenses_router
from app.modules.categories.controller import router as categories_router
from app.modules.users.controller import router as users_router

app = FastAPI(
    title="Whisp API",
    description="A messaging and user management API",
    version="1.0.0",
)

# Add global exception handler
app.add_exception_handler(Exception, global_exception_handler)

# Middlewares
app.add_middleware(RequestIDMiddleware)

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


@app.get("/demo")
async def demo(request: Request) -> dict[str, str]:
    return {"message": "Hello World", "request_id": str(request.state.request_id)}
