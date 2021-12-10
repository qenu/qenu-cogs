import asyncio
import re
import time
from dataclasses import dataclass, field
from logging import exception
from typing import Literal, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

PAYMENT_TYPE: dict = {
    0: "其他",
    1: "轉帳",
    2: "歐富寶",
    3: "paypal",
}

COMM_STATUS_TYPE: dict = {
    0: "無",
    1: "草稿",
    2: "線搞",
    3: "上色",
    4: "完工",
}

COMM_TYPE: dict = {
    "客製貼圖": 650,
    "訂閱徽章": 550,
    "小奇點圖": 550,
    "資訊大圖": 700,
    "實況圖層": 0,
    "其他委託": 0,
}

COMMISSION_DATA: dict = {
    "type": None,
    "count": 0,
}

QUOTE_STATUS_TYPE: dict = {
    0: "取消",
    1: "等待中",
    2: "進行中",
    3: "已完成",
}


class Commission:
    def __init__(self, *, _type: str, _count: int = 0, per: int = 0) -> None:
        self._type = _type
        self._count = _count
        self.per = COMM_TYPE.get(_type, per)
        self._status =


@dataclass
class CommissionData:
    commission: list[Commission] = field(default_factory=list)

    def total(self) -> str:
        return_str = ""
        for item in self.commission:
            if item._count != 0:
                return_str += f"{item._type} x{item._count} = {(item._count * item.per) or '報價'}\n"
        return return_str


@dataclass
class CustomerData:
    name: str  # 委託人姓名
    contact: str  # 聯絡方式
    payment_method: int  # 付款方式
    contact_info: str = ""  # 委託人聯絡資訊


@dataclass
class Quote:
    message_id: int  # discord.Message.id
    status: int  # 委託狀態
    last_update: int  # 最後更新時間
    estimate_start_date: str  # 預計開始日期
    timestamp: int  # 時間戳記
    customer_data: CustomerData
    commission_data: CommissionData
    comment: str = ""  # 委託備註


# regex compiles
CUSTOMER_NAME_REGEX = re.compile("委託人:.*\n")
CUSTOMER_CONTACT_REGEX = re.compile("聯絡方式:.*\n")
CUSTOMER_CONTACT_INFO_REGEX = re.compile("聯絡資訊:.*\n")
CUSTOMER_PAYMENT_REGEX = re.compile("付款方式:.*\n")
ESTIMATE_DATE_REGEX = re.compile("預計開始日期:.*\n")
QUOTE_STATUS_REGEX = re.compile("訂單狀態:.*\n")

EMOTE_REGEX = re.compile("客製貼圖:.*\n")
SUBSCRIBE_REGEX = re.compile("訂閱徽章:.*\n")
BITS_REGEX = re.compile("小奇點圖:.*\n")
PANEL_REGEX = re.compile("資訊大圖:.*\n")
LAYER_REGEX = re.compile("實況圖層:.*\n")
OTHER_REGEX = re.compile("其他委託:.*\n")

