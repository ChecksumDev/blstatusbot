from cooldowns import CallableOnCooldown
from discord import Interaction
from nextcord.ext import commands


class Events(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"Connected to Discord as {self.bot.user}")

    @commands.Cog.listener()
    async def on_application_command_error(self, inter: Interaction, error):
        error = getattr(error, "original", error)

        if isinstance(error, CallableOnCooldown):
            return await inter.send(
                f"You are being rate-limited! Retry in `{error.retry_after}` seconds."
            )

        await inter.send(f"An error occured while processing this command.\n:```{error}```\n<@573909482619273255>")
