from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from app.infra.middleware.request_id_middleware import RequestIDMiddleware

app = FastAPI(
    title="Whisp API",
    description="A messaging and user management API",
    version="1.0.0",
)

# Middlewares
app.add_middleware(RequestIDMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/demo")
async def demo(request: Request) -> dict[str, str]:
    return {"message": "Hello World", "request_id": str(request.state.request_id)}
