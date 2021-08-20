import streamrolenotify
from typing import Literal, Optional
import time
from datetime import datetime, timedelta
import logging
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

log = logging.getLogger("cog.qenu-cogs.streamrolenotify")


class Streamrolenotify(commands.Cog):
    """ """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=164900704526401545015,
            force_registration=True,
        )

        self.stream_start = "Member is streaming."

        default_guild = {
            "channel": None,
            "toggle": False,
        }

        self.config.register_guild(**default_guild)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):

        guild: discord.Guild = after.guild

        if not await self.config.guild(guild).toggle():
            return

        if not guild.me.guild_permissions.view_audit_log:
            return log.info(
                "Unable to verify reason, Missing permissions to check audit log!"
            )

        user = after
        time_from = datetime.utcnow() - timedelta(minutes=1)

        await asyncio.sleep(2.5)

        try:
            action = await guild.audit_logs(
                action=discord.AuditLogAction.member_role_update, after=time_from
            ).find(
                lambda e: e.target.id == user.id
                and e.reason == self.stream_start
                and time_from < e.created_at
            )
        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        else:
            channel = guild.get_channel(channel_id=await self.config.guild(guild).channel())
            await channel.send(f"{user.name} has started streaming!")

    @commands.group(name="streamrolenotify")
    @commands.guild_only()
    @commands.admin_or_permissions(manage_guild=True)
    async def streamrolenotify(self, ctx: commands.Context):
        """"""

        config = await self.config.guild(ctx.guild).all()

        embed = discord.Embed(color=ctx.author.color, title="Streamrole Notification Settings")
        embed.add_field(name="Status", value=config['toggle'])
        embed.add_field(name="Channel", value=config['channel'])

        await ctx.send(embed=embed)

    @streamrolenotify.command()
    async def toggle(self, ctx: commands.Context, on_off: Optional[str] = None):
        """Toggles on/off notification
        Usage: [p]streamrolenotify toggle <on_off>
        """
        guild: discord.Guild = ctx.guild

        if on_off is None:
            state = not await self.config.guild(guild).toggle()
        else:
            state = False if on_off.lower() == "off" else True

        await self.config.guild(guild).toggle.set(state)

        await ctx.send(f"Streamrole notification has been {'enabled' if state else 'disabled'}.")

        if state and await self.config.guild(guild).channel() == None:
            await self.channel(ctx, str(ctx.channel.id))

    @streamrolenotify.command()
    async def channel(self, ctx: commands.Context, channel_id: Optional[str] = None):
        """specify channel to send notifications"""

        SNOWFLAKE_THRESHOLD = 2 ** 63
        if channel_id.isnumeric() and len(channel_id) >= 17 and int(channel_id) < SNOWFLAKE_THRESHOLD:
            guild: discord.Guild = ctx.guild
            await self.config.guild(guild).channel.set(ctx.channel.id)
            await ctx.send(f"Streamrole Notification Channel has been set to {ctx.channel.mention}")

        else:
            await ctx.send("invalid channel id")


    @streamrolenotify.command()
    async def test(self, ctx: commands.Context, user: discord.Member):

        await ctx.send("L123")


        guild: discord.Guild = user.guild

        if not await self.config.guild(guild).toggle():
            return

        if not guild.me.guild_permissions.view_audit_log:
            return log.info(
                "Unable to verify reason, Missing permissions to check audit log!"
            )

        await ctx.send("L136")

        time_from = datetime.utcnow() - timedelta(minutes=1)

        await asyncio.sleep(2.5)

        try:
            action = await guild.audit_logs(
                action=discord.AuditLogAction.member_role_update, after=time_from
            ).find(
                lambda e: e.target.id == user.id
                and e.reason == self.stream_start
                and time_from < e.created_at
            )
            await ctx.send("L150")

        except discord.Forbidden:
            pass
        except discord.HTTPException:
            pass

        else:
            await ctx.send("L158")

            channel = guild.get_channel(channel_id=await self.config.guild(guild).channel())
            await channel.send(f"{user.name} has started streaming!")