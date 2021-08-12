import json
from pathlib import Path

from redbot.core.bot import Red
from .timedch import Timedchannel


async def setup(bot: Red) -> None:
    bot.add_cog(Timedchannel(bot))
