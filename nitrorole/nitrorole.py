from typing import Literal, Optional, Union
import logging

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("cog.qenu-cogs.nitrorole")

class Nitrorole(commands.Cog):
    """Giving Nitro Booster a personal role"""
    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=164900704526401545021,
            force_registration=True,
        )

        self.nitro_template()

        default_guild = {}

        self.config.register_guild(**default_guild)

    async def if_member_booster(member: discord.Member):
        """checks if a member has the booster role"""
        return any([role.is_premium_subscriber() for role in member.roles])

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        guild: discord.Guild = after.guild

        if not await self.config.guild(guild).toggle():
            return

        if nitro := after.guild.premium_subscriber_role is None:
            await log.debug("I cannot find a nitro-booster role in this guild.")
            return



