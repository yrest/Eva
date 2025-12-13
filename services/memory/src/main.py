from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os

app = FastAPI(title="Eva Memory Service")


class Memory(BaseModel):
    id: str
    user_id: str
    content: str
    embedding: list[float] | None = None
    metadata: dict | None = None


class MemoryCreateRequest(BaseModel):
    user_id: str
    content: str
    metadata: dict | None = None


class MemorySearchRequest(BaseModel):
    user_id: str
    query: str
    limit: int = 10


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/memories", response_model=Memory)
async def create_memory(request: MemoryCreateRequest):
    # TODO: Store memory with embedding
    raise HTTPException(status_code=501, detail="Not implemented")


@app.post("/memories/search")
async def search_memories(request: MemorySearchRequest):
    # TODO: Search memories by similarity
    raise HTTPException(status_code=501, detail="Not implemented")


@app.get("/memories/{user_id}")
async def get_user_memories(user_id: str, limit: int = 100):
    # TODO: Get user's recent memories
    raise HTTPException(status_code=501, detail="Not implemented")


@app.delete("/memories/{memory_id}")
async def delete_memory(memory_id: str):
    # TODO: Delete a memory
    raise HTTPException(status_code=501, detail="Not implemented")


if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", "8004"))
    uvicorn.run(app, host="0.0.0.0", port=port)
