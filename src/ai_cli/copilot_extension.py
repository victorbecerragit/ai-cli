from __future__ import annotations

import asyncio
import json
import logging
import os
import uvicorn
import time
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.responses import StreamingResponse
from .api_client import ApiClient
from .profile_manager import get_profile

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("copilot-bridge")

app = FastAPI(title="ai-cli Copilot Extension")

async def verify_auth(request: Request):
    """
    Verify the API key if AI_CLI_API_KEY is set in the environment.
    """
    required_key = os.getenv("AI_CLI_API_KEY")
    if not required_key:
        return

    auth_header = request.headers.get("Authorization")
    if not auth_header:
        logger.warning("Unauthorized access attempt: Missing Authorization header")
        raise HTTPException(status_code=401, detail="Missing Authorization header")

    provided_key = auth_header.replace("Bearer ", "").strip()
    if provided_key != required_key:
        logger.warning("Unauthorized access attempt: Invalid API Key")
        raise HTTPException(status_code=401, detail="Invalid API Key")

@app.get("/health")
async def health_check(request: Request): # request is unused but kept for consistency with other endpoints
    """Verify server status and profile availability."""
    from .profile_manager import load_profiles
    return {"status": "ok", "profiles_count": len(load_profiles())}

@app.get("/v1/models", dependencies=[Depends(verify_auth)])
async def list_models(request: Request):
    """Allow clients to discover local profiles as models."""
    from .profile_manager import load_profiles
    profiles = load_profiles()
    return {
        "object": "list",
        "data": [
            {
                "id": name,
                "object": "model",
                "created": int(time.time()), # Dynamic timestamp
                "owned_by": "ai-cli"
            }
            for name in profiles.keys()
        ]
    }

@app.post("/v1/chat/completions", dependencies=[Depends(verify_auth)])
async def chat_handler(request: Request):
    """
    Endpoint that GitHub Copilot calls.
    """
    try:
        data = await request.json()
    except Exception:
        logger.error("Failed to parse incoming JSON payload")
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    messages = data.get("messages", [])
    
    if not messages:
        logger.warning("Received request with no messages")
        raise HTTPException(status_code=400, detail="No messages provided")

    stream_requested = data.get("stream", False)

    # The last message is the current prompt
    last_msg = messages[-1]
    prompt = last_msg.get("content", "")
    
    # History format: ApiClient expects everything before the current prompt
    history = messages[:-1] if len(messages) > 1 else []

    # 2. Pick a profile. Default to google-gemma4, but allow override via header.
    profile_name = request.headers.get("X-AI-CLI-Profile", "google-gemma4")
    profile = get_profile(profile_name)
    
    logger.info(f"Request: {profile_name} | Prompt: {prompt[:50]}... | Stream: {stream_requested}")

    if not profile:
        logger.error(f"Profile not found: {profile_name}")
        raise HTTPException(status_code=404, detail=f"Profile '{profile_name}' not found locally.")

    client = ApiClient(profile)

    if stream_requested:
        async def stream_generator():
            logger.info(f"Starting stream for profile: {profile_name}")
            # 1. Send an initial chunk indicating the role
            yield f"data: {json.dumps({'choices': [{'delta': {'role': 'assistant'}, 'index': 0}]})}\n\n"
            
            # Create the blocking generator
            gen = client.ask_stream(prompt, history=history)
            
            while True:
                try:
                    # Offload the blocking next() call to a thread to keep the event loop free
                    chunk = await asyncio.to_thread(next, gen, None)
                    if chunk is None:
                        break

                    payload = {
                        "choices": [{"delta": {"content": chunk}, "index": 0}]
                    }
                    yield f"data: {json.dumps(payload)}\n\n"
                except Exception as e:
                    logger.error(f"Stream error: {e}")
                    error_payload = {
                        "choices": [{"delta": {"content": f"\n[Stream Error: {e}]"}, "index": 0}]
                    }
                    yield f"data: {json.dumps(error_payload)}\n\n"
                    break
            
            # 2. Send final finish_reason for strict clients
            final_payload = {
                "choices": [{"delta": {}, "finish_reason": "stop", "index": 0}]
            }
            yield f"data: {json.dumps(final_payload)}\n\n"
            yield "data: [DONE]\n\n"
            logger.info(f"Stream finished for profile: {profile_name}")

        return StreamingResponse(stream_generator(), media_type="text/event-stream")

    try:
        # Pass history to maintain conversation context
        result = await asyncio.to_thread(client.ask, prompt, history=history)
        logger.info(f"Sync request completed: {result.status_code} ({result.elapsed_ms}ms)")
    except Exception as e:
        logger.error(f"Model request failed: {e}")
        raise HTTPException(status_code=500, detail=f"Model request failed: {str(e)}")

    # 4. Return the response in the format Copilot/OpenAI expects
    return {
        "choices": [
            {
                "message": {
                    "role": "assistant",
                    "content": result.text
                }
            }
        ]
    }

if __name__ == "__main__":
    # Run with: uv run python -m ai_cli.copilot_extension
    uvicorn.run(app, host="0.0.0.0", port=8000)