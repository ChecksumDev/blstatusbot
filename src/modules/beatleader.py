from logging import getLogger
from typing import Optional
import aiohttp
import aiosqlite
from discord import Color, Embed, TextChannel
from nextcord.ext import commands, tasks
from redis.asyncio import Redis
from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from modules.status_manager import OFFLINE_IMG, StatusManager, WSLogHandler


class BeatLeader(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis: Redis = bot.redis

        self.test_leaderboard.start()
        self.bot.loop.create_task(self.connect_websocket())

    # ? Utils
    async def _get_channel(self) -> Optional[int]:
        async with aiosqlite.connect('bot.db') as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT value FROM bot_settings WHERE name='alert_channel'")
            result = await cursor.fetchone()

        return int(result[0]) if result else None

    # ? Websocket
    async def connect_websocket(self):
        await self.bot.wait_until_ready()

        self.status_manager = StatusManager(self)
        getLogger("websockets.client").addHandler(
            WSLogHandler(self.status_manager))

        async for websocket in ws_connect('wss://api.beatleader.xyz/scores'):
            await self.status_manager.handle_connect()

            try:
                while True:
                    _ = await websocket.recv()
            except ConnectionClosedOK:
                await self.status_manager.handle_close()
            except ConnectionClosed as cle:
                await self.status_manager.handle_close(cle)
            except Exception as exception:
                await self.status_manager.handle_exception(exception)

    # ? Endpoints
    @tasks.loop(seconds=30)
    async def test_leaderboard(self):
        channel_id = await self._get_channel()
        channel: TextChannel = self.bot.get_channel(channel_id)

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.beatleader.xyz/v3/scores/518FD81AC6FDBFD050AB8FAC7C6AE7D73E16257A/Expert/Standard/standard/global/around"
                params = {
                    "player": "76561198157672038",
                    "count": 10
                }
                async with session.get(url, params=params) as resp:
                    if resp.status >= 400:
                        embed = Embed(
                            description=f"```{await resp.text()}```",
                            color=Color.red()).set_author(name='Leaderboard endpoint sent non-200 error code.', icon_url=OFFLINE_IMG)

                        await channel.send(embed=embed)

        except Exception as e:
            embed = Embed(
                description=f"```{e}```",
                color=Color.red()).set_author(name='An unexpected exception occured on the leaderboard endpoint.', icon_url=OFFLINE_IMG)

            await channel.send(embed=embed)
