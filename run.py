import asyncio
import logging
from aiogram import Bot, Dispatcher, F

from app.handlers import router
from config import TOKEN
from app.database.models import async_main


async def main():
    await async_main()
    bot = Bot(token=TOKEN)
    dp = Dispatcher()

    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == '__main__':
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        filename="bot.log",
        filemode = "a",
    )
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("EXIT")