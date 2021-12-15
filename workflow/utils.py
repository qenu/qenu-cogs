import asyncio
from typing import Any

import discord
from redbot.core import commands
import contextlib

RED_TICK = "<:redTick:901080156217704478>"
GREEN_TICK = "<:greenTick:901080153873068052>"
GREY_TICK = "<:greyTick:901080154992967691>"
TYPING = "<:typing:901080160680419419>"


async def replying(ctx: commands.Context,
    **kwargs: Any
):
    """better reply"""
    mention_author = kwargs.get("mention_author", False)
    content = kwargs.get("content", None)
    embed = kwargs.get("embed", None)
    response = await ctx.reply(
        content=content,
        embed=embed,
        mention_author=mention_author,
    )

    await response.add_reaction(RED_TICK)

    try:
        reaction, user = await ctx.bot.wait_for(
            "reaction_add",
            timeout=60.0,
            check=lambda reaction, user: user.id == ctx.author.id
            and str(reaction.emoji) == RED_TICK
            and reaction.message.id == response.id,
        )
    except asyncio.TimeoutError:
        with contextlib.suppress(discord.HTTPException, discord.errors.NotFound):
            await response.remove_reaction(RED_TICK, ctx.me)

    else:
        with contextlib.suppress(discord.HTTPException, discord.errors.NotFound):
            await response.delete()



async def send_x(ctx: commands.Context,
    **kwargs: Any
):
    """better send"""
    content = kwargs.get("content", None)
    embed = kwargs.get("embed", None)
    response = await ctx.send(
        content=content,
        embed=embed,
    )

    await response.add_reaction(RED_TICK)

    try:
        reaction, user = await ctx.bot.wait_for(
            "reaction_add",
            timeout=60.0,
            check=lambda reaction, user: user.id == ctx.author.id
            and str(reaction.emoji) == RED_TICK
            and reaction.message.id == response.id,
        )
    except asyncio.TimeoutError:
        with contextlib.suppress(discord.HTTPException, discord.errors.NotFound):
            await response.remove_reaction(RED_TICK, ctx.me)

    else:
        with contextlib.suppress(discord.HTTPException, discord.errors.NotFound):
            await response.delete()
