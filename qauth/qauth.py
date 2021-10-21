from logging import Manager
from typing import Literal, Optional
import pyotp
import asyncio

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Qauth(commands.Cog):
    """
    OTP verification perms
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x249D8512C82,
            force_registration=True,
        )

        default_user = {"secret": ""}
        default_guild = {"enabled": [], "allowed": [], "timeout": 30, "role_id": 0}

        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user datapip removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    @commands.command(name="qauthorize", aliases=["qa", "su"])
    @commands.guild_only()
    async def qauthorize(self, ctx: commands.Context):
        """ """
        async with self.config.guild(ctx.guild) as guild:
            role_id = guild["role_id"]
            if role_id == 0:
                return await ctx.reply(
                    content=(
                        "Guild perm role has not been configured, or has been reseted.\n"
                        "Set the perm role via `[p]qauth role <@role>`"
                    )
                )
            if isinstance(ctx.guild.get_role(role_id), type(None)):
                await self._set_role(guild=ctx.guild, role_id=0)
                return await ctx.reply(
                    content=(
                        "Configured Role is invalid, reseting to default settings.\n"
                        "Set the perm role via `[p]qauth role <@role>`"
                    )
                )
            if ctx.author not in guild["allowed"]:
                return await ctx.reply(
                    content="You do not have permission to do that.",
                    mention_author=False,
                )

            if ctx.author in guild["enabled"]:
                # run remove process
                return await ctx.reply(
                    content="Your role has been removed.", mention_author=False
                )

        async with self.config.user(ctx.author) as userdata:
            if userdata["secret"] == "":
                return await ctx.reply(
                    content="An error must've occured, you haven't been registered yet.",
                    mention_author=False,
                )
            guild_message = await ctx.reply(
                content="I have received your request, please check your dms.",
                mention_author=False,
            )
            author_dm = await ctx.author.dm_channel
            if isinstance(author_dm, type(None)):
                author_dm = await ctx.author.create_dm()

            otpinfo = discord.Embed(
                description=(
                    "**OTP verification**\n"
                    "---\n"
                    f"guild id: {ctx.guild.id}\n"
                    f"request from: #{ctx.channel.name}\n"
                    f"request time: <t:{int(ctx.message.created_at.timestamp)}:R>\n"
                    "\n"
                    "please respond with your code on your authenticator"
                )
            )
            otpinfo.set_author(
                name=f"from **{ctx.guild.name}**", icon_url=ctx.guild.icon_url
            )
            otpinfo.set_footer(
                text="if you somehow lost your code, please contact the bot owner"
            )

            await author_dm.send(embed=otpinfo)

            result = await self.validate_attempts(user=ctx.author, user_dm=author_dm)

            if result:
                # run add process
                return await guild_message.edit()
            else:
                return await guild_message.edit("Auth failed.", mention_author=False)

    async def validate_attempts(
        self, *, user: discord.user, user_dm: discord.Channel, attempt: int = 3
    ) -> bool:
        while attempt > 0:

            def validate(message):
                return len(message.content) == 6 and message.channel == user_dm

            try:
                code = await self.bot.wait_for("message", check=validate, timeout=60.0)
            except asyncio.TimeoutError:
                return await user_dm.send(content="Request timeout.")
            else:
                if self.timebasedOTP(
                    secret=await self.config.user(user).secret(), code=code
                ):
                    await user_dm.send(
                        embed=discord.Embed(description="code verified.")
                    )
                    return True
                else:
                    await user_dm.send(
                        embed=discord.Embed(
                            description=f"wrong code. please try again...\n {attempt}/3 remaining attpemts."
                        )
                    )
                    attempt -= 1
        return False

    def create_secret(self) -> str:
        return pyotp.random_base32()

    def timebasedOTP(self, *, secret: str, code: str) -> bool:
        """returns True if OTP code valid"""
        return pyotp.TOTP(secret).verify(code)

    @commands.command()
    @commands.is_owner()
    async def resetotp(self, ctx: Optional[commands.Context], *, user: discord.User):
        """assigns user a new secret"""
        secret = self.create_secret()
        await self.config.user(user).secret.set(secret)
        await user.send(
            content=f"Your Auth Key has been reseted, please save your new key somewhere safe.\nYou have 30 seconds to do so..."
        )
        await user.send(content=secret, delete_after=30.0)
        return await ctx.tick()

    async def member_enable(self):
        pass  # add process

    async def member_disable(self):
        pass  # remove process

    @commands.group(name="qauth")
    @commands.has_permissions(manage_roles=True)
    async def qauth(self, ctx: commands.Context):
        """ """
        if ctx.invoked_subcommand is None:
            pass
            # show embed current settings here

    async def _set_role(self, *, guild: discord.Guild, role_id: int) -> None:
        """sets the role with config"""
        return await self.config.guild(guild).role_id.set(role_id)

    @qauth.command(name="role")
    @commands.has_permissions(administrator=True)
    async def set_role(self, ctx: commands.Context, role: discord.Role):
        """set the role given on verification"""
        pass

    @qauth.command(name="timeout")
    @commands.has_permissions(administrator=True)
    async def set_timeout(self, ctx: commands.Context, seconds: int):
        """
        set the timeout seconds for temporary role, -1 to disable timeout
        default timeout is 30 seconds
        """
        await self.config.guild(ctx.guild).timeout.set(seconds)
        return await ctx.reply(
            content=f"The timeout for {ctx.guild.name} has been set to {seconds} seconds.",
            mention_author=False,
        )

    @qauth.command(name="add")
    @commands.has_permissions(administrator=True)
    async def user_add(self, ctx: commands.Context, user: discord.User):
        """adds a user to the list for perms"""
        pass

    @qauth.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def user_remove(self, ctx: commands.Context, user: discord.User):
        """removes a user from the list for perms"""
        pass

    @qauth.command(name="list")
    async def list_guild(self, ctx: commands.Context):
        """check the users that are able to gain perms"""
        pass
