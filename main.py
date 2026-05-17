from fastapi import FastAPI
from pydantic import BaseModel
import logging

from agent import run_agent

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Real Estate AI Agent",
    description="مستشار عقاري ذكي متخصص في السوق المصري",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    from rag.retriever import _get_collection
    from rag.embeddings import init_model
    
    try:
        logger.info("Loading embedding model...")
        init_model()
        logger.info("✅ Embedding model loaded successfully")
    except Exception as e:
        logger.error(f"❌ Failed to load embedding model: {e}")
        raise
    
    try:
        logger.info("Initializing vector store...")
        _get_collection()
        logger.info("✅ Vector store initialized successfully")
    except Exception as e:
        logger.warning(f"⚠️  Vector store initialization failed (this is OK if it's empty): {e}")
        # Don't raise - let the app start even if vector store is empty


class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


@app.get("/")
async def root():
    return {"status": "ok", "message": "Real Estate AI Agent is running"}


@app.post("/ask", response_model=AnswerResponse)
async def ask(request: QuestionRequest):
    answer = run_agent(request.question)
    return AnswerResponse(answer=answer)
