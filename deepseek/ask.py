import sys
import asyncio
import httpx
from config import load_config
from client import chat_completion

async def main():
    cfg = load_config()

    if len(sys.argv) > 1:
        question = " ".join(sys.argv[1:])
    else:
        try:
            question = input("\n👉 Nhập câu hỏi cho DeepSeek: ").strip()
        except (KeyboardInterrupt, EOFError):
            return

    if not question:
        print("[-] Câu hỏi không được để trống!")
        return

    print(f"\n[*] Đang gửi câu hỏi tới DeepSeek: \"{question}\"...")
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            answer = await chat_completion(client, cfg, question, thinking_enabled=True)
            print("\n" + "=" * 55)
            print("🤖 PHẢN HỒI TỪ DEEPSEEK:")
            print("=" * 55)
            print(answer)
            print("=" * 55 + "\n")
        except Exception as e:
            print(f"[-] Lỗi: {e}")

if __name__ == "__main__":
    asyncio.run(main())
