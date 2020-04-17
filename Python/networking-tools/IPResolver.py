import aiohttp
import logging
import json
import asyncio
import time
from itertools import chain

from ratelimiter import RateLimiter

IP_API_HEADERS = {"Content-Type": "application/json"}
IP_API_RESP_HEADERS = {
    "X-Rl": int,
    "X-Ttl": int,
}
IP_REST_ENDPOINTS = [
    {"url": "http://ip-api.com/batch",
     "method": "POST",
     "headers": IP_API_HEADERS,
     "response-headers": IP_API_RESP_HEADERS
     },
]


class IPResolver:
    """ Provides asynchronous querying for tradiitional DNS and DNS-over-HTTPS(DoH)"""
    CACHE_SIZE = 128

    def __init__(self, ip_rest_endpoints):
        self._http_client = None
        self._ip_rest_endpoints = ip_rest_endpoints
        self._latest_ip_api_resp = {"X-Ttl": "0", "X-Rl": "15"}

    async def start_session(self):
        self._http_client = self._http_client or aiohttp.ClientSession()

    async def stop_session(self):
        await self._http_client.close()

    async def query_http(self, method="GET", client=None, *args, **kwargs):
        query_methods = {
            "get": client.get or self._http_client.get,
            "post": client.post or self._http_client.post,
            "put": client.put or self._http_client.put,
        }

        query = query_methods.get(method.lower())
        try:
            async with await query(*args, **kwargs) as resp:
                logging.info(f"Using {args[0]}; Response: {resp.status}; Headers: {resp.headers}")
                if resp.status == 200:
                    return await resp.text(), resp.headers
                elif resp.status == 429:  # too many requests
                    await asyncio.sleep(int(resp.headers.get("X-Ttl") or resp.headers.get("Retry-After") or 1))
        except Exception as e:
            logging.warning(e)
        return None, None

    async def query_json(self, rest_endpoint: dict, client=None, **kwargs):
        while int(self._latest_ip_api_resp.get("X-Rl")) < 2:
            await asyncio.sleep(int(self._latest_ip_api_resp.get("X-Ttl")) // 2)
        method = rest_endpoint.get("method")
        url = rest_endpoint.get("url")
        headers = rest_endpoint.get("headers")
        text, headers = await self.query_http(method, client, url, headers=headers, **kwargs)
        print(headers)
        self._latest_ip_api_resp = headers
        return json.loads(text)

    async def mass_query_json_ip_api(self, target_ips: list):
        params = {"fields": "status,countryCode,query"}
        client = RateLimiter(self._http_client, rate=0.75, max_tokens=2)
        ip_api_results = await asyncio.gather(
            *[self.query_json(rest_endpoint=IP_REST_ENDPOINTS[0], client=client, json=ip_chunk, params=params) for ip_chunk in
              self.chunks(target_ips, 99)])
        return ((result.get("query"), result.get("countryCode")) for result in chain(*ip_api_results))

    @staticmethod
    def chunks(lst, n):
        for i in range(0, len(lst), n):
            yield lst[i:i + n]


async def test_ip():

    ip_resolver = IPResolver(IP_REST_ENDPOINTS)

    await ip_resolver.start_session()
    start = time.time()

    test_data = [
        "208.80.152.201",
        "8.8.8.8"
    ]
    ip_res = await ip_resolver.mass_query_json_ip_api(test_data)
    print(list(ip_res))
    end = time.time()
    print(f"Time taken: {end - start}")

    await ip_resolver.stop_session()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test_ip())
    loop.close()