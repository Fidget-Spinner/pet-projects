"""
Using code made by Quentin Pradet (https://github.com/pquentin)/ . Full credits to them.
Code from https://gist.github.com/pquentin/5d8f5408cdad73e589d85ba509091741, discussed in
https://quentin.pradet.me/blog/how-do-you-rate-limit-calls-with-aiohttp.html.
Much thanks for their extremely useful code and clear explanation.
"""

import asyncio
import time
import logging

START = time.monotonic()


class RateLimiter:
    """Rate limits an HTTP client that would make get() and post() calls.
    Calls are rate-limited by host.
    https://quentin.pradet.me/blog/how-do-you-rate-limit-calls-with-aiohttp.html
    This class is not thread-safe."""

    def __init__(self, client, *, rate: int = 1, max_tokens: int = 10):
        """
        :param client: aiohttp client
        :param rate: maximum requests per second
        :param max_tokens: maximum open requests at any time
        """
        self.client = client
        self.MAX_TOKENS = max_tokens
        self.RATE = rate
        self.tokens = max_tokens
        self.updated_at = time.monotonic()

    async def get(self, *args, **kwargs):
        await self.wait_for_token()
        # now = time.monotonic() - START
        # logging.info(f'{now:.0f}s: ask {args[0]}')
        logging.info(f"Tokens left: {self.tokens}")
        return self.client.get(*args, **kwargs)

    async def wait_for_token(self):
        while self.tokens < 1:
            self.add_new_tokens()
            await asyncio.sleep(0.1)
        self.tokens -= 1

    def add_new_tokens(self):
        now = time.monotonic()
        time_since_update = now - self.updated_at
        new_tokens = time_since_update * self.RATE
        if self.tokens + new_tokens >= 1:
            self.tokens = min(self.tokens + new_tokens, self.MAX_TOKENS)
            self.updated_at = now
