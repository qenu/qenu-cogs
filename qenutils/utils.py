import discord
import asyncio
from typing import Optional, List, Any, Dict
from redbot.core import commands
import contextlib

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


# class Selection(discord.ui.View):
#     def __init__(self, *, placeholder: str, **kwargs: Any):
#         super().__init__(timeout=60)
#         self.placeholder = placeholder
#         self.ctx = kwargs.get("ctx", None)
#         self.message = kwargs.get("message", None)
#         self._selection = {}
#         print("Selection created.")

#     def add(
#         self,
#         *,
#         embed: discord.Embed,
#         description: str,
#         title: Optional[str] = None,
#         emoji: Optional[str] = None
#     ):
#         """Adds a page for the selection menu

#         embed:  discord.Embed
#             The embed page used as a page
#         description:    str
#             Brief description that will should under the selection
#         title:  Optional[str]
#             Title of sub-menu, will default to embed title if leave blank
#         emoji:  Optional[str]
#             The emote used infront of select title
#         """
#         if isinstance(title, type(None)):
#             title = embed.title
#         self._selection[title] = {
#             "Embed": embed,
#             "SelectOption": discord.SelectOption(
#                 label=title,
#                 description=description,
#                 emoji=emoji,
#             ),
#         }

#     def make(self):
#         self.add_item(
#             Dropdown(
#                 placeholder=self.placeholder,
#                 message=self.message,
#                 selection=self._selection,
#                 ctx=self.ctx,
#             )
#         )

#     async def on_timeout(self):
#         for item in self.children:
#             item.disabled = True
#         self.clear_items()
#         self.stop()

#     async def interaction_check(self, interaction: discord.Interaction):
#         """Just extends the default reaction_check to use owner_ids"""
#         if interaction.user.id not in (*self.ctx.bot.owner_ids, self.ctx.author.id):
#             await interaction.response.send_message(
#                 content="This is not your dropdown. \U0001f90c",
#                 ephemeral=True,
#             )
#             return False
#         return True


# class Dropdown(discord.ui.Select):
#     def __init__(
#         self, placeholder: str, message: discord.Message, selection: dict, **kwargs: Any
#     ):
#         self.selects = [item["SelectOption"] for item in selection.values()]
#         super().__init__(
#             placeholder=placeholder,
#             min_values=1,
#             max_values=1,
#             options=self.selects,
#         )
#         self.selection = selection
#         self.menu_message = message
#         self.ctx = kwargs.get("ctx", None)

#     async def callback(self, interaction: discord.Interaction):
#         await interaction.response.defer()
#         # a response can only be triggered once,
#         await self.menu_message.edit(
#             embed=self.selection[self.values[0]]["Embed"],
#             allowed_mentions=discord.AllowedMentions.none(),
#         )
