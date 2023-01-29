import logging
from os import getenv

import aiosqlite
from discord import Color, Embed, TextChannel
from dotenv import load_dotenv
from nextcord import Activity, ActivityType, Status
from nextcord.ext import commands

from commands import Commands
from events import Events
from modules.beatleader import BeatLeader
import redis.asyncio as redis
from modules.status_manager import CLOUDFLARE_IMG

from version import VERSION

load_dotenv()

logging.basicConfig(level=logging.INFO)


class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.redis = redis.Redis()
        self.loop.create_task(self.startup())

        self.add_cog(Events(self))
        self.add_cog(Commands(self))
        self.add_cog(BeatLeader(self))

    async def init_db(self, db):
        await db.execute("""CREATE TABLE IF NOT EXISTS meta
                            (version TEXT NOT NULL);""")

        await db.execute("""
                CREATE TABLE IF NOT EXISTS bot_settings (
                  name varchar(255) PRIMARY KEY,
                  value varchar(255)
                );
            """)

        await db.commit()

    async def startup(self):
        await self.wait_until_ready()

        async with aiosqlite.connect('bot.db') as db:
            await self.init_db(db)

            async with db.execute("SELECT value FROM bot_settings WHERE name='alert_channel'") as cursor:
                channel_id = await cursor.fetchone()

            # don't update internal version unless we have a channel set for notifying about it.
            if channel_id is not None:
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

                            channel: TextChannel = self.get_channel(int(channel_id[0]))  # type: ignore
                            await channel.send(embed=embed)
                    else:
                        await db.execute("INSERT INTO meta (version) VALUES (?)", (VERSION,))
                        await db.commit()

client = Client(
    activity=Activity(type=ActivityType.playing,
                      name="Disconnected from BeatLeader"),
    status=Status.dnd)

client.run(getenv("DISCORD_TOKEN"))
