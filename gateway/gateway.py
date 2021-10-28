import logging

from typing import Literal
import asyncio
import random
import string

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from . import utils

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]
_log = logging.getLogger("red.qenu.gateway")


class Gateway(commands.Cog):
    """
    Connects two TextChannels
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x11694CAB731712FC,
            force_registration=True,
        )
        default_global = {"enabled": False, "ports": (None, None)}
        self.config.register_global(**default_global)

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        return super().red_delete_data_for_user(requester=requester, user_id=user_id)

    @commands.group(name="gateway", invoke_without_command=True)
    @commands.is_owner()
    @commands.bot_has_permissions(send_messages=True, read_message_history=True)
    async def channel_gateway(self, ctx: commands.Context):
        """Bridges two channel together"""
        if ctx.invoked_subcommand is None:

            emb = discord.Embed(
                title="Gateway Status",
                description=f"Connection is currently **{'enabled' if await self.config.enabled() else 'disabled'}**.",
                color=await ctx.embed_color(),
            )
            ports = await self.config.ports()
            port_0 = self.bot.get_channel(ports[0])
            port_1 = self.bot.get_channel(ports[1])

            emb.add_field(
                name=f"{port_0.guild.name if isinstance(port_0, discord.TextChannel) else 'None'}",
                value=f"{port_0.name if isinstance(port_0, discord.TextChannel) else 'None'}",
                inline=True,
            )
            emb.add_field(
                name=f"{port_1.guild.name if isinstance(port_1, discord.TextChannel) else 'None'}",
                value=f"{port_1.name if isinstance(port_1, discord.TextChannel) else 'None'}",
                inline=True,
            )
            return await ctx.reply(embed=emb, mention_author=False)

    @channel_gateway.command(name="create", aliases=["make"])
    @commands.max_concurrency(1)
    async def channel_gateway_create(self, ctx: commands.Context):
        """Starts the process of bridging two channels"""
        react = await ctx.reply(
            content=(
                "I am about to bridge this channel with a second channel\n"
                "This will also revert all previous settings\n"
                "\n"
                "Are you sure you want to do proceed? type `I agree` to continue"
            ),
            mention_author=False,
        )

        try:
            response = await self.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda message: message.author.id == ctx.author.id
                and str(message.content).lower() == "i agree"
                and message.channel.id == ctx.channel.id,
            )
        except asyncio.TimeoutError:
            await react.delete()
            return

        verify = "".join(random.sample(string.ascii_letters, k=32))
        await react.edit(
            content=(
                "Next step, please copy this string and paste it at the channel you want me to bridge to\n"
                "Make sure that I can see/read/edit messages in that channel as well.\n"
                "\n"
                f"`{verify}`"
            ),
            mention_author=False,
        )

        try:
            portal = await self.bot.wait_for(
                "message",
                timeout=30.0,
                check=lambda message: message.author.id == ctx.author.id
                and message.content == verify,
            )
        except asyncio.TimeoutError:
            await react.delete()
            return

        await self.config.ports.set((ctx.channel.id, portal.channel.id))
        await self.config.enabled.set(True)
        emb = discord.Embed(
            description=f"Successfully created a gateway between {ctx.channel.name} & {portal.channel.name}",
            color=await ctx.embed_color(),
        )
        await react.delete()
        await ctx.send(embed=emb)
        await portal.channel.send(embed=emb)

    @channel_gateway.command(name="shutdown", aliases=["close"])
    @commands.max_concurrency(1)
    async def channel_gateway_shutdown(self, ctx: commands.Context):
        await self.config.enabled.set(False)
        await self.config.ports.set((None, None))
        await ctx.message.add_reaction(utils.TICK_MRK)

    async def _gateway(self, *, message: discord.Message, channel: discord.TextChannel):
        if channel is None:
            return
        embed = discord.Embed(description=message.content, color=message.author.color)
        embed.set_author(
            name=f"{message.author} • {message.author.id}",
            icon_url=message.author.avatar_url,
        )
        for attachment in message.attachments:
            if any(
                attachment.filename.endswith(extension)
                for extension in ["jpg", "png", "gif"]
            ):
                embed.set_image(url=attachment.url)
            else:
                embed.add_field(
                    name="Attachments",
                    value=f"[{attachment.filename}]({attachment.url})",
                    inline=False,
                )
        embed.timestamp = message.created_at
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        if message.author == self.bot.user:
            return
        if message.guild is None:
            return
        if not await self.config.enabled():
            return
        if not await self.bot.allowed_by_whitelist_blacklist(message.author):
            return
        if message.channel.id in (port := await self.config.ports()):
            _log.info(f"Gateway message {message.content} from {message.guild.name}")
            port.remove(message.channel.id)
            return await self._gateway(
                message=message, channel=self.bot.get_channel(port[0])
            )
