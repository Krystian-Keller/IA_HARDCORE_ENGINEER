from functools import lru_cache

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.agents.customer_support import CustomerSupportAgent
from app.agents.knowledge import KnowledgeAgent
from app.agents.router import RouterAgent
from app.config import Settings
from app.schemas import AppError, ChatRequest, ChatResponse
from app.services.gemini import Gemini

app = FastAPI(title="AI Hardcore Engineer - Multi-Agent Support System")


@lru_cache
def get_router() -> RouterAgent:
    settings = Settings.from_env()
    gemini = Gemini(settings)
    return RouterAgent(gemini, KnowledgeAgent(gemini, settings), CustomerSupportAgent(gemini, settings))


@app.exception_handler(AppError)
async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest, router: RouterAgent = Depends(get_router)) -> ChatResponse:
    return router.chat(request)
