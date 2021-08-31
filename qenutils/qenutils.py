import socket
from time import time
from typing import Literal, Optional, Union

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Qenutils(commands.Cog):
    """
    Utility cogs from qenu
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=164900704526401545003,
            force_registration=True,
        )

        # self.config.register_global(**default_global)

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    async def latency_point(
        self, host: str, port: str, timeout: float = 5, offset: bool = False
    ) -> Optional[float]:
        """
        full credit to : https://github.com/dgzlopes/tcp-latency
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        s_start = time()

        try:
            s.connect((host, int(port)))
            s.shutdown(socket.SHUT_RD)

        except socket.timeout:
            return None
        except OSError:
            return None

        s_runtime = (time() - s_start) * 1000

        return (
            round(float(s_runtime) - 130, 2)
            if offset is False
            else round(float(s_runtime), 2)
        )

    @commands.command(name="tcping")
    @commands.admin_or_permissions(manage_guild=True)
    async def tcping(self, ctx: commands.Context, host: str, port: int = 443):
        """
        Pings a server with port with bot
        [p]tcping [host] <port>
        Default port: 443
        """
        latency = await self.latency_point(host=host, port=port, offset=True)
        await ctx.tick()
        if latency is None:
            await ctx.send(f"{host} connection timed out!")
            return
        await ctx.send(f"{host} responded with {latency:.2f}ms latency.")

    @commands.command(name="whatdis")
    @commands.is_owner()
    async def whatdis(
        self, ctx: commands.Context, input: Optional[Union[discord.Message, str]]
    ):
        """
        owo What dis
        """
        reply = (
            f"\nreceived input: {input}\n"
            f"input type:     {type(input)}\n"
            f"input length:   {len(input)}"
        )
        await ctx.send(content=reply)

    async def nqn_webhook(
        self, channel: discord.TextChannel
    ) -> Optional[discord.Webhook]:
        return discord.utils.get(await channel.webhooks(), name="nqn")

    @commands.command(name="nqn")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_webhooks=True)
    async def nqn(self, ctx: commands.Context, emoji_name: str):
        """nqn emote from this guild"""
        pseudo = ctx.author

        emoji = discord.utils.get(ctx.guild.emojis, name=emoji_name)
        if emoji is None:
            await ctx.send(f'Emoji "{emoji_name}" not found.')
            return

        if (webhook := await self.nqn_webhook(ctx.channel)) is None:
            webhook = await ctx.channel.create_webhook(name="nqn")

        await webhook.send(
            content=emoji, username=pseudo.display_name, avatar_url=pseudo.avatar_url
        )
        await ctx.message.delete()

    @commands.command(name="rmnqn")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_webhooks=True)
    async def rmnqn(self, ctx: commands.Context):
        """remove all webhooks with the name nqn"""
        whs = await ctx.channel.webhooks()
        await ctx.send(f"{len(whs)} webhooks found.")
        if len(whs) != 0:
            count = 0
            for wh in whs:
                if wh.name == "nqn":
                    count += 1
                    await wh.delete()
        await ctx.send(f"Remove nqn process ended. {count} webhooks were removed.")
