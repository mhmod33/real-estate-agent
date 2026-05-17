from fastapi import FastAPI
from pydantic import BaseModel

from agent import run_agent
app = FastAPI(
    title="Real Estate AI Agent",
    description="مستشار عقاري ذكي متخصص في السوق المصري",
    version="1.0.0",
)

@app.on_event("startup")
async def startup_event():
    from rag.retriever import _get_collection
_get_collection()
    

class QuestionRequest(BaseModel):
    question: str


class AnswerResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AnswerResponse)
async def ask(request: QuestionRequest):
    """إرسال سؤال للمستشار العقاري والحصول على إجابة."""
    answer = run_agent(request.question)
    return AnswerResponse(answer=answer)
