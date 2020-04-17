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

    def __init__(self, client, *, rate: int or float = 1, max_tokens: int = 10, x_ttl: int or float = 60, x_rl: int = 1500):
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
        self._x_ttl = x_ttl  # x_ttl is time (in seconds)a left to refresh quota
        self._x_updated_at = time.monotonic()
        self.X_RL = x_rl
        self._x_rl = x_rl  # X_rl is sends left.

    @property
    def x_rl(self):
        return self._x_rl

    @property
    def x_ttl(self):
        return self._x_ttl

    @x_ttl.setter
    def x_ttl(self, value):
        self._x_ttl = value

    async def get(self, *args, **kwargs):
        await self.wait_for_token()
        await self.wait_for_ttl()
        # now = time.monotonic() - START
        # logging.info(f'{now:.0f}s: ask {args[0]}')
        logging.info(f"Tokens left: {self.tokens}")
        return self.client.get(*args, **kwargs)

    async def post(self, *args, **kwargs):
        await self.wait_for_token()
        # now = time.monotonic() - START
        # logging.info(f'{now:.0f}s: ask {args[0]}')
        logging.info(f"Tokens left: {self.tokens}")
        return self.client.post(*args, **kwargs)

    async def put(self, *args, **kwargs):
        await self.wait_for_token()
        # now = time.monotonic() - START
        # logging.info(f'{now:.0f}s: ask {args[0]}')
        logging.info(f"Tokens left: {self.tokens}")
        return self.client.put(*args, **kwargs)

    async def wait_for_token(self):
        while self.tokens < 1:
            self.add_new_tokens()
            await asyncio.sleep(0.1)

        self.tokens -= 1

    async def wait_for_ttl(self):
        now = time.monotonic()
        time_since_update = now - self._x_updated_at
        if self._x_rl < 1:
            while time_since_update < self._x_ttl:
                await asyncio.sleep(0.5)
                time_since_update += time.monotonic()
            self._x_rl = self.X_RL
        self._x_updated_at = time.monotonic()
        self._x_rl -= 1

    def add_new_tokens(self):
        now = time.monotonic()
        time_since_update = now - self.updated_at
        new_tokens = time_since_update * self.RATE
        if self.tokens + new_tokens >= 1:
            self.tokens = min(self.tokens + new_tokens, self.MAX_TOKENS)
            self.updated_at = now


# class HTTPRateLimiter(RateLimiter):
#     def __init__(self, client, *, rate: int or float = 1, max_tokens: int = 10):
#         super(HTTPRateLimiter, self).__init__(client, rate=rate, max_tokens=max_tokens)
