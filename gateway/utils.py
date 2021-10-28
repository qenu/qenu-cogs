import discord
import asyncio
from typing import Optional
from redbot.core import commands

CROSS_MRK = "<:redTick:901080156217704478>"
TICK_MRK = "<:greenTick:901080153873068052>"
GREY_MRK = "<:greyTick:901080154992967691>"
LOADING = "<:typing:901080160680419419>"

class enutils():
    async def replying(
        self,
        ctx: commands.Context,
        embed: Optional[discord.Embed] = None,
        content: Optional[str] = None,
        mention_author: Optional[bool] = False,
    ):
        """better reply"""
        response = await ctx.reply(
            content=content,
            embed=embed,
            mention_author=mention_author,
        )

        await response.add_reaction(CROSS_MRK)

        try:
            reaction, user = await ctx.bot.wait_for(
                "reaction_add",
                timeout=30.0,
                check=lambda reaction, user:
                    user.id == ctx.author.id
                    and str(reaction.emoji) == CROSS_MRK
                    and reaction.message.id == response.id,
            )
        except asyncio.TimeoutError:
            await response.remove_reaction(CROSS_MRK, ctx.me)
        else:
            await response.delete()
