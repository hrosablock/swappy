import asyncio
import logging
import sys

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage
from aiogram.utils.callback_answer import CallbackAnswerMiddleware

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
from bot.db.database import async_session, engine
from bot.db.models import Base
from bot.env import REDIS_URL, TOKEN
from bot.handlers import crosschainHD, limitHD, menuHD, swapHD, withdrawHD
from bot.Middlewares.dbMD import DbSessionMiddleware
from bot.Middlewares.FloodMD import FloodMiddleware

# --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------


logging.basicConfig(level=logging.DEBUG, stream=sys.stdout, format="%(asctime)s - %(levelname)s - %(message)s")

logger = logging.getLogger(__name__)

bot = None
async def main() -> None:
    global bot
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        storage = RedisStorage.from_url(REDIS_URL)

        bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML), storage=storage)
        dp = Dispatcher()

        dp.message.filter(F.chat.type == "private")
        dp.callback_query.filter(F.message.chat.type == "private")

        dp.message.middleware(FloodMiddleware())
        dp.update.middleware(DbSessionMiddleware(session_pool=async_session))
        dp.callback_query.middleware(CallbackAnswerMiddleware())

        dp.include_router(menuHD.router)
        dp.include_router(swapHD.router)
        dp.include_router(limitHD.router)
        dp.include_router(crosschainHD.router)
        dp.include_router(withdrawHD.router)

        logger.info("Bot started successfully!")
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logger.exception("Fatal error in main()")
    finally:
        if bot:
            await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
