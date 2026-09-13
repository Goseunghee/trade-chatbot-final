from typing import Any, Dict, Optional

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from app.services.chat_service import answer_question

app = FastAPI(
    title="Trade Chatbot API",
    version="1.0.0"
)

class ChatRequest(BaseModel):
    question: str

class ChatResponse(BaseModel):
    intent: str
    question: str
    answer: str
    data: Optional[Dict[str, Any]] = None
    firestore_saved: bool

@app.get("/")
def root():
    return {"message": "Trade Chatbot API is running"}

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ask", response_model=ChatResponse)
def ask_chat(request: ChatRequest):
    try:
        result = answer_question(request.question)
        return ChatResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))