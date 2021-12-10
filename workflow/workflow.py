from dataclasses import dataclass
from typing import Literal, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

from .structure import *

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Workflow(commands.Cog):
    """
    custom tailored project flow system by ba
    """
    """
    All commission statuses would be posted to the same channel,
    where the commisision status would be categorized by config guild,
    reason being in that way we can fetch data for each category easily

    each commission data should also hold message object and id just in case

    also each commission should have a unique id number just for the sake of sanity
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x13969aa179e8081f,
            force_registration=True,
        )
        default_guild: dict = {
            "owner": None, # discord user id
            "channel": None, # discord channel id
            "quotations": {},
            "pending": {},
            "ongoing": {},
            "finished": {},
            "cancelled": {},
        }
        # self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    async def update_workflow_message(self, ctx: commands.Context, quote_id: Optional[int]=None) -> None:
        """
        Update/Creates the workflow embed

        Parameters
        ----------
        ctx : commands.Context
            The context of the command
        quote_id : Optional[int]
            The quotation id to update,
            if None, then it will create a new commission
        """
        guild_data = self.config.guild(ctx.guild.id)
        if not quote_id:
            # creates and update the commission count if not exist
            quote_id = guild_data.commission_count + 1
            await self.config.guild(ctx.guild).quote_count.set(quote_id)

        if not guild_data.channel():
            await ctx.send("找不到工作排程文字頻道，請重新確認設定")
            return
        channel = self.bot.get_channel(guild_data.channel())



    @commands.group(name="workflow", aliases=["wf", "排程"], invoke_without_command=True)
    async def workflow(self, ctx: commands.Context) -> None:
        """
        顯示目前的工作排程


        """
        pass

    @commands.max_concurrency(1, commands.BucketType.guild)
    @workflow.command(name="add", aliases=["a", "新增"])
    async def workflow_add(self, ctx: commands.Context, *, content: str) -> None:
        """
        新增工作

        """
        if not content:
            await ctx.send(
                "請依照格式新增工作排程\n"
                "---\n"
                "委託內容 數量 報價\n"
                "報價可以為空\n"
                )
            await ctx.send(
                "```\n"
                "委託人:\n"
                "聯繫方式: \n"
                "聯絡資訊: \n"
                "預計開始日期: \n"
                "訂單狀態: 等待中\n"
                "--- \n"
                "客製貼圖 0\n"
                "訂閱徽章 0\n"
                "小奇點圖 0\n"
                "資訊大圖 0\n"
                "實況圖層 0\n"
                "其他委託 0\n"
                "```"
            )