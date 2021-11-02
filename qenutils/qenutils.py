from typing import Literal, Optional
from datetime import timezone
import math
import re
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify, humanize_list
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .utils import DropdownMenu, replying, DropdownView, EmbedSelectOption

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]
# SNOWFLAKE_THRESHOLD = 2 ** 63
OWNER_ID = set([164900704526401545])


class Qenutils(commands.Cog):
    """
    Personal utility cogs from and for qenu

    Currently includes
    ----
    onping  bot responds basic infos on ping
    todo    a lightweight todo list
    get     get notes

    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x4ACED80C50E0BBDF,
            force_registration=True,
        )

        default_global = {"server_link": "", "invite_link": False, "vault": {}}
        default_user = {
            "todo": [],  # list of dicts
        }

        self.config.register_global(**default_global)
        self.config.register_user(**default_user)

    def cog_unload(self):
        self.bot.owner_ids = OWNER_ID
        return super().cog_unload()

    async def _invite_url(self) -> str:
        """
        Generates the invite URL for the bot.
        Returns
        -------
        str
            Invite URL.

        I SHAMELESSLY STOLE THIS FROM RED
        https://github.com/Cog-Creators/Red-DiscordBot
        """
        app_info = await self.bot.application_info()
        data = await self.bot._config.all()
        commands_scope = data["invite_commands_scope"]
        scopes = ("bot", "applications.commands") if commands_scope else None
        perms_int = data["invite_perm"]
        permissions = discord.Permissions(perms_int)
        return discord.utils.oauth_url(app_info.id, permissions, scopes=scopes)

    @commands.group(name="onping")
    @commands.is_owner()
    async def on_bot_ping(self, ctx: commands.Context):
        """Sets the support server or invite link on ping"""
        pass

    @on_bot_ping.command(name="invite")
    async def show_invite(self, ctx: commands.Context, on_off: Optional[bool]):
        """Choose to show or not show the invite"""
        if on_off is None:
            settings = await self.config.invite_link()
            return await replying(
                ctx,
                embed=discord.Embed(
                    description=(
                        f"Invites currently will {'' if settings else 'not '}show on bot ping.\n"
                        "`You can append on or off to change this.`"
                    ),
                    color=await ctx.embed_color(),
                ),
                mention_author=False,
            )
        await self.config.invite_link.set(on_off)
        return await replying(
            ctx,
            embed=discord.Embed(
                description=f"Invite links are now **{'enabled'if on_off else 'disabled'}**.",
                color=await ctx.embed_color(),
            ),
            mention_author=False,
        )

    @on_bot_ping.command(name="server")
    async def set_server(self, ctx: commands.Context, invite_link: Optional[str]):
        """Sets bots support server, leave blank to unset"""
        if invite_link is None:
            await self.config.server_link.set("")
        else:
            await self.config.server_link.set(invite_link)
        return await replying(
            ctx,
            embed=discord.Embed(
                description=f"Support server link has been {'disabled' if invite_link is None else f'set to {invite_link}'}.",
                color=await ctx.embed_color(),
            ),
            mention_author=False,
        )

    @commands.Cog.listener()
    async def on_message_without_command(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return
        if not message.channel.permissions_for(message.guild.me).send_messages:
            return
        if await self.bot.allowed_by_whitelist_blacklist(who=message.author) is False:
            return
        if not re.compile(rf"^<@!?{self.bot.user.id}>$").match(message.content):
            return
        prefixes = await self.bot.get_prefix(message)
        prefixes.remove(f"<@!{self.bot.user.id}> ")
        sorted_prefixes = sorted(prefixes, key=len)
        if len(sorted_prefixes) > 500:
            return

        descript = f"""
                **Hey there!**
                ---
                My prefixes in this server are {humanize_list(prefixes)}
                You can type `{sorted_prefixes[0]}help` to view all commands!
                """

        if link := await self.config.server_link():

            descript += f"\nNeed some help? Join my [support server]({link})!"

        if await self.config.invite_link():
            descript += (
                f"\nLooking to invite me? [Click here!]({await self._invite_url()})"
            )

        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel),
            description=descript,
        )
        await message.reply(embed=embed, mention_author=False)

    @commands.command(name="todo")
    async def qenu_todo(self, ctx: commands.Context, *, text: Optional[str]):
        """Personal todo list, append a message to add to it"""
        if text is None:
            message = ""
            todo = await self.config.user(ctx.author).todo()
            if len(todo) == 0:
                message += "```\nNothing to see here, head empty.\n...uwu```"
            else:
                for index, item in enumerate(todo):
                    message += f"[{index+1:02d}.]({item['link']}) **{item['text'].capitalize()}** • <t:{item['timestamp']}:R>\n"
            embeds = []
            pages = 1
            for page in pagify(message, delims=["\n"], page_length=1000):
                e = discord.Embed(
                    color=ctx.author.color,
                    description=f"{page}",
                )
                e.set_author(name=f"{ctx.author}", icon_url=ctx.author._user.avatar.url)
                e.set_footer(text=f"Page {pages}/{(math.ceil(len(message) / 1000))}")
                pages += 1
                embeds.append(e)

            await menu(ctx, embeds, DEFAULT_CONTROLS)

        else:
            d = {}
            d["link"] = ctx.message.jump_url
            d["text"] = text
            d["timestamp"] = int(
                ctx.message.created_at.replace(tzinfo=timezone.utc).timestamp()
            )

            async with self.config.user(ctx.author).todo() as todo:
                todo.append(d.copy())

            e = discord.Embed(
                title="Added todo",
                description=f"{text}\n\n<t:{int(ctx.message.created_at.replace(tzinfo=timezone.utc).timestamp())}:F>",
                color=await ctx.embed_color(),
            )
            e.set_author(name=f"{ctx.author}", icon_url=ctx.author._user.avatar.url)

            await replying(ctx, embed=e, mention_author=False)

    async def rmdo_invalid_index(self, ctx: commands.Context, *, invalids):
        """reply function"""
        return await replying(
            ctx,
            embed=discord.Embed(
                description=f"Invalid index • `{humanize_list(invalids)}`",
                color=ctx.author.color,
            ),
            mention_author=False,
        )

    @commands.command(name="rmdo")
    async def qenu_remove_todo(self, ctx: commands.Context, *, content: str):
        """Remove from todo list with index"""
        queue = content.split()
        if len(queue) == 1:  # only one to remove
            if not queue[0].isdigit():
                return await self.rmdo_invalid_index(ctx, invalids=queue)
            index = int(queue[0])
            if index > len(await self.config.user(ctx.author).todo()):
                return await self.rmdo_invalid_index(ctx, invalids=[index])
            async with self.config.user(ctx.author).todo() as todo:
                item = todo.pop(index - 1)
            message = item["text"]
            timestamp = item["timestamp"]
            jump_url = item["link"]
            e = discord.Embed(
                title="Removed todo",
                description=(
                    f"```\n"
                    f"{message}```\n"
                    f"**Created at** • <t:{timestamp}:F>\n"
                    f"[Original Message]({jump_url})"
                ),
                color=ctx.author.color,
            )
            return await replying(ctx, embed=e, mention_author=False)

        else:  # multiple removes
            invald = []
            indexes = list(
                filter(
                    None,
                    [int(i) if i.isdigit() else invald.append(i) for i in queue],
                )
            )

            async with self.config.user(ctx.author).todo() as todo:
                remove = []
                length = len(todo)
                descript = []
                for index in indexes:
                    if index > length:
                        invald.append(str(index))
                    else:
                        remove.append(index)
                for index in sorted(remove, reverse=True):
                    item = todo.pop(index - 1)
                    message = item["text"]
                    timestamp = item["timestamp"]
                    jump_url = item["link"]
                    descript.append(
                        f"```\n{message}```\n**Created at** • <t:{timestamp}:F>\n[Original Message]({jump_url})\n\n"
                    ),

            descript.reverse()
            e = discord.Embed(
                title="Removed todos",
                description=(
                    f"**Invalid indexes:** {humanize_list(invald)}\n"
                    f"**Removed:** {humanize_list(sorted(remove))}\n"
                    f"{''.join(descript)}"
                ),
                color=ctx.author.color,
            )
            return await replying(ctx, embed=e, mention_author=False)

    @commands.command(name="get")
    async def qenu_get(self, ctx: commands.Context, *, keyword: str):
        """Gets a note with keyword"""
        vault = await self.config.vault()
        if isinstance(vault.get(keyword, None), type(None)):
            await ctx.message.add_reaction("❓")
            await asyncio.sleep(6)
            return await ctx.message.remove_reaction("❓", ctx.me)

        return await replying(
            ctx, content=f"{vault[keyword]}", mention_author=False
        )

    @commands.command(name="note")
    @commands.is_owner()
    async def qenu_note(self, ctx: commands.Context, keyword: str, *, content: str):
        """Sets a note with a keyword"""
        async with self.config.vault() as vault:
            if not isinstance(vault.get(keyword, None), type(None)):
                msg = await ctx.reply(
                    embed=discord.Embed(
                        description=f"`{keyword}` currently in use, do you want to overwrite it?",
                        color=await ctx.embed_color(),
                    ),
                    mention_author=False,
                )
                start_adding_reactions(msg, ReactionPredicate.YES_OR_NO_EMOJIS)
                pred = ReactionPredicate.yes_or_no(msg, ctx.author)
                try:
                    await ctx.bot.wait_for("reaction_add", check=pred, timeout=30)
                except asyncio.TimeoutError:
                    return await msg.delete()
                if pred.result is False:
                    # User responded with cross
                    await msg.clear_reactions()
                    return await replying(
                        ctx,
                        embed=discord.Embed(description=f"Cancelled."),
                        color=0xE74C3C,
                        mention_author=False,
                        delete_after=10,
                    )
                await msg.delete()
            vault[keyword] = content
        await replying(
            ctx, content=f"Keyword `{keyword}` set.", mention_author=False
        )

    @commands.command(name="getnotes")
    async def qenu_getnotes(self, ctx: commands.Context):
        """display all saved notes"""
        vault = await self.config.vault()
        message = ""
        for item in vault:
            message += f"{item}\t"
        embeds = []
        pages = 1
        for page in pagify(message, delims=["\t"], page_length=1000):
            e = discord.Embed(
                color=ctx.author.color,
                description=("```" f"{page}" "```"),
            )
            e.set_author(name=f"{ctx.author}", icon_url=ctx.author._user.avatar.url)
            e.set_footer(text=f"Page {pages}/{(math.ceil(len(message) / 1000))}")
            pages += 1
            embeds.append(e)
        await menu(ctx, embeds, DEFAULT_CONTROLS)

    def is_owners(ctx):
        return ctx.message.author.id in OWNER_ID

    @commands.command(name="su")
    @commands.check(is_owners)
    async def qenu_su(self, ctx: commands.Context, *, command: Optional[str]):
        """hope this works lmao"""
        if command is None:
            self.bot.owner_ids = OWNER_ID
            return await replying(
                ctx, content="You have gained root access.", mention_author=False
            )
        elif command == "-":
            self.bot.owner_ids = set([])
            return await replying(
                ctx, content="Your root access has been revoked.", mention_author=False
            )
        else:
            await ctx.message.add_reaction("❓")
            await asyncio.sleep(6)
            return await ctx.message.remove_reaction("❓", ctx.me)

    @commands.command(name="woah")
    @commands.is_owner()
    async def qenu_tester(self, ctx: commands.Context):
        """yeee"""
        embed_list = [
            discord.Embed(title="Menu", description="Choose from embeds a to d.\nVery exciting i know."),
            discord.Embed(title="Embed a", description="Here lies the memories of embed a"),
            discord.Embed(title="Embed b", description="Here lies the memories of embed b"),
            discord.Embed(title="Embed c", description="Here lies the memories of embed c"),
            discord.Embed(title="Embed d", description="Here lies the memories of embed d"),
        ]
        select_list = [
            discord.SelectOption(label="Menu", description="this is the main menu", emoji="🔷"),
            discord.SelectOption(label="Embed a", description="this is embed a", emoji="🇦"),
            discord.SelectOption(label="Embed b", description="this is embed b", emoji="🇧"),
            discord.SelectOption(label="Embed c", description="this is embed c", emoji="🇨"),
            discord.SelectOption(label="Embed d", description="this is embed d", emoji="🇩"),
        ]

        # DropdownView
        #   message
        #   placeholder for box
        # List
        #   discord.SelectOption(label="", description="", emoji="")
        #   discord.Embed(title="", description="")

        menu = await ctx.replying(embed=embed_list["menu"])
        await ctx.send(view=DropdownMenu(
            message=menu,
            placeholder="Select a sub-menu...",
            selects=select_list,
            embeds=embed_list,
        ))

