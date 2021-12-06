import os
from pathlib import Path
from random import sample
from typing import Literal, Optional
import asyncio

import discord
from discord.ext import tasks
from pyboy import PyBoy, WindowEvent
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

GAME_FILE = "pokemon_red.gb"

INPUT_OPTIONS = {
    "A": [WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A],
    "B": [WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B],
    "上": [WindowEvent.PRESS_ARROW_UP, WindowEvent.RELEASE_ARROW_UP],
    "下": [WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN],
    "左": [WindowEvent.PRESS_ARROW_LEFT, WindowEvent.RELEASE_ARROW_LEFT],
    "右": [WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.RELEASE_ARROW_RIGHT],
    "開始": [WindowEvent.PRESS_BUTTON_START, WindowEvent.RELEASE_BUTTON_START],
    "選擇": [WindowEvent.PRESS_BUTTON_SELECT, WindowEvent.RELEASE_BUTTON_SELECT],
}


class Discord_Pokemon(commands.Cog):
    """
    discord plays pokemon
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.datapath = Path(__file__).parent.resolve()
        self._game = False
        self._enabled = False
        self._channel = False
        self._message_cache = {}
        # self.config = Config.get_conf(
        #     self,
        #     identifier=0x566391e60ee70bf1,
        #     force_registration=True,
        # )

    def cog_unload(self):
        self._pokemon_bg_loop.cancel()
        self._pokemon_loop.cancel()
        self._game.stop()

    @commands.group(name="pokemon", aliases=["pkm", "寶可夢"], invoke_without_command=True)
    async def _pokemon(self, ctx: commands.Context) -> None:
        """
        Discord plays pokemon menu

        This function should show command options and current game status
        """
        embed = discord.Embed(
            title="寶可夢 紅版",
            description="Discord 一起玩寶可夢",
            color=await ctx.embed_color(),
        )
        embed.add_field(
            name="遊戲方式",
            value=(
                "```yaml\n"
                "A, B,\n"
                "上, 下, 左, 右,\n"
                "開始, 選擇\n"
                "```"
            ),
            inline=False,
        )
        embed.add_field(
            name="遊戲狀態",
            value=(
                f"遊戲狀態：{'進行中' if self._enabled else '停止'}\n"
                f"遊戲頻道：{self._channel.mention if self._channel else '無'}"
            ),
            inline=False,
        )
        embed.set_footer(
            text="powered by PyBoy"
        )
        await ctx.send(embed=embed)

    @commands.is_owner()
    @_pokemon.command(name="start")
    async def _pokemon_start(self, ctx: commands.Context) -> None:
        """
        Start a new pokemon game
        """
        if self._enabled:
            await ctx.send("Pokemon game is already running")
            return
        self._enabled = True
        self._channel = ctx.channel
        self._game = PyBoy(os.path.join(self.datapath, "rom", GAME_FILE))
        self._pokemon_bg_loop.start()
        self._pokemon_loop.start()
        await ctx.send(embed=discord.Embed(description="成功啟動寶可夢",color=await ctx.embed_color(),))
        [self._game.tick() for _ in range(240)]
        await self._pokemon_screen()

    @commands.is_owner()
    @_pokemon.command(name="stop")
    async def _pokemon_stop(self, ctx: commands.Context) -> None:
        """
        Stop the current pokemon game
        """
        if not self._enabled:
            await ctx.send("Pokemon game is not running")
            return
        self._pokemon_loop.stop()
        self._pokemon_bg_loop.stop()
        self._game.stop()
        self._enabled = False
        self._channel = False
        await ctx.send(embed=discord.Embed(description="寶可夢已停止",color=await ctx.embed_color(),))

    @tasks.loop(seconds=0.02)
    async def _pokemon_bg_loop(self) -> None:
        """
        This function is called every second
        """
        self._game.tick()

    @tasks.loop(seconds=5)
    async def _pokemon_loop(self) -> None:
        """
        This function is called every 5 seconds
        """
        if self._message_cache:
            counter = {
                "A": 0,
                "B": 0,
                "上": 0,
                "下": 0,
                "左": 0,
                "右": 0,
                "開始": 0,
                "選擇": 0,}
            messages = list(self._message_cache.values())
            for content in messages:
                counter[content] += 1
            choice = sample(messages, k=1)[0]
            choosen = INPUT_OPTIONS[choice]
            self._message_cache.clear()
            embed = discord.Embed(
                title="聊天室決定",
                description=(
                    "```yaml\n"
                    f"欸: {counter['A']} "
                    f"逼: {counter['B']}\n"
                    f"上: {counter['上']} "
                    f"下: {counter['下']}\n"
                    f"左: {counter['左']} "
                    f"右: {counter['右']}\n"
                    f"開始: {counter['開始']} "
                    f"選擇: {counter['選擇']}\n"
                    "```"
                ),
                color=await self.bot.get_embed_color(self.bot.user),
            )
            embed.add_field(
                name="結論",
                value=f"{choice}",
                inline=False,
            )
            self._game.send_input(choosen[0])
            self._game.tick()
            self._game.tick()
            self._game.tick()
            self._game.send_input(choosen[1])
            [self._game.tick() for _ in range(240)]
            await self._channel.send(embed=embed)
            await self._pokemon_screen()

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """
        This function is called when a message is sent
        """
        if not self._enabled:
            return
        if message.channel != self._channel:
            return
        if message.author.bot:
            return
        if len(message.content) > 2:
            return
        if message.content.upper() not in INPUT_OPTIONS.keys():
            return
        self._message_cache[message.author] = message.content.upper()

    async def _pokemon_screen(self, ctx: Optional[commands.Context]=None) -> None:
        """
        This function send the current screen to discord
        """
        cache_image_path = os.path.join(self.datapath, "cache_img.png")
        temp = self._game.screen_image()
        temp = temp.resize((temp.width * 2, temp.height * 2))
        temp.save(cache_image_path)
        if ctx is None:
            return await self._channel.send(file=discord.File(cache_image_path))
        else:
            await ctx.send(file=discord.File(cache_image_path))

    @commands.max_concurrency(1, commands.BucketType.channel)
    @_pokemon.command(name="screen", aliases=["畫面", "now"])
    async def _pokemon_get_screen(self, ctx: commands.Context) -> None:
        """
        This function is called when a screen is requested
        """
        if not self._game:
            return await ctx.send("There is no pokemon running!")
        await self._pokemon_screen(ctx)