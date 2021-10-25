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
# SUPPORT_SERVER = "https://discord.gg/BXAa6yskzU"
# INVITE_URL = "https://discord.com/oauth2/authorize?client_id=361249607520354306&scope=bot&permissions=805314614"


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
            "invite_link": "",
        }

        self.config.register_global(**default_global)

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

        if (link := await self.config.server_link()) != "":
            descript += f"\nNeed some help? Join my [support server!]({link})"

        if (link := await self.config.invite_link()) != "":
            descript += f"\nLooking to invite me? [Click here!]({link})"

        embed = discord.Embed(
            colour=await self.bot.get_embed_colour(message.channel),
            description=descript,
        )
        await message.channel.send(embed=embed)
