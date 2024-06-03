import asyncio
from time import time
from random import randint
from datetime import datetime, timedelta, timezone
from urllib.parse import quote, unquote

import aiohttp
from aiohttp_proxy import ProxyConnector
from better_proxy import Proxy
from pyrogram import Client
from pyrogram.errors import Unauthorized, UserDeactivated, AuthKeyUnregistered
from pyrogram.raw.functions.messages import RequestWebView

from bot.config import settings
from bot.utils import logger
from bot.utils.boosts import FreeBoosts, UpgradableBoosts
from bot.exceptions import InvalidSession
from .headers import headers


class Slapper:
    def __init__(self, tg_client: Client):
        self.session_name = tg_client.name
        self.tg_client = tg_client

    def convert_to_url_encoded_format(self,input_string:str):
        parts = input_string.split('&')
        encoded_parts = []
        for part in parts:
            key, value = part.split('=', 1)
            if key == 'user':
                value = quote(value)
            encoded_parts.append(f"{key}={value}")
        return '&'.join(encoded_parts)
    
    async def get_tg_web_data(self, proxy: str | None) -> str:
        try:
            if proxy:
                proxy = Proxy.from_str(proxy)
                proxy_dict = dict(
                    scheme=proxy.protocol,
                    hostname=proxy.host,
                    port=proxy.port,
                    username=proxy.login,
                    password=proxy.password
                )
            else:
                proxy_dict = None

            self.tg_client.proxy = proxy_dict

            if not self.tg_client.is_connected:
                try:
                    await self.tg_client.connect()
                except (Unauthorized, UserDeactivated, AuthKeyUnregistered):
                    raise InvalidSession(self.session_name)

            web_view = await self.tg_client.invoke(RequestWebView(
                peer=await self.tg_client.resolve_peer('cexio_tap_bot'),
                bot=await self.tg_client.resolve_peer('cexio_tap_bot'),
                platform='android',
                from_bot_menu=False,
                url='https://cexp.cex.io/'
            ))

            auth_url = web_view.url
            tg_web_data = unquote(
                string=unquote(
                    string=auth_url.split('tgWebAppData=', maxsplit=1)[1].split('&tgWebAppVersion', maxsplit=1)[0]))

            if self.tg_client.is_connected:
                await self.tg_client.disconnect()


            return tg_web_data
        except InvalidSession as error:
            raise error

        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error during Authorization: {error}")
            await asyncio.sleep(delay=7)

    async def getUserInfo(self, http_client: aiohttp.ClientSession, tg_web_data: str) -> str:
        try:
            response = await http_client.post(
                url='https://cexp.cex.io/api/getUserInfo',
                json={
                "devAuthData": tg_web_data.split('"id":')[1].split(',')[0].strip(),
                "authData": self.convert_to_url_encoded_format(tg_web_data),
                "platform": "android",
                "data": {}
            })
            response.raise_for_status()

            response_json = await response.json()
            return response_json
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error while getting Access Token: {error}")
            await asyncio.sleep(delay=7)

    async def claim(self, http_client: aiohttp.ClientSession, tg_web_data: str,taps: int) -> dict[str]:
        try:
            response = await http_client.post(
                url='https://cexp.cex.io/api/claimTaps',
                json={
                "devAuthData": tg_web_data.split('"id":')[1].split(',')[0].strip(),
                "authData": self.convert_to_url_encoded_format(tg_web_data),
                "platform": "android",
                "data": {
                    "taps": taps
                }
            })
            response.raise_for_status()

            response_json = await response.json()
            player_data = response_json

            return player_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when Slapping: {error}")
            await asyncio.sleep(delay=7)

    async def startFarm(self, http_client: aiohttp.ClientSession, tg_web_data: str) -> dict[str]:
        try:
            response = await http_client.post(
                url='https://cexp.cex.io/api/startFarm',
                json={
                "devAuthData": tg_web_data.split('"id":')[1].split(',')[0].strip(),
                "authData": self.convert_to_url_encoded_format(tg_web_data),
                "platform": "android",
                "data": {}
            })
            response.raise_for_status()

            response_json = await response.json()
            player_data = response_json

            return player_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when start farming: {error}")
            await asyncio.sleep(delay=7)

    async def claimFarm(self, http_client: aiohttp.ClientSession, tg_web_data: str) -> dict[str]:
        try:
            response = await http_client.post(
                url='https://cexp.cex.io/api/claimFarm',
                json={
                "devAuthData": tg_web_data.split('"id":')[1].split(',')[0].strip(),
                "authData": self.convert_to_url_encoded_format(tg_web_data),
                "platform": "android",
                "data": {}
            })
            response.raise_for_status()

            response_json = await response.json()
            player_data = response_json

            return player_data
        except Exception as error:
            logger.error(f"{self.session_name} | Unknown error when start claim farm: {error}")
            await asyncio.sleep(delay=7)

    async def check_proxy(self, http_client: aiohttp.ClientSession, proxy: Proxy) -> None:
        try:
            response = await http_client.get(url='https://httpbin.org/ip', timeout=aiohttp.ClientTimeout(5))
            ip = (await response.json()).get('origin')
            logger.info(f"{self.session_name} | Proxy IP: {ip}")
        except Exception as error:
            logger.error(f"{self.session_name} | Proxy: {proxy} | Error: {error}")

    async def run(self, proxy: str | None) -> None:

        proxy_conn = ProxyConnector().from_url(proxy) if proxy else None

        async with aiohttp.ClientSession(headers=headers, connector=proxy_conn) as http_client:
            if proxy:
                await self.check_proxy(http_client=http_client, proxy=proxy)

            while True:
                try:
                    tg_web_data = await self.get_tg_web_data(proxy=proxy)
                    profile_data_raw = await self.getUserInfo(http_client=http_client, tg_web_data=tg_web_data)
                    if profile_data_raw['status'] != "ok":
                        continue
                    profile_data=profile_data_raw['data']
                    balance = profile_data['balance']
                    availableTaps = profile_data['availableTaps']
                    # farmReward = profile_data['farmReward']
                    # zeroTapWindowFinishAt = profile_data['zeroTapWindowFinishAt']
                    currentTapWindowFinishIn = profile_data['currentTapWindowFinishIn']
                    # serverTime = profile_data['serverTime']

                    miningEraIntervalInSeconds = profile_data['miningEraIntervalInSeconds']
                    farmStartedAt = profile_data['farmStartedAt']
                    if availableTaps > 0:
                        taps = randint(a=1, b=availableTaps)
                        profile_data_raw = await self.claim(http_client=http_client,tg_web_data=tg_web_data, taps=taps)
                        if profile_data_raw['status'] != "ok":
                            continue
                        profile_data=profile_data_raw['data']
                        balance = profile_data['balance']

                        logger.info(f"| Earned: <g>{taps}</g>")
                        logger.info(f"{self.session_name} | Balance: <c>{balance}</c>")
                    else:
                        currentTapWindowFinishInSeconds = (currentTapWindowFinishIn / 1000)
                        if currentTapWindowFinishInSeconds < miningEraIntervalInSeconds:
                            logger.info(f"Sleep {currentTapWindowFinishInSeconds}s")
                            await asyncio.sleep(delay=currentTapWindowFinishInSeconds)
                        else:
                            logger.info(f"Sleep {miningEraIntervalInSeconds}s")
                            await asyncio.sleep(delay=miningEraIntervalInSeconds)
                        
                    mining_era_start_time = datetime.fromisoformat(farmStartedAt.replace("Z", "+00:00"))
                    mining_era_end_time = mining_era_start_time + timedelta(seconds=miningEraIntervalInSeconds)
                    current_time = datetime.now(timezone.utc)

                    logger.info(f"Still in mining era current-{current_time}  end-{mining_era_end_time}")
                    if current_time > mining_era_end_time:
                        logger.info(f"Claiming farmed cexp")
                        await self.claimFarm(http_client=http_client,tg_web_data=tg_web_data)
                        logger.info(f"Sleep 4s")
                        await asyncio.sleep(delay=4)
                        logger.info(f"Starting Farm")
                        await self.startFarm(http_client=http_client,tg_web_data=tg_web_data)
                    



                except InvalidSession as error:
                    raise error

                except Exception as error:
                    logger.error(f"{self.session_name} | Unknown error: {error}")
                    await asyncio.sleep(delay=7)

                else:
                    sleep_between_clicks = randint(a=settings.SLEEP_BETWEEN_SLAP[0], b=settings.SLEEP_BETWEEN_SLAP[1])
                    logger.info(f"Sleep {sleep_between_clicks}s")
                    await asyncio.sleep(delay=sleep_between_clicks)


async def run_slapper(tg_client: Client, proxy: str | None):
    try:
        await Slapper(tg_client=tg_client).run(proxy=proxy)
    except InvalidSession:
        logger.error(f"{tg_client.name} | Invalid Session")
