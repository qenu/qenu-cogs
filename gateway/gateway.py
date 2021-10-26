from typing import Literal

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


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
        default_global = {
            "enabled": False,
            "port_one": {
                "guild": 0,
                "channel": 0,
            },
            "port_two": {
                "guild": 0,
                "channel": 0,
            },
        }

        self.config.register_global(**default_global)

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    @commands.group(name="gateway", invoke_without_commands=True)
    @commands.is_owner()
    async def channel_gateway(self, ctx: commands.Context):
        """Bridges two channel together"""
        pass
