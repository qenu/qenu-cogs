import json
from pathlib import Path

from redbot.core.bot import Red
from .ocr import OCR

async def setup(bot: Red) -> None:
    bot.add_cog(OCR(bot))
