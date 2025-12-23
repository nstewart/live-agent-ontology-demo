"""FastAPI server for the FreshMart Operations Agent with SSE streaming."""

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from src.graphs.ops_assistant_graph import cleanup_graph_resources, run_assistant


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown."""
    yield
    # Cleanup on shutdown
    await cleanup_graph_resources()


app = FastAPI(
    title="FreshMart Operations Agent",
    description="AI-powered operations assistant with SSE streaming",
    lifespan=lifespan,
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Thread-Id"],
)


class ChatRequest(BaseModel):
    """Request body for chat endpoints."""

    message: str
    thread_id: Optional[str] = None


class ChatResponse(BaseModel):
    """Response body for non-streaming chat endpoint."""

    response: str
    thread_id: str


async def event_generator(message: str, thread_id: str):
    """
    Generate SSE events from the assistant.

    Event types:
    - tool_call: {"name": str, "args": dict}
    - tool_result: {"content": str}
    - thinking: {"content": str}  (extended thinking if enabled)
    - response: str (final complete response)
    - error: {"message": str}
    - done: {}  (stream complete)
    """
    try:
        async for event_type, data in run_assistant(message, thread_id=thread_id, stream_events=True):
            # Format as SSE
            event_data = {"type": event_type, "data": data}
            yield f"data: {json.dumps(event_data)}\n\n"

        # Signal completion
        yield f"data: {json.dumps({'type': 'done', 'data': {}})}\n\n"
    except Exception as e:
        error_event = {"type": "error", "data": {"message": str(e)}}
        yield f"data: {json.dumps(error_event)}\n\n"


@app.post("/chat/stream")
async def chat_stream(request: ChatRequest):
    """
    SSE streaming endpoint for chat.

    Returns a stream of Server-Sent Events with thinking states and responses.
    The thread_id is returned in the X-Thread-Id response header.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    thread_id = request.thread_id or f"chat-{uuid.uuid4().hex[:8]}"

    return StreamingResponse(
        event_generator(request.message, thread_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Thread-Id": thread_id,
        },
    )


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Non-streaming chat endpoint (backwards compatible).

    Returns the final response after all processing is complete.
    """
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="message is required")

    thread_id = request.thread_id or f"api-{uuid.uuid4().hex[:8]}"

    response_text = None
    async for event_type, data in run_assistant(request.message, thread_id=thread_id, stream_events=False):
        if event_type == "response":
            response_text = data
            break

    if not response_text:
        raise HTTPException(status_code=500, detail="No response generated")

    return ChatResponse(response=response_text, thread_id=thread_id)


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}
