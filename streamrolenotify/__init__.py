import json
from pathlib import Path

from redbot.core.bot import Red
from .streamrolenotify import Streamrolenotify


async def setup(bot: Red) -> None:
    bot.add_cog(streamrolenotify(bot))
