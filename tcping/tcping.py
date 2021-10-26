from typing import Literal, Optional
import socket
from time import time

import discord
from redbot.core import commands
from redbot.core.bot import Red

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Tcping(commands.Cog):
    """
    check server latency with bot
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot

    async def latency_point(
        self, host: str, port: str, timeout: float = 5
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

        return round(float(s_runtime), 2)

    @commands.command(name="tcping")
    async def tcping(self, ctx: commands.Context, host: str, port: int = 443):
        """
        Pings a server with port with bot
        [p]tcping [host] <port>
        Default port: 443
        """
        latency = await self.latency_point(host=host, port=port)
        await ctx.tick()
        if latency is None:
            await ctx.send(f"{host} connection timed out!")
            return
        await ctx.reply(
            embed=discord.Embed(
                description=f"{host} responded with {latency:.2f}ms latency.",
                color=await ctx.embed_color(),
            ),
            mention_author=False,
        )
