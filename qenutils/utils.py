import discord
import asyncio
from typing import Optional, List, Any, Dict
from redbot.core import commands
import contextlib

CROSS_MRK = "<:redTick:901080156217704478>"
TICK_MRK = "<:greenTick:901080153873068052>"
GREY_MRK = "<:greyTick:901080154992967691>"
LOADING = "<:typing:901080160680419419>"


async def replying(
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
            check=lambda reaction, user: user.id == ctx.author.id
            and str(reaction.emoji) == CROSS_MRK
            and reaction.message.id == response.id,
        )
    except asyncio.TimeoutError:
        await response.remove_reaction(CROSS_MRK, ctx.me)
    else:
        await response.delete()

def EmbedSelectOption(embeddict: dict, emojis: Optional[list]=None):
    if emojis is not None:
        if len(embeddict) != len(emojis):
            raise AttributeError("Emojis and embeds must match")
    options = []
    for index, item in enumerate(embeddict):
        options.append(
            discord.SelectOption(
                label=item,
                description=embeddict[item].description,
                emoji=None if emojis is None else emojis[index]
            )
        )
    return options


class Dropdown(discord.ui.Select):
    def __init__(
        self,
        cats: List[discord.SelectOption],
        ctx: Optional[commands.Context]=None,
        placeholder: str="Select a category...",
        embeds: Optional[dict]=None,
        ):
        super().__init__(
            placeholder=placeholder,
            min_values=1,
            max_values=1,
            options=cats,
        )
        self.embeds = embeds
        self.cats = cats
        self.ctx = ctx


    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        # a response can only be triggered once,  discord.errors.InteractionResponded: This interaction has already been responded to before
        await interaction.edit_original_message(
            embed=self.embeds[self.values[0]],
            view=DropdownView(
                self.cats,
                ctx=self.ctx,
                placeholder=f"{self.values[0]}",
                embeds=self.embeds,
                )
            )
        # with contextlib.suppress(discord.HTTPException):
        #     await interaction.followup.send(
        #             content=(
        #                 "**Debug info**\n"
        #                 f"Values: {self.values}\n"
        #                 f"Type: {type(self.values[0])}\n"
        #                 f"item: {dir(self)}"
        #             )
        #         )
        # editing the original message force resets the dropdown
        # await interaction.message.delete()

class DropdownView(discord.ui.View):
    def __init__(
        self,
        cats: List[discord.SelectOption],
        ctx: Optional[commands.Context] = None,
        placeholder: str = "Select ...",
        message: discord.Message = None,
        embeds: Optional[dict]=None,
        ):
        super().__init__(timeout=60)
        # self.message = ctx.message
        self.ctx = ctx
        # self.ctx = kwargs.get("ctx", None)
        # self.config = kwargs.get("config", None)

        # Adds the dropdown to our view object.
        self.add_item(
            Dropdown(
                cats=cats,
                ctx=ctx,
                placeholder=placeholder,
                embeds=embeds,
                )
            )


    async def on_timeout(self):
        for item in self.children:
            item.disabled = True
        # self.clear_items()
        with contextlib.suppress(discord.NotFound):
            await self.message.edit(view=self)
        self.stop()

    async def interaction_check(self, interaction: discord.Interaction):
        """Just extends the default reaction_check to use owner_ids"""
        # if interaction.message.id != self.message.id:
        #     await interaction.response.send_message(
        #         content="You are not authorized to interact with this.", ephemeral=True,
        #     )
        #     return False
        if interaction.user.id not in (*self.ctx.bot.owner_ids, self.ctx.author.id):
            await interaction.response.send_message(
                content="This is not your dropdown. \U0001f928", ephemeral=True,
            )
            return False
        return True