from typing import Any, Awaitable, Callable, Dict

from aiogram import BaseMiddleware
from aiogram.types import Message
from cachetools import TTLCache

from bot.config import flood_delay


class FloodMiddleware(BaseMiddleware):
    def __init__(self, timer: int = flood_delay):
        self.delay = TTLCache(maxsize=10_000, ttl=timer)

    async def __call__(
        self,
        handler: Callable[[Message, Dict[str, Any]], Awaitable[Any]],
        event: Message,
        data: Dict[str, Any],
    ) -> Any:
        user_id = event.from_user.id

        if user_id in self.delay:
            return

        self.delay[user_id] = True

        return await handler(event, data)
