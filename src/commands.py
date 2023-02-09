from datetime import date
from unittest import mock

import aiohttp
import aiosqlite
from nextcord import Color, Embed, Interaction, Message, slash_command
from nextcord.abc import GuildChannel
from nextcord.ext import commands
from redis.asyncio import Redis


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.redis: Redis = bot.redis

    @slash_command(description="Set the channel for the bot to send alerts to.")
    async def set_alerts_channel(self, interaction: Interaction, channel: GuildChannel):
        async with aiosqlite.connect('bot.db') as db:
            cursor = await db.cursor()
            await cursor.execute("""
                INSERT INTO bot_settings (name, value)
                VALUES (?, ?)
                ON CONFLICT (name)
                DO UPDATE SET value = excluded.value
            """, ("alert_channel", str(channel.id)))

            await db.commit()
            await interaction.send(f"Successfully set alert channel to {channel.mention}.")

    @slash_command(description="Gets a realtime status check on all of our infrastructure.")
    async def status_check(self, interaction: Interaction):
        websocket_connected = self.bot.websocket_connected  # type: int
        last_websocket_message = self.bot.last_websocket_message

        leaderboard_endpoint = {
            "url": "https://api.beatleader.xyz/v3/scores/518FD81AC6FDBFD050AB8FAC7C6AE7D73E16257A/Expert/Standard/standard/global/around",
            "params": {
                "player": "76561198157672038",
                "count": 10
            }
        }

        player_endpoint = {
            "url": "https://api.beatleader.xyz/player/3225556157461414",
            "params": {
                "stats": "true"
            }
        }

        status_embed = Embed()
        status_embed.title = "Running a status check..."
        status_embed.set_thumbnail(
            "https://cdn.discordapp.com/attachments/1068292632855457882/1073006248523477122/staging-spin.gif")

        status_embed.description = "This might take a few seconds..."
        status_embed.color = Color.orange()

        message = await interaction.send(embed=status_embed)

        failed_errors = ""
        failed_checks = 0
        services_out = "" + "**``Services``**:\n"

        # Check if the main server is running by checking the current WebSocket connection
        if websocket_connected:  # TODO: Add "degraded" check for stale websocket
            services_out += "<a:bl_pet:1073010219313021069> Main Server is **UP**.\n"
        else:
            services_out += "<a:bl_onfire:1073008674882211951> Main Server is **DOWN**.\n"
            failed_checks += 1

        status_embed.description = services_out
        await message.edit(embed=status_embed)

        # Run checks against the API endpoints
        async with aiohttp.ClientSession() as session:
            # ? Leaderboard
            async with session.get(leaderboard_endpoint["url"], params=leaderboard_endpoint["params"]) as resp:
                if resp.status >= 400:
                    services_out += "<a:bl_onfire:1073008674882211951> Leaderboards are **DOWN**\n"
                    failed_checks += 1
                else:
                    services_out += "<a:bl_pet:1073010219313021069> Leaderboards are **UP**\n"

            status_embed.description = services_out
            await message.edit(embed=status_embed)

            async with session.get(player_endpoint["url"], params=player_endpoint["params"]) as resp:
                if resp.status >= 400:
                    services_out += "<a:bl_onfire:1073008674882211951> Profiles are **DOWN**\n"
                    failed_checks += 1
                else:
                    services_out += "<a:bl_pet:1073010219313021069> Profiles are **UP**\n"

            status_embed.description = services_out
            await message.edit(embed=status_embed)

        # Final
        if failed_checks == 0:
            async with aiohttp.ClientSession() as session:
                async with session.get("https://api.waifu.pics/sfw/smug") as resp:
                    waifu = await resp.json()
                    status_embed.set_image(waifu["url"])

            status_embed.title = "Server Status"
            status_embed.set_thumbnail(
                "https://cdn.discordapp.com/emojis/1073015370497147051.webp?quality=lossless")
            status_embed.color = Color.green()

            services_out += "\n**All services operational**"

        else:
            status_embed.color = Color.red()
            status_embed.title = "Server Status"
            status_embed.set_thumbnail(
                "https://cdn.discordapp.com/emojis/1073015375060545566.webp?quality=lossless")
            status_embed.set_image(
                "https://i.waifu.pics/UhbtpTF.gif")

            services_out += f"\n**Some services are not operational.**"

            await message.channel.send(content="<@698212038106677259> THE SERVER IS ON FIRE.") # type: ignore

        status_embed.description = services_out
        await message.edit(embed=status_embed)