COMMENT_REGEX = re.compile("備註:.*$")


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
            identifier=0x13969AA179E8081F,
            force_registration=True,
        )
        default_guild: dict = {
            "owner": None,  # discord user id
            "channel_id": None,  # discord channel id
            "quotations": {},
            "pending": [],
            "ongoing": [],
            "finished": [],
            "cancelled": [],
        }
        # self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(
        self, *, requester: RequestType, user_id: int
    ) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    def parse_content(self, content: str) -> Quote:
        """
        Parse content to Quote object

        Parameters
        ----------
        content : str
            content to parse

        Returns
        -------
        Quote
            quote object
        """
        quote_data: dict = {}

        quote_data["message_id"] = 0
        quote_status = QUOTE_STATUS_REGEX.search(content).group().split(":")[1].strip()
        quote_data["status"] = int(quote_status)

        quote_data["last_update"] = int(time.time())
        quote_data["estimate_start_date"] = (
            ESTIMATE_DATE_REGEX.search(content).group().split(":")[1].strip()
        )
        quote_data["timestamp"] = int(time.time())

        customer_name = CUSTOMER_NAME_REGEX.search(content).group().split(":")[1].strip()
        customer_contact = CUSTOMER_CONTACT_REGEX.search(content).group().split(":")[1].strip()
        customer_contact_info = (
            CUSTOMER_CONTACT_INFO_REGEX.search(content).group().split(":")[1].strip()
        )
        customer_payment = CUSTOMER_PAYMENT_REGEX.search(content).group().split(":")[1].strip()
        quote_data["customer_data"] = CustomerData(
            name=customer_name,
            contact=customer_contact,
            payment_method=int(customer_payment),
            contact_info=customer_contact_info,
        )

        def convert_commission(commission_str: str) -> Commission:
            """
            Convert string to Commission object

            Parameters
            ----------
            commission_str : str
                string to convert

            Returns
            -------
            Commission
                converted string
            """
            commission_type, commission_data = commission_str.split(":")
            commission_list = commission_data.split()
            if len(commission_list) == 1:
                per = COMM_TYPE[commission_type]
            else:
                per = int(commission_list[1])
            return Commission(
                _type=commission_type,
                per=per,
                _count=int(commission_list[0]),
            )

        emote = EMOTE_REGEX.search(content).group()
        subscribe = SUBSCRIBE_REGEX.search(content).group()
        bits = BITS_REGEX.search(content).group()
        panel = PANEL_REGEX.search(content).group()
        layer = LAYER_REGEX.search(content).group()
        other = OTHER_REGEX.search(content).group()

        commission = []
        commission.append(convert_commission(emote))
        commission.append(convert_commission(subscribe))
        commission.append(convert_commission(bits))
        commission.append(convert_commission(panel))
        commission.append(convert_commission(layer))
        commission.append(convert_commission(other))

        quote_data["commission_data"] = CommissionData(commission=commission)

        quote_data["comment"] = COMMENT_REGEX.search(content).group().split(":")[1].strip()

        return Quote(**quote_data)

    def workflow_embed(self, ctx: commands.Context, quote_id: int) -> discord.Embed:
        """
        Creates the workflow embed

        Parameters
        ----------
        ctx : commands.Context
        quote_id : int
        """
        quote: Quote = self.config.guild(ctx.guild).quotations.get(quote_id)
        embed = discord.Embed()
        embed.title = f"{quote.customer_data.name}的委託 • {QUOTE_STATUS_TYPE[quote.status]}"
        embed.description = (
            f"最後更新時間: <t:{quote.last_update}:R>\n"
            f"預計開工日期: {quote.estimate_start_date}\n"
            f"聯絡方式: {quote.customer_data.contact}\n"
            f"付款方式: {PAYMENT_TYPE[quote.customer_data.payment_method]}\n"
            f"委託時間: <t:{quote.timestamp}:D>\n"
            "\n"
            "**委託內容:**\n"
        )
        embed.set_footer(text=f"委託編號: #{quote_id} • 訊息編號: {quote.message_id}")
        for item in quote.commission_data.commission:
            if item._count != 0:
                embed.add_field(
                    name=f"{item._type}",
                    value=(
                        f"數量: {item._count}\n" f"進度: {COMM_STATUS_TYPE[item._status]}\n"
                    ),
                    inline=True,
                )

        return embed

    async def update_workflow_message(
        self, ctx: commands.Context, quote_id: int
    ) -> None:
        """
        Update/Creates the workflow embed

        Parameters
        ----------
        ctx : commands.Context
            The context of the command
        quote_id : int
            The quotation id to update
        """
        quote: Quote = self.config.guild(ctx.guild.id).quotations.get(quote_id)
        channel_id: int = self.config.guild(ctx.guild.id).channel
        if not channel_id:
            await ctx.send("找不到工作排程文字頻道，請重新確認設定")
            return
        channel: discord.TextChannel = ctx.guild.get_channel(channel_id)

        try:
            message = await channel.fetch_message(quote.message_id)
        except discord.NotFound:
            return await ctx.send("找不到訊息 discord.NotFound")
        except discord.Forbidden:
            return await ctx.send("沒有訊息權限 discord.Forbidden")
        except discord.HTTPException:
            return await ctx.send("請求失敗，請稍後重試 discord.HTTPException")
        except Exception as e:
            return await ctx.send(f"未知錯誤: {e.__class__.__name__}")

        await message.edit(embed=self.workflow_embed(ctx, quote_id))

    @commands.group(name="workflow", aliases=["wf", "排程"], invoke_without_command=True)
    async def workflow(self, ctx: commands.Context) -> None:
        """
        顯示目前的工作排程


        """
        pass

    @commands.max_concurrency(1, commands.BucketType.guild)
    @workflow.command(name="add", aliases=["a", "新增"])
    async def workflow_add(
        self, ctx: commands.Context, *, content: Optional[str] = None
    ) -> None:
        """
        新增工作

        """
        if not content:
            e = discord.Embed(
                description=(
                    "複製以上格式新增工作排程\n"
                    "---\n"
                    "委託部分數字代表的意思如下\n"
                    "委託內容 數量 報價\n"
                    "報價可以為空或0, 則代表特例價格\n"
                )
            )
            e.add_field(
                name="付款方式",
                value=("   1: 轉帳\n" "   2: 歐富寶\n" "   3: Paypal\n" "   0: 其他\n"),
                inline=True,
            )
            e.add_field(
                name="訂單狀態",
                value=("   1: 等待中\n" "   2: 進行中\n" "   3: 已完成\n" "   0: 取消\n"),
                inline=True,
            )
            explain = await ctx.send(
                content=(
                    "```\n"
                    "委託人:\n"
                    "聯絡方式: \n"
                    "聯絡資訊: \n"
                    "付款方式: 1\n"
                    "預計開始日期: \n"
                    "訂單狀態: 1\n"
                    "---\n"
                    "客製貼圖: 0\n"
                    "訂閱徽章: 0\n"
                    "小奇點圖: 0\n"
                    "資訊大圖: 0\n"
                    "實況圖層: 0\n"
                    "其他委託: 0\n"
                    "---\n"
                    "備註:\n"
                    "```"
                ),
                embed=e,
            )

            try:
                msg = await self.bot.wait_for(
                    "message",
                    timeout=180,
                    check=lambda m: m.author == ctx.author and m.channel == ctx.channel,
                )
                content = msg.content
            except asyncio.TimeoutError:
                return await ctx.send("連線超時，請重新執行指令")

        quote = self.parse_content(content)


        message = await ctx.send("新增工作排程中...")
        quote.message_id = message.id
        # ==================================================
        embed = discord.Embed()
        embed.title = f"{quote.customer_data.name}的委託 • {QUOTE_STATUS_TYPE[quote.status]}"
        embed.description = (
            f"最後更新時間: <t:{quote.last_update}:R>\n"
            f"預計開工日期: {quote.estimate_start_date}\n"
            f"聯絡方式: {quote.customer_data.contact}\n"
            f"付款方式: {PAYMENT_TYPE[quote.customer_data.payment_method]}\n"
            f"委託時間: <t:{quote.timestamp}:D>\n"
            "\n"
            "**委託內容:**\n"
        )
        embed.set_footer(text=f"委託編號: #{'tester_id'} • 訊息編號: {quote.message_id}")
        for item in quote.commission_data.commission:
            if item._count != 0:
                embed.add_field(
                    name=f"{item._type}",
                    value=(
                        f"數量: {item._count}\n" f"進度: {COMM_STATUS_TYPE[item._status]}\n"
                    ),
                    inline=True,
                )

        # ==================================================

        await message.edit(embed=embed)

        await ctx.send(quote)

        # async with self.config.guild(ctx.guild) as guild_data:
        #     next_id = len(guild_data["quotes"]) + 1
        #     guild_data["quotes"][next_id] = quote
        #     if quote.status == 0:
        #         guild_data["cancelled"].append(next_id)
        #     elif quote.status == 1:
        #         guild_data["pending"].append(next_id)
        #     elif quote.status == 2:
        #         guild_data["ongoing"].append(next_id)
        #     elif quote.status == 3:
        #         guild_data["completed"].append(next_id)
