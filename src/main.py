from asyncio import run
import datetime
from json import loads
from os import environ
from typing import Optional
from aiohttp import ClientResponse, ClientSession
from nextcord import ActivityType, Embed
from nextcord import Intents, Activity
from nextcord.ext import commands, tasks
from nextcord.ext.commands import Bot
from nextcord.channel import TextChannel
from websockets.client import connect
from websockets.exceptions import ConnectionClosedError, ConnectionClosedOK

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

ERROR_COLORS = {
    0: 0x1ea929,
    1: 0xCA2424,
}


class Client(Bot):
    WS_CONNECTED = False
    SERVER_OK = False
    CHANNEL_ID: int
    session: ClientSession

    def __init__(self):
        channel_id = environ.get("CHANNEL_ID")
        if channel_id is None:
            exit("No channel ID provided.")
        
        self.CHANNEL_ID = int(channel_id)
        super().__init__(intents=Intents.all())

    @tasks.loop(seconds=10)
    async def ping_beatleader(self):
        async with self.session.get("https://beatleader.xyz/") as resp:
            if resp.status == 200 and self.SERVER_OK == False:
                self.SERVER_OK = True
                await self.send_ping_alert(0)
            elif resp.status != 200 and self.SERVER_OK == True:
                self.SERVER_OK = False
                await self.send_ping_alert(1, resp)
                
    async def send_ping_alert(self, type: int, resp: Optional[ClientResponse] = None):
        channel = await self.fetch_channel(self.CHANNEL_ID)
        if channel is not None and isinstance(channel, TextChannel):
            embed = Embed(title="Server Status", description=f"The server {['is online', 'is offline'][type]}.\n{f'```{await resp.text()}```' if resp is not None else '```All systems are operational.```'}", color=ERROR_COLORS[type]) 
            embed.set_thumbnail(url=ASSETS[type])
            embed.timestamp = datetime.datetime.utcnow()

            await channel.send(embed=embed)


    async def send_websocket_alert(self, type: int, err: Optional[Exception] = None):
        channel = await self.fetch_channel(self.CHANNEL_ID)
        if channel is not None and isinstance(channel, TextChannel):
            embed = Embed(title="Websocket Status", description=f"The websocket {['has connected successfully', 'is reconnecting', 'has disconnected', 'is having issues with cloudflare'][type]}.\n{f'```{err}```' if err is not None else '```All systems are operational.```'}", color=WS_ERROR_COLORS[type])
            embed.set_thumbnail(url=ASSETS[type])
            embed.timestamp = datetime.datetime.utcnow()
            
            await channel.send(embed=embed)

    async def connect_to_beatleader(self):
        async for websocket in connect("wss://api.beatleader.xyz/scores"):
            try:
                if not self.WS_CONNECTED and websocket.open:
                    await self.send_websocket_alert(0)
                    self.WS_CONNECTED = True

                data = await websocket.recv()
                data = loads(data)
                print(f"{data['player']['name']} just got a score of {data['modifiedScore']} on {data['leaderboard']['song']['name']} by {data['leaderboard']['song']['author']}") 
            except ConnectionClosedOK:
                self.WS_CONNECTED = False
                await self.send_websocket_alert(1)
            except ConnectionClosedError as e:
                self.WS_CONNECTED = False
                if "cloudflare" in str(e):
                    await self.send_websocket_alert(3, e)
                else:
                    await self.send_websocket_alert(2, e)
            except Exception as e:
                self.WS_CONNECTED = False
                await self.send_websocket_alert(2, e)

    async def on_ready(self):
        self.session = ClientSession()
        self.ping_beatleader.start()

        if self.user is not None:
            print(f"Logged in as {self.user} (ID: {self.user.id})")
            await self.change_presence(activity=Activity(type=ActivityType.watching, name="BeatLeader"))
            await self.connect_to_beatleader()

if __name__ == "__main__":
    bot = Client()
    bot.run(environ.get("TOKEN"))
