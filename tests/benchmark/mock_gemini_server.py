"""
Requirements:
- fastapi
- uvicorn

Mock benchmark server for DENTAI performance tests.
Run:
    python tests/benchmark/mock_gemini_server.py
"""

from __future__ import annotations

import asyncio
import random
from typing import Any, Dict

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create and return the mock API app."""
    app = FastAPI(title="DENTAI Mock Gemini Server", version="1.0.0")

    @app.post("/v1/models/gemini-pro:generateContent")
    async def mock_gemini_generate_content(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Gemini API latency and response payload."""
        delay_seconds = random.uniform(0.3, 0.8)
        await asyncio.sleep(delay_seconds)

        prompt_preview = str(payload)[:100]
        return {
            "model": "gemini-pro-mock",
            "latency_ms_simulated": round(delay_seconds * 1000, 2),
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": f"Mock Gemini response for payload preview: {prompt_preview}"
                            }
                        ]
                    },
                    "finishReason": "STOP",
                    "index": 0,
                }
            ],
            "usageMetadata": {
                "promptTokenCount": random.randint(30, 120),
                "candidatesTokenCount": random.randint(40, 180),
                "totalTokenCount": random.randint(80, 300),
            },
        }

    @app.post("/v1/shadow-evaluator")
    async def mock_shadow_evaluator(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate Gemma/MedGemma evaluator with lower latency."""
        delay_seconds = random.uniform(0.08, 0.2)
        await asyncio.sleep(delay_seconds)

        return {
            "model": "gemma-2-9b-mock",
            "latency_ms_simulated": round(delay_seconds * 1000, 2),
            "is_clinically_accurate": random.choice([True, True, True, False]),
            "safety_violation": random.choice([False, False, False, True]),
            "missing_critical_info": random.choice([False, False, True]),
            "feedback": "Mock evaluator feedback generated for benchmark pipeline.",
            "request_echo": payload,
        }

    @app.get("/health")
    async def health() -> Dict[str, Any]:
        return {"status": "ok", "service": "dentai-mock-server"}

    return app


app = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("tests.benchmark.mock_gemini_server:app", host="127.0.0.1", port=8001, reload=False)
