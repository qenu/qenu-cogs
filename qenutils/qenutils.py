import socket
from time import time
from typing import Literal, Optional, Union
import re

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import humanize_list


RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]
SNOWFLAKE_THRESHOLD = 2 ** 63

class Qenutils(commands.Cog):
    """
    Utility cogs from qenu
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x4ACED80C50E0BBDF,
            force_registration=True,
        )

        default_global = {
            "server_link": "",
            "invite_link": False,
        }

        self.config.register_global(**default_global)

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
        """sets the support server or invite link on ping"""
        pass

    @on_bot_ping.command(name="invite")
    async def show_invite(self, ctx: commands.Context, on_off: Optional[bool]):
        """choose to show or not show the invite"""
        if on_off is None:
            settings = await self.config.invite_link()
            return await ctx.reply(
                embed=discord.Embed(
                    description=f"Invites currently will {'' if settings else 'not '}show on bot ping.\n`You can append on or off to change this.`",
                    color=await ctx.embed_color(),
                ),
                mention_author=False,
            )
        await self.config.invite_link.set(on_off)
        return await ctx.reply(
            embed=discord.Embed(
                description=f"Invite links are now **{'enabled'if on_off else 'disabled'}**.",
                color=await ctx.embed_color(),
            ),
            mention_author=False,
        )

    @on_bot_ping.command(name="server")
    async def set_server(self, ctx: commands.Context, invite_link: Optional[str]):
        """sets bots support server, leave blank to unset"""
        if invite_link is None:
            await self.config.server_link.set("")
        else:
            await self.config.server_link.set(invite_link)
        return await ctx.reply(
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
        prefixes = await self.bot.get_prefix(message.channel)
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

            descript += f"\nNeed some help? Join my [support server!]({link})"

        if await self.config.invite_link():
            descript += (
                f"\nLooking to invite me? [Click here!]({await self._invite_url()})"
            )

        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel),
            description=descript,
        )
        await message.reply(embed=embed, mention_author=False)
