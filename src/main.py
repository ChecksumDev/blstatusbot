import logging
from collections import deque
from os import getenv

from aiosqlite import connect
from dotenv import load_dotenv
from nextcord import Activity, ActivityType, Status
from nextcord.ext import commands

from commands import Commands
from events import Events
from modules.beatleader import BeatLeader

load_dotenv()

logging.basicConfig(level=logging.INFO)


class Client(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Global Variables
        self.sl = deque(maxlen=30)
        self.average_latency = 0

        self.add_cog(Events(self))
        self.add_cog(Commands(self))
        self.add_cog(BeatLeader(self))


client = Client(
    activity=Activity(type=ActivityType.playing,
                      name="Disconnected from BeatLeader"),
    status=Status.dnd)

client.run(getenv("DISCORD_TOKEN"))
