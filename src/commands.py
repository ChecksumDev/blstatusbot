from nextcord import Interaction, slash_command
from nextcord.ext import commands


class Commands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @slash_command(description="Checks the current latency to BeatLeader")
    async def ping(self, interaction: Interaction):
        await interaction.send(content=f":ping_pong: Pong! `{self.bot.average_latency}ms`", ephemeral=True)
