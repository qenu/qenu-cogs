from typing import Literal, Optional
import pyotp
import asyncio
import math
import time

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import pagify
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS

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
        default_guild = {"allowed": [], "timeout": 300, "role_id": 0}
        default_global = {"_qauth": {}}

        self.config.register_user(**default_user)
        self.config.register_guild(**default_guild)
        self.config.register_global(**default_global)

        self.role_check.start()

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user datapip removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    async def auth_add(self, *, user: discord.User, guild: discord.Guild, time: int):
        async with self.config._qauth() as auth:
            _guild = auth.get(guild.id, None)
            if isinstance(_guild, type(None)):
                # create if not exist
                auth[guild.id] = {}
            auth[guild.id][user.id] = time

    async def auth_remove(self, *, user: discord.User, guild: discord.Guild):
        async with self.config._qauth() as auth:
            del auth[guild.id][user.id]
            if len(auth[guild.id]) == 0:
                del auth[guild.id]

    @commands.command(name="qauthorize", aliases=["qa", "su"])
    @commands.guild_only()
    async def qauthorize(self, ctx: commands.Context):
        """toggle priviledges"""
        member = ctx.author
        role_id = await self.config.guild(ctx.guild).role_id()
        if role_id == 0:
            return await ctx.reply(
                content=(
                    "Guild perm role has not been configured, or has been reseted.\n"
                    "Set the perm role via `[p]qauth role <@role>`"
                ),
                mention_author=False,
            )
        role = ctx.guild.get_role(role_id)
        if not isinstance(role, discord.Role):
            await self._set_role(guild=ctx.guild, role_id=0)
            return await ctx.reply(
                content=(
                    "Configured Role is invalid, reseting to default settings.\n"
                    "Set the perm role via `[p]qauth role <@role>`"
                ),
                mention_author=False,
            )
        if member.id not in await self.config.guild(ctx.guild).allowed():
            return await ctx.reply(
                content="You do not have permission to do that.",
                mention_author=False,
            )

        auth = await self.config._qauth()
        if (not isinstance(auth.get(ctx.guild.id, None), type(None))) and str(member.id) in auth[ctx.guild.id]:
            # disable
            await member.remove_roles(role, reason="qauth role remove on demand")
            await self.auth_remove(user=member, guild=ctx.guild)
            return await ctx.reply(
                content="Your role has been removed.", mention_author=False
            )

        if await self.config.user(ctx.author).secret() == "":
            return await ctx.reply(
                content="An error must've occured, you haven't been registered yet.",
                mention_author=False,
            )
        guild_message = await ctx.reply(
            content="I have received your request, please check your dms.",
            mention_author=False,
        )
        author_dm = member.dm_channel
        if isinstance(author_dm, type(None)):
            author_dm = await member.create_dm()

        otpinfo = discord.Embed(
            description=(
                "**OTP verification**\n"
                "---\n"
                f"guild id: {ctx.guild.id}\n"
                f"request from: #{ctx.channel.name}\n"
                f"request time: <t:{int(ctx.message.created_at.timestamp())}:R>\n"
                "\n"
                "please respond with your code on your authenticator"
            ),
            color=await ctx.embed_color(),
        )
        otpinfo.set_author(
            name=f"from **{ctx.guild.name}**", icon_url=ctx.guild.icon_url
        )
        otpinfo.set_footer(
            text="if you somehow lost your code, please contact the bot owner"
        )

        await author_dm.send(embed=otpinfo)

        result = await self.validate_attempts(user=member._user, user_dm=author_dm)

        if result:
            # enable
            await member.add_roles(role, reason="qauth role verified")
            timeout = await self.config.guild(ctx.guild).timeout()
            timeout = int(time.time() + timeout) if timeout != -1 else timeout
            await self.auth_add(user=member, guild=ctx.guild, time=timeout)
            return await guild_message.edit(content="Auth Verified.", mention_author=False)

        else:
            return await guild_message.edit(content="Auth failed.", mention_author=False)

    async def validate_attempts(
        self, *, user: discord.user, user_dm: discord.TextChannel, attempt: int = 3
    ) -> bool:
        secret = await self.config.user(user).secret()
        while attempt > 0:
            def validate(message):
                return len(message.content) == 6 and message.channel == user_dm

            try:
                code = await self.bot.wait_for("message", check=validate, timeout=60.0)
            except asyncio.TimeoutError:
                return await user_dm.send(content="Request timeout.")
            else:
                if self.timebasedOTP(
                    secret=secret, code=code.content
                ):
                    await user_dm.send(
                        embed=discord.Embed(
                            description="Code verified.", color=discord.Color.green()
                        )
                    )
                    return True
                else:
                    await user_dm.send(
                        embed=discord.Embed(
                            description=f"Wrong code. please try again...\n {attempt}/3 remaining attpemts.",
                            color=discord.Color.red(),
                        )
                    )
                    attempt -= 1
        await user_dm.send(
            embed=discord.Embed(
                    description="Maximum attempts exceeded, Terminating process.",
                    color=discord.Color.red(),
            )
        )
        return False

    def create_secret(self) -> str:
        return pyotp.random_base32()

    def timebasedOTP(self, *, secret: str, code: str) -> bool:
        """returns True if OTP code valid"""
        return pyotp.TOTP(secret).verify(code)

    @commands.command()
    @commands.is_owner()
    async def resetotp(self, ctx: Optional[commands.Context], *, user: discord.User):
        """removes user secret"""
        await self.config.user(user).secret.set("")
        await user.send(
            content=f"Your Auth Key has been reseted, you can now re-register for a new key."
        )
        return await ctx.tick()

    @commands.group(name="qauth", invoke_without_command=True)
    async def qauth(self, ctx: commands.Context):
        """settings and infos about Qauth"""
        if ctx.invoked_subcommand is None:
            status = (await self.config.user(ctx.author).secret()) != ""
            emb = discord.Embed(
                title="Qauth discord Authenticator",
                description=(
                    f"Name: {ctx.author} • ({ctx.author.id})\n"
                    f"Status: {'R' if status else 'Not r'}egistered\n"
                ),
                color=await ctx.embed_color(),
            )
            emb.set_author(name=ctx.author.name, icon_url=ctx.author.avatar_url)
            if not status:
                emb.add_field(
                    name="[p]qauth register",
                    value="(dm only)\nUse this command via dm to start using qauth.",
                    inline=False,
                )
            return await ctx.send(embed=emb)

    @qauth.command(name="register")
    @commands.dm_only()
    @commands.max_concurrency(1)
    async def register(self, ctx: commands.Context):
        """register for qauth"""
        await ctx.send(
            embed=discord.Embed(
                description=(
                    "**Qauth Register**\n"
                    "---\n"
                    "You are about to create a key for qauth,\n"
                    "please make sure you are ready to save your key safely\n"
                    "as the key could **not** be reditributed.\n"
                    "if you ever lost your key code, you would have to contact the owner for it.\n"
                    "\n"
                    "Please type `agree` once you are ready!"
                ),
                color=await ctx.embed_color(),
            )
        )

        def check_agree(message):
            return message.content.lower() == "agree" and message.channel == ctx.channel

        try:
            await self.bot.wait_for("message", check=check_agree, timeout=180.0)
        except asyncio.TimeoutError:
            return await ctx.send(
                content="Request Timed out, please do `[p]qauth register` again once you're ready!"
            )

        secret = self.create_secret()
        with_code = await ctx.send(
            embed=discord.Embed(
                description=(
                    "**Your OTP Key code**\n"
                    f"{secret}\n"
                    "----\n"
                    "after entering the key code to your prefered app,\n"
                    "please respond with your 6-digits otp to finish register."
                )
            )
        )

        def verify(message):
            return self.timebasedOTP(secret=secret, code=message.content)

        try:
            await self.bot.wait_for("message", check=verify, timeout=60.0)
        except asyncio.TimeoutError:
            await with_code.delete()
            return await ctx.send(
                content="Request Timed out, please do `[p]qauth register` again once you're ready!"
            )
        else:
            await with_code.delete()
            await self.config.user(ctx.author).secret.set(secret)
            await ctx.send("Your qauth has been successfully registered!")

    async def _set_role(self, *, guild: discord.Guild, role_id: int) -> None:
        """sets the role with config"""
        return await self.config.guild(guild).role_id.set(role_id)

    @qauth.command(name="role")
    @commands.has_permissions(administrator=True)
    async def set_role(self, ctx: commands.Context, role: discord.Role):
        """set the role given on verification"""
        await self._set_role(guild=ctx.guild, role_id=role.id)
        return await ctx.tick()

    @qauth.command(name="timeout")
    @commands.has_permissions(administrator=True)
    async def set_timeout(self, ctx: commands.Context, seconds: int):
        """
        set the timeout seconds for temporary role, -1 to disable timeout
        default timeout is 300 seconds, timeout cannot be shorter than 60 seconds
        """
        if seconds != -1 and seconds >= 60:
            return await ctx.reply(
                content="Time out must be either -1 or more than 5 seconds.",
                mention_author=False,
            )
        await self.config.guild(ctx.guild).timeout.set(seconds)
        return await ctx.reply(
            content=f"The timeout for {ctx.guild.name} has been set to {seconds} seconds.",
            mention_author=False,
        )

    @qauth.command(name="add")
    @commands.has_permissions(administrator=True)
    async def user_add(self, ctx: commands.Context, user: discord.User):
        """adds a user to the qauth list"""
        async with self.config.guild(ctx.guild).all() as guild:
            if user.id in guild["allowed"]:
                return await ctx.reply(
                    content=f"{user}({user.id}) is already in qauth list",
                    mention_author=False,
                )
            guild["allowed"].append(user.id)
        reply = f"I have added {user}({user.id}) to qauth list"
        secret = await self.config.user(user).secret()
        if secret == "":
            await user.send(
                embed=discord.Embed(
                    description=(
                        "**You have been invited to use Qauth**\n"
                        "---\n"
                        f"<t:{ctx.message.created_at.timestamp()}:R>\n"
                        f"from: {ctx.author}\n"
                        f"in: {ctx.guild.name} ({ctx.guild.id})\n"
                        "\n"
                        "to start the registration, type `[p]qauth register` in dms"
                    ),
                    color=await ctx.embed_color(),
                )
            )
            reply += (
                f"\n\nSince {user.name} hasn't setup their auth key, "
                "I have dmd them the instructions to register.\n"
                "They will **not** be able to use this command before registering."
            )
        return await ctx.reply(content=reply, mention_author=False)

    @qauth.command(name="remove")
    @commands.has_permissions(administrator=True)
    async def user_remove(self, ctx: commands.Context, user: discord.User):
        """removes a user from the qauth list"""
        async with self.config.guild(ctx.guild).all() as guild:
            if user.id not in guild["allowed"]:
                return await ctx.reply(
                    content=f"{user}({user.id}) was not in qauth list",
                    mention_author=False,
                )
            guild["allowed"].remove(user.id)
        return await ctx.reply(
            content=f"I have removed {user}({user.id}) from qauth list",
            mention_author=False,
        )

    @qauth.command(name="list")
    async def list_guild(self, ctx: commands.Context):
        """check the users that are able to gain perms"""
        allowed = await self.config.guild(ctx.guild).allowed()

        message = ""
        auth = await self.config._qauth()
        for member_id in allowed:
            message += f"{'+' if member_id in auth[ctx.guild.id] else '-'} {ctx.guild.get_member(member_id)}\n"

        embeds = []
        pages = 1
        for page in pagify(message, delims=["\n"], page_length=100):
            emb = discord.Embed(
                colour=await ctx.embed_colour(),
                title=f"{ctx.guild.name} qauth members",
                description=page,
            )
            emb.set_footer(text=f"Page {pages}/{(math.ceil(len(message) / 100))}")
            pages += 1
            embeds.append(emb)

        await menu(ctx, embeds, DEFAULT_CONTROLS)

    @tasks.loop(seconds=10)
    async def role_check(self):
        now = time.time()
        async with self.config._qauth() as auth:
            for guild in auth:
                role = await self.config.guild(guild).role_id()
                removal = []
                for user in auth[guild]:
                    if (timeout := auth[guild][user]) != -1 and timeout <= now:
                        removal.append(user)
                for user in removal:
                    await self.bot.get_or_fetch_member(
                        guild=guild, member_id=user
                    ).remove_roles(
                        await self.bot.get_guild(guild).get_role(role),
                        reason="qauth role remove on timeout",
                    )
                    del auth[user]

    @qauth.command(name="test")
    async def test(self, ctx: commands.Context):
        secret = await self.config.user(ctx.author).secret()

        await ctx.send(content="Please enter your OTP code.")

        def verify(message):
            return (
                len(message.content) == 6
                and message.author == ctx.author
                and message.channel == ctx.channel
            )

        try:
            code = await self.bot.wait_for("message", check=verify, timeout=60.0)
        except asyncio.TimeoutError:
            return await ctx.reply(content="Request Timed out", mention_author=False)
        else:
            if self.timebasedOTP(secret=secret, code=code.content):
                return await ctx.reply("OTP verified!", mention_author=False)
            else:
                return await ctx.reply("Invalid OTP.", mention_author=False)
