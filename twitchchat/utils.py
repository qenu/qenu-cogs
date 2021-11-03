import discord
import asyncio
from typing import Optional, List, Any, Dict


RED_TICK = "<:redTick:901080156217704478>"
GREEN_TICK = "<:greenTick:901080153873068052>"
GREY_TICK = "<:greyTick:901080154992967691>"
TYPING = "<:typing:901080160680419419>"


async def replying(
    embed: Optional[discord.Embed] = None,
    content: Optional[str] = None,
    mention_author: Optional[bool] = False,
    **kwargs: Any
):
    """better reply"""
    ctx = kwargs.get("ctx", None)
    response = await ctx.reply(
        content=content,
        embed=embed,
        mention_author=mention_author,
    )

    await response.add_reaction(RED_TICK)

    try:
        reaction, user = await ctx.bot.wait_for(
            "reaction_add",
            timeout=30.0,
            check=lambda reaction, user: user.id == ctx.author.id
            and str(reaction.emoji) == RED_TICK
            and reaction.message.id == response.id,
        )
    except asyncio.TimeoutError:
        await response.remove_reaction(RED_TICK, ctx.me)
    else:
        await response.delete()
