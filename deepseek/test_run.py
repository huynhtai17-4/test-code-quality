import asyncio
import time
import httpx
from config import load_config
from client import chat_completion

async def run_test():
    cfg = load_config()
    print("=" * 60)
    print("🧪 BẮT ĐẦU TEST TOÀN DIỆN HỆ THỐNG MỚI (MODULAR ARCHITECTURE)")
    print("=" * 60)
    print(f"[*] Token xác thực : {cfg.get('auth_token', '')[:12]}...")
    print(f"[*] Session hiện tại: {cfg.get('chat_session_id', 'Chưa có')}")
    
    question = "Một tam giác vuông có 2 cạnh góc vuông là 3 và 4. Hỏi cạnh huyền bằng bao nhiêu? Trả lời thật ngắn gọn."
    print(f"[*] Câu hỏi test    : \"{question}\"")
    print("[*] Đang gửi tới DeepSeek Web & giải PoW...")

    t0 = time.time()
    async with httpx.AsyncClient() as client:
        ans = await chat_completion(client, cfg, question, thinking_enabled=True)
    t1 = time.time()

    print("=" * 60)
    print(f"✅ THÀNH CÔNG! Thời gian phản hồi: {t1 - t0:.2f}s")
    print("=" * 60)
    print(f"Đáp án: {ans}")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(run_test())
