import asyncio
import json
import logging
import time

import aiohttp
import aiodns
from ratelimiter import RateLimiter
from async_lru import alru_cache

# logging.basicConfig(level=logging.INFO)

GOOGLE_HEADERS = {"accept": "application/x-javascript"}
CLOUDFLARE_HEADERS = {"accept": "application/dns-json"}

DOH_REST_ENDPOINTS = [{"url": "https://1.1.1.1/dns-query",  # Cloudflare
                       "headers": CLOUDFLARE_HEADERS
                       },
                      {"url": "https://8.8.8.8/resolve",  # Google DNS servers
                       "headers": GOOGLE_HEADERS
                       },
                      # {"url": "https://8.8.4.4/resolve",
                      #  "headers": GOOGLE_HEADERS
                      #  }
                      ]

DNS_ENDPOINTS = [
                "1.1.1.1",
                 #"8.8.8.8"
]

DNS_RETRY_CODES = [2, 5, 8, 9]  # try another server if receiving these codes


class DNSResolver:
    """ Provides asynchronous querying for tradiitional DNS and DNS-over-HTTPS(DoH)"""
    CACHE_SIZE = 128

    def __init__(self, dns_name_servers: list, doh_name_servers: list, *, doh_client: aiohttp.ClientSession = None):
        self._doh_name_servers = doh_name_servers or []
        self._dns_name_servers = dns_name_servers or []
        self._doh_client = doh_client or None
        self._dns_client = aiodns.DNSResolver(loop=asyncio.get_running_loop(), nameservers=dns_name_servers)
        self._loop = asyncio.get_running_loop()

    async def start_session(self):
        self._doh_client = self._doh_client or aiohttp.ClientSession()

    async def stop_session(self):
        await self._doh_client.close()

    """ DNS over HTTPS """
    @alru_cache(maxsize=max(CACHE_SIZE, 0))
    async def query_doh_json(self, target_domain: str, *, dns_type: str = "A", client=None, retry_if_fail: bool = True):
        client = client or self._doh_client
        for endpoint in self._doh_name_servers:
            url, headers = endpoint.get("url"), endpoint.get("headers")
            try:
                # passing param instead of json due to inconsistent MIME types :(
                async with await client.get(url, params={"name": target_domain, "type": dns_type},
                                            headers=headers) as resp:
                    logging.info(f"Using {url}; Response: {resp.status}")
                    if resp.status != 200:
                        continue
                    elif not retry_if_fail:
                        break
                    json_reply = json.loads(await resp.text())
                    status = json_reply.get("Status")
                    if not status:  # error code 0 means success
                        return [answer.get("data") for answer in json_reply.get("Answer")]
                    if status in DNS_RETRY_CODES and retry_if_fail:
                        continue
                    else:
                        return None
            except Exception as e:
                logging.warning(f"Err: {e} for {url}:{target_domain}")

    async def mass_query_doh_json(self, target_domains: list, *, dns_type: str = "A", rate=20, max_tokens=20,
                                  retry_if_fail: bool = True):
        client = RateLimiter(self._doh_client, rate=rate, max_tokens=max_tokens)
        return await asyncio.gather(
            *[self.query_doh_json(target_domain, dns_type=dns_type, client=client, retry_if_fail=retry_if_fail) for
              target_domain in target_domains])

    """ Traditional DNS """
    @alru_cache(maxsize=max(CACHE_SIZE, 0))
    async def query_dns(self, target_domain, *, dns_type: str = "A"):
        try:
            answers = await self._dns_client.query(target_domain, dns_type)
            return [getattr(answer, "host", None) for answer in answers]
        except Exception as e:
            logging.warning(f"Err: {e} for {target_domain}")

    async def mass_query_dns(self, target_domains: list):
        return await asyncio.gather(*[self.query_dns(target_domain) for target_domain in target_domains])


async def test():
    resolver = DNSResolver(DNS_ENDPOINTS, DOH_REST_ENDPOINTS)
    await resolver.start_session()
    start = time.time()
    res = await resolver.mass_query_doh_json(["google.com"] * 10, retry_if_fail=False)
    #res = await resolver.mass_query_dns(["google.com"]*100)
    print(res)
    end = time.time()
    print(f"Time taken: {end - start}")
    await resolver.stop_session()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(test())
    loop.close()
