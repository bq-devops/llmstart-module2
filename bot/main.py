import asyncio
import logging
import os

from aiogram import Bot, Dispatcher, types, Router
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv


router = Router()


@router.message(Command("ping"))
async def handle_ping(message: types.Message) -> None:
    await message.answer("pong")


@router.message()
async def handle_any(message: types.Message) -> None:
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="/ping")]],
        resize_keyboard=True,
    )
    await message.answer("Привет! Я готов. Попробуйте /ping", reply_markup=kb)


async def main() -> None:
    # Load .env from project root, then fallback to config/env if needed
    load_dotenv()
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        load_dotenv("config/env")
        telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in environment (.env or config/env)")

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )

    bot = Bot(
        token=telegram_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher()
    dp.include_router(router)

    logging.info("Starting bot via long polling")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Bot stopped")


