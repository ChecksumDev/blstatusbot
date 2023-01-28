from logging import getLogger
from statistics import mean

import aiosqlite
from nextcord import Color, Embed, TextChannel
from nextcord.ext import commands, tasks
from tcp_latency import measure_latency
from websockets.client import connect as ws_connect
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

from modules.status_manager import CLOUDFLARE_IMG, StatusManager, WSLogHandler
from version import VERSION

# TODO: Make this configurable by bot commands in the database
BOT_CHANNEL = 1067871362032611370


class BeatLeader(commands.Cog):
    def __init__(self, bot):
        self.ws_con_msg_id = None
        self.ws_con_attempts = None

        self.bot = bot

        self.get_beatleader_latency.start()
        self.bot.loop.create_task(self._pre_start())

    async def _pre_start(self):
        await self.bot.wait_until_ready()

        self.channel: TextChannel = self.bot.get_channel(BOT_CHANNEL)  # type: ignore
        self.status_manager = StatusManager(self)

        async with aiosqlite.connect('bot.db') as db:
            await self.init_db(db)

            async with db.execute("SELECT version FROM meta") as cursor:
                version = await cursor.fetchone()
                if version:
                    if version[0] != VERSION:
                        # If we have updated, update the version in the DB
                        await db.execute("UPDATE meta SET version = ?", (VERSION,))
                        await db.commit()

                        # Send an embed into the discord channel
                        embed = Embed()
                        embed.color = Color.orange()
                        embed.set_author(
                            name=f"The bot has been updated to v{VERSION}.", icon_url=CLOUDFLARE_IMG)

                        await self.channel.send(embed=embed)  # type: ignore
                else:
                    await db.execute("INSERT INTO meta (version) VALUES (?)", (VERSION,))
                    await db.commit()

        # Start
        await self.connect_websocket()

    async def connect_websocket(self):
        getLogger("websockets.client").addHandler(
            WSLogHandler(self.status_manager))

        async for websocket in ws_connect('wss://api.beatleader.xyz/scores'):
            self.ws_con_attempts = 0
            self.ws_con_msg_id = 0

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

    async def init_db(self, db):
        await db.execute('''CREATE TABLE IF NOT EXISTS meta
                            (version TEXT NOT NULL);''')

        await db.commit()

    @ tasks.loop(seconds=3)
    async def get_beatleader_latency(self):
        self.bot.sl.append(measure_latency('beatleader.xyz'))
        self.bot.average_latency = round(mean([x[0] for x in self.bot.sl]))

    @ get_beatleader_latency.before_loop
    async def before_my_task(self):
        await self.bot.wait_until_ready()
