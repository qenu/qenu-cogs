import json
from pathlib import Path

from redbot.core.bot import Red
from .nitrorole import Nitrorole


async def setup(bot: Red) -> None:
    bot.add_cog(Nitrorole(bot))
