from datetime import datetime, timedelta
from json import loads
from os import environ
from typing import Optional

from aiohttp import ClientResponse, ClientSession
from discord import AllowedMentions
from dotenv import load_dotenv
from nextcord import Activity, ActivityType, Embed, Intents
from nextcord.channel import TextChannel
from nextcord.ext import tasks
from nextcord.ext.commands import Bot
from websockets.client import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

from stats import (HOURLY_MAPS, HOURLY_SCORES, HOURLY_USERS, map_add,
                   score_add, user_add)

ASSETS = {
    0: "https://media.discordapp.net/attachments/1068292632855457882/1068292759045283840/online.png?width=512&height=512",
    1: "https://media.discordapp.net/attachments/1068292632855457882/1068292759389225121/reconnecting.png?width=512&height=512",
    2: "https://media.discordapp.net/attachments/1068292632855457882/1068292758755885066/offline.png?width=512&height=512",
    3: "https://media.discordapp.net/attachments/1068292632855457882/1068292759666044958/cloudflare.png?width=512&height=512"
}

WS_ERROR_COLORS = {
    0: 0x1ea929,
    1: 0x2485CA,
    2: 0xCA2424,
    3: 0xca7f24
}

HTTP_ERROR_COLORS = {
    0: 0x1ea929,
    1: 0xCA2424,
}

class Client(Bot):
    WS_CONNECTED = False
    SERVER_OK = False
    CHANNEL_ID: int
    ROLE_ID: int
    session: ClientSession
    last_score_time: datetime = None
    score_status_message = None

    def __init__(self):
        channel_id = environ.get("CHANNEL_ID")
        if channel_id is None:
            exit("No channel ID provided.")
        
        role_id = environ.get("ROLE_ID")
        if role_id is None:
            exit("No role ID provided.")

        self.CHANNEL_ID = int(channel_id)
        self.ROLE_ID = int(role_id)
        super().__init__(intents=Intents.all(), allowed_mentions=AllowedMentions.all())

    @tasks.loop(seconds=60)
    async def update_status(self):
        await self.change_presence(activity=Activity(type=ActivityType.watching, name=f"BeatLeader | {len(HOURLY_SCORES)} scores set by {len(HOURLY_USERS)} users on {len(HOURLY_MAPS)} maps in the last hour."))
        
    @tasks.loop(seconds=5)
    async def ping_beatleader(self):
        async with self.session.get("https://beatleader.xyz/") as resp:
            if resp.status == 200 and not self.SERVER_OK:
                self.SERVER_OK = True
                await self.send_ping_alert(0)
            elif resp.status != 200 and self.SERVER_OK:
                self.SERVER_OK = False
                await self.send_ping_alert(1, resp)

    @tasks.loop(seconds=10)
    async def check_score_delay(self):
        channel = await self.fetch_channel(self.CHANNEL_ID)
        if not channel:
            return

        if self.last_score_time:
            time_diff = datetime.utcnow() - self.last_score_time
            status_text = f"Last score was posted {time_diff.total_seconds() // 60} minutes and {time_diff.total_seconds() % 60} seconds ago."
        else:
            status_text = "Waiting for the first score to be posted."

        if self.score_status_message:
            await self.score_status_message.edit(content=status_text)
        else:
            self.score_status_message = await channel.send(status_text)

        if time_diff and time_diff > timedelta(minutes=1):
            await channel.send(f"<@&{self.ROLE_ID}> More than a minute has passed since the last score was posted.")
            self.score_status_message = None

    async def send_ping_alert(self, type: int, resp: Optional[ClientResponse] = None):
        channel = await self.fetch_channel(self.CHANNEL_ID)
        if channel is not None and isinstance(channel, TextChannel):
            embed = Embed(title="Server Status", description=f"The server {['is online', 'is offline'][type]}.\n{f'```{await resp.text()}```' if resp is not None else '```All systems are operational.```'}", color=HTTP_ERROR_COLORS[type]) 
            embed.set_thumbnail(url=ASSETS[type])
            embed.timestamp = datetime.utcnow()

            status_msg = await channel.send(content=f"<@&{self.ROLE_ID}>" if type != 0 else None, embed=embed)
            
            if channel.is_news():
                await status_msg.publish()

    async def send_websocket_alert(self, type: int, err: Optional[Exception] = None):
        channel = await self.fetch_channel(self.CHANNEL_ID)
        if channel is not None and isinstance(channel, TextChannel):
            embed = Embed(title="Websocket Status", description=f"The websocket {['has connected successfully', 'is reconnecting', 'has disconnected', 'is having issues with cloudflare'][type]}.\n{f'```{err}```' if err is not None else '```All systems are operational.```'}", color=WS_ERROR_COLORS[type])
            embed.set_thumbnail(url=ASSETS[type])
            embed.timestamp = datetime.utcnow()
            
            status_msg = await channel.send(content=f"<@&{self.ROLE_ID}>" if type != 0 else None, embed=embed)
            
            if channel.is_news():
                await status_msg.publish()

    async def connect_to_beatleader(self):
        async for websocket in connect("wss://api.beatleader.xyz/scores"):
            try:
                if not self.WS_CONNECTED:
                    await self.send_websocket_alert(0)
                    self.WS_CONNECTED = True

                data = await websocket.recv()
                score = loads(data)

                score_add()
                user_add(score["player"]["id"])
                map_add(score["leaderboard"]["song"]["id"])
                self.last_score_time = datetime.utcnow()

            except ConnectionClosedOK as e:
                self.WS_CONNECTED = False
                await self.send_websocket_alert(1, e)
                continue

            except ConnectionClosedError as e:
                self.WS_CONNECTED = False
                if "cloudflare" in str(e):
                    await self.send_websocket_alert(3, e)
                else:
                    await self.send_websocket_alert(2, e)
                continue
            except Exception as e:
                self.WS_CONNECTED = False
                await self.send_websocket_alert(2, e)
                continue

    async def on_ready(self):
        self.session = ClientSession()        
        self.ping_beatleader.start()
        self.update_status.start()
        self.check_score_delay.start()

        await self.connect_to_beatleader()

if __name__ == "__main__":
    load_dotenv()

    bot = Client()
    bot.run(environ.get("TOKEN"))
