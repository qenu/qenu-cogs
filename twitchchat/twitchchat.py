from typing import Literal
from socket import socket

import discord
from discord.ext import tasks
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from .utils import replying, RED_TICK, GREEN_TICK, TYPING, GREY_TICK


RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Twitchchat(commands.Cog):
    """
    Connect an instance in chat with twitch api
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0xB57CAD433D9EAB1,
            force_registration=True,
        )
        default_global = {
            "oauth": "",
            "_channel": "",
            "username": "",
        }
        self.respond = False

        self.config.register_global(**default_global)

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    @commands.group(name="twitchchat", invoke_without_command=True)
    @commands.is_owner()
    async def twitchchat(self, ctx: commands.Context):
        """Menu for twitchchat cogs, also displays current config"""
        embed = discord.Embed(title="Twitch chat bridge")
        embed.add_field(
            name="Channel", value=f"{await self.config._channel()}", inline=True
        )
        embed.add_field(
            name="Username", value=f"{await self.config.username()}", inline=True
        )

        embed.add_field(
            name="Commands",
            value=(
                "list of commands for twitchchat cog\n"
                f"{ctx.clean_prefix}twitchchat set\n"
                "> Set up credentials before using this function\n"
                f"{ctx.clean_prefix}twitchchat connect\n"
                "> Starts the connection to twitch chat\n"
                f"{ctx.clean_prefix}twitchchat disconnect\n"
                "> Exits the connection to twitch chat\n"
            ),
            inline=False,
        )
        embed.timestamp = ctx.message.created_at
        return replying(embed=embed, ctx=ctx)

    @commands.Cog.listener()
    async def on_message_without_command(self, message):
        """Cog listener to yeet discord to twitch"""
        if not self.respond:
            return
        if message.author.bot:
            return
        if message.channel != self.respond:
            return
        channel = await self.config._channel()
        message_temp = f"PRIVMSG #{channel} :{message.content}"
        self.socket.send(f"{message_temp}\n".encode())

    @tasks.loop(seconds=1)
    async def chat_listener(self):
        read_buffer = self.socket.recv(1024).decode()
        for line in read_buffer.split("\r\n"):
            # ping pong to stay alive
            if "PING" in line and "PRIVMSG" not in line:
                self.socket.send("PONG tmi.twitch.tv\r\n".encode())

            # reacts at user message
            elif line != "":
                parts = line.split(":", 2)
                # return parts[1].split('!', 1)[0], parts[2]
                await self.respond.send(
                    embed=discord.Embed(
                        title=f"{parts[1].split('!', 1)[0]}", description=f"{parts[2]}"
                    )
                )

    @twitchchat.command(name="connect", aliases=["start"])
    async def twitchchat_connect(self, ctx: commands.Context):
        """Starts the connection with twitch"""
        server = "irc.twitch.tv"
        port = 6667

        self.socket = socket()
        channel = await self.config._channel()
        auth = await self.config.oauth()
        name = await self.config.username()
        self.socket.connect((server, port))
        self.socket.send(f"PASS {auth}\nNICK {name}\n JOIN #{channel}\n".encode())

        loading = True
        while loading:
            read_buffer_join = self.socket.recv(1024)
            read_buffer_join = read_buffer_join.decode()
            print(read_buffer_join)

            for line in read_buffer_join.split("\n")[0:-1]:
                # checks if loading is complete
                loading = "End of /NAMES list" not in line

        await replying(content="Twitch loaded, starting loop.", ctx=ctx)
        self.chat_listener.start()
        # use to store discord.TextChannel object
        self.respond = ctx.channel

    @twitchchat.command(name="disconnect", aliases=["stop", "close", "exit"])
    async def twitchchat_disconnect(self, ctx: commands.Context):
        """Ends the connection with twitch"""
        self.respond = False
        await replying(content="Disconnected from twitch chat.", ctx=ctx)

    @twitchchat.group(name="set")
    async def _set(self, ctx: commands.Context):
        """Setup the credentials for twitchchat to work"""
        pass

    @_set.command(name="channel")
    async def _channel(self, ctx: commands.Context, *, twitch_channel: str = ""):
        """Sets the twitch channel to connect to

        setting it empty removes the channel
        """
        await self.config._channel.set(twitch_channel)
        if twitch_channel == "":
            return replying(
                content=f"I have removed your twitch channel selection.", ctx=ctx
            )
        return replying(
            content=f"Twtich channel has been set to {twitch_channel}.", ctx=ctx
        )

    @_set.command(name="username")
    async def _username(self, ctx: commands.Context, *, twitch_username: str = ""):
        """Enter your twitch username

        setting it empty removes the username
        """
        await self.config.username.set(twitch_username)
        if twitch_username == "":
            return await ctx.message.add_reaction(GREEN_TICK)
        return await replying(
            content=f"Your username has been set to {twitch_username}.", ctx=ctx
        )

    @_set.command(name="oauth")
    async def _oauth(self, ctx: commands.Context, *, tmi_oauth: str = ""):
        """Oauth token generated by twitch, **include** oauth:
        link to token: https://twitchapps.com/tmi/

        setting it empty removes the token
        """
        await self.config.oauth.set(tmi_oauth)
        if tmi_oauth == "":
            return await ctx.message.add_reaction(GREEN_TICK)
        await ctx.message.delete()
        return await replying(content="Your credentials has been set.", ctx=ctx)
