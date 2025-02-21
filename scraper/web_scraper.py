import asyncio
from abc import abstractmethod


class WebScraper:
    def __init__(self):
        self._stop_event = asyncio.Event()

    @abstractmethod
    async def run(self):
        raise NotImplementedError

    async def stop(self):
        """Stop the background fetch loop"""
        self._stop_event.set()