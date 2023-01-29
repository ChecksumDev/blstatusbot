import asyncio
from logging import Handler
from typing import Optional
import aiosqlite

from nextcord import Color, Embed, Game, Message, Status, TextChannel
from websockets.exceptions import ConnectionClosed, ConnectionClosedOK

# TODO: Use the official BeatLeader CDN and or set these as configurable?
OFFLINE_IMG = 'https://cdn.discordapp.com/attachments/1068292632855457882/1068292758755885066/offline.png'
ONLINE_IMG = 'https://cdn.discordapp.com/attachments/1068292632855457882/1068292759045283840/online.png'
CONNECTING_IMG = 'https://cdn.discordapp.com/attachments/1068292632855457882/1068292759389225121/reconnecting.png'
CLOUDFLARE_IMG = 'https://media.discordapp.net/attachments/1068292632855457882/1068292759666044958/cloudflare.png'


class StatusManager:
    def __init__(self, bl) -> None:
        self.bl = bl

        self.reconnect_attempts = 0
        self.reconnect_message: Optional[Message] = None

    async def _pre_handle(self, status):
        if status == 0:
            await self.bl.bot.change_presence(activity=Game('Reconnecting to BeatLeader...'), status=Status.idle)
        else:
            self.reconnect_attempts = 0
            self.reconnect_message = None

            await self.bl.bot.change_presence(activity=Game('Connected to BeatLeader!'), status=Status.online)

    async def _post_handle(self):
        # TODO: Not implemented, no use yet.
        pass

    async def _get_channel(self) -> Optional[int]:
        async with aiosqlite.connect('bot.db') as db:
            cursor = await db.cursor()
            await cursor.execute("SELECT value FROM bot_settings WHERE name='alert_channel'")
            result = await cursor.fetchone()

        return int(result[0]) if result else None

    async def handle_connect(self):
        await self._pre_handle(1)
        channel_id = await self._get_channel()

        if channel_id is None:
            return

        channel: TextChannel = self.bl.bot.get_channel(channel_id)

        embed = Embed(color=Color.green())
        embed.set_author(name='Connected to the WebSocket',
                         icon_url=ONLINE_IMG)

        await channel.send(embed=embed)

        return await self._post_handle()

    async def handle_close(self, exception: Optional[ConnectionClosedOK | ConnectionClosed] = None):
        await self._pre_handle(0)
        channel_id = await self._get_channel()

        if channel_id is None:
            return

        channel: TextChannel = self.bl.bot.get_channel(channel_id)

        # An error has occured, lets dig in
        if exception is not None:
            if 'cloudflare' in exception.reason.lower():  # is this cloudflare related?
                embed = Embed(color=Color.orange(), description=f"```{exception}```").set_author(
                    name='CloudFlare closed WebSocket connection, reconnecting...', icon_url=CLOUDFLARE_IMG)

                self.reconnect_message = await channel.send(embed=embed)
                return await self._post_handle()

            # non graceful termination
            embed = Embed(color=Color.red(), description=f"```{exception}```").set_author(
                name='Server terminated WebSocket connection, reconnecting...', icon_url=OFFLINE_IMG)

            self.reconnect_message = await channel.send(embed=embed)
            return await self._post_handle()

        # Graceful closure (no exceptions)
        embed = Embed(color=Color.blue()).set_author(
            name='Server gracefully closed WebSocket connection, reconnecting...', icon_url=CONNECTING_IMG)

        self.reconnect_message = await channel.send(embed=embed)

    async def handle_exception(self, exception: Exception):
        await self._pre_handle(0)
        channel_id = await self._get_channel()

        if channel_id is None:
            return

        channel: TextChannel = self.bl.bot.get_channel(channel_id)

        embed = Embed(description=f"```{exception}```", color=Color.red()).set_author(
            name='An unexpected exception has occured on the WebSocket connection, reconnecting...',
            icon_url=OFFLINE_IMG)

        self.reconnect_message = await channel.send(embed=embed)


# Thanks @NSGolova for this ingenius solution.
class WSLogHandler(Handler):
    def __init__(self, sm: StatusManager):
        super().__init__()
        self.sm = sm

    def emit(self, record):
        if "! connect failed again; retrying" in record.msg:
            self.sm.reconnect_attempts += 1

            if self.sm.reconnect_message is not None:
                embed = self.sm.reconnect_message.embeds[0]
                embed.set_footer(
                    text=f"Reconnection attempts: {self.sm.reconnect_attempts}")

                asyncio.create_task(
                    self.sm.reconnect_message.edit(embed=embed))
