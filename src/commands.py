import aiosqlite
from nextcord import Interaction, slash_command
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
