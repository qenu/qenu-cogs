import json
from pathlib import Path

from redbot.core.bot import Red
from .qenutils import Qenutils


async def setup(bot: Red) -> None:
    bot.add_cog(Qenutils(bot))
