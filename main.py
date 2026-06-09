import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from config import BOT_TOKEN
from database import init_db
from admin import router

logging.basicConfig(level=logging.INFO)


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp  = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)

    await init_db()
    print("✅ Bot ishga tushdi!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
