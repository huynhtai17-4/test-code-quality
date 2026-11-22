#!/usr/bin/env python3
"""
DeepSeek Web Proxy Server (FastAPI)
Cung cấp API HTTP cục bộ phục vụ các ứng dụng khác gọi DeepSeek.
"""
import logging
from typing import Optional
import httpx
import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import load_config
from client import chat_completion

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
log = logging.getLogger("deepseek")

app = FastAPI(title="DeepSeek Web Proxy", version="2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="Nội dung câu hỏi")
    system_prompt: Optional[str] = Field(None, description="Prompt hệ thống (tùy chọn)")
    thinking_enabled: bool = Field(True, description="Bật chế độ suy luận DeepSeek-R1")
    new_chat: bool = Field(False, description="Tạo một đoạn chat mới riêng biệt")

class ChatResponse(BaseModel):
    response: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        cfg = load_config()
        prompt = req.message
        if req.system_prompt:
            prompt = f"{req.system_prompt}\n\n{req.message}"

        async with httpx.AsyncClient(follow_redirects=True) as client:
            answer = await chat_completion(
                client=client,
                cfg=cfg,
                prompt=prompt,
                thinking_enabled=req.thinking_enabled,
                force_new_session=req.new_chat,
            )
        return ChatResponse(response=answer)
    except Exception as e:
        log.error(f"Lỗi endpoint /chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok", "service": "deepseek-proxy"}

if __name__ == "__main__":
    print("[*] Khởi động DeepSeek API Proxy Server trên http://127.0.0.1:8001 ...")
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=False)
