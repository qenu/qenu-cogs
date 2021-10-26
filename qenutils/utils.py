import discord
import asyncio
from typing import Optional
from redbot.core import commands

CROSS_MRK = "❌"


async def replying(
    ctx: commands.Context,
    embed: Optional[discord.Embed] = None,
    content: Optional[str] = None,
    mention_author: Optional[bool] = False,
    delete_after: Optional[float] = 10,
):
    """better reply"""
    response = await ctx.reply(
        content=content,
        embed=embed,
        mention_author=mention_author,
        delete_after=delete_after,
    )

    await response.add_reaction(CROSS_MRK)

    try:
        reaction, user = await ctx.bot.wait_for(
            "reaction_add",
            timeout=30.0,
            check=lambda reaction, user: user == ctx.author
            and str(reaction.emoji) == CROSS_MRK
            and reaction.message.id == response.id,
        )
    except asyncio.TimeoutError:
        await response.remove_reaction(CROSS_MRK, ctx.me)
    else:
        await response.delete()
