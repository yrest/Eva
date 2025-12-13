from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

app = FastAPI(title="Eva Chat Service")


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    conversation_id: str | None = None


class ChatResponse(BaseModel):
    message: ChatMessage
    conversation_id: str


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/completions", response_model=ChatResponse)
async def chat_completions(request: ChatRequest):
    # TODO: Implement AI chat completion
    raise HTTPException(status_code=501, detail="Not implemented")


@app.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str):
    # TODO: Get conversation history
    raise HTTPException(status_code=501, detail="Not implemented")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8002"))
    uvicorn.run(app, host="0.0.0.0", port=port)
