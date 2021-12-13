import asyncio
import re
import time
import json
from dataclasses import dataclass, field, asdict
from typing import Literal, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

YELLOW = 0xffc629
GREEN = 0x31f7c6
BLUE = 0x3163f7
GREY = 0x8c8c8c

PRIVILEGED_USERS = [393050606828257287, 164900704526401545]

def privileged(ctx):
    return ctx.author.id in PRIVILEGED_USERS

PAYMENT_TYPE: dict = {
    0: "其他",
    1: "轉帳",
    2: "歐富寶",
    3: "Paypal",
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

QUOTE_STATUS_TYPE: dict = {
    0: "取消",
    1: "等待中",
    2: "進行中",
    3: "已完成",
}

QUOTE_STATUS_COLOR: dict = {
    0: GREY,
    1: YELLOW,
    2: GREEN,
    3: BLUE,
}


@dataclass
class Commission(dict):
    def __init__(self, *, _type: str, _count: int = 0, per: int = 0) -> None:
        self._type = _type
        self._count = _count
        self.per = COMM_TYPE.get(_type, per)
        self._status = 0

    @property
    def __dict__(self) -> dict:
        return asdict(self)

    @property
    def json(self) -> str:
        return json.dumps(self.__dict__)


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

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "status": self.status,
            "last_update": self.last_update,
            "estimate_start_date": self.estimate_start_date,
            "timestamp": self.timestamp,
            "customer_data": self.customer_data.__dict__,
            "commission_data": self.commission_data.__dict__,
            "comment": self.comment,
        }

    def from_dict(self, data: dict) -> None:
        self.message_id = data["message_id"]
        self.status = data["status"]
        self.last_update = data["last_update"]
        self.estimate_start_date = data["estimate_start_date"]
        self.timestamp = data["timestamp"]
        self.customer_data = CustomerData(**data["customer_data"])
        self.commission_data = CommissionData(**data["commission_data"])
        self.comment = data["comment"]


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
            "channel_id": None,  # discord channel id
            "timestamp": time.time(),  # last update timestamp
            "quote_number": 0,  # last quote number
            "quotations": {},
            "pending": [],
            "ongoing": [],
            "finished": [],
            "cancelled": [],
        }
        self.config.register_guild(**default_guild)

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

    async def workflow_embed(self, ctx: commands.Context, *, quote_id: Optional[int]=None, quote: Optional[Quote]=None) -> discord.Embed:
        """
        Creates the workflow embed

        Parameters
        ----------
        ctx : commands.Context
        quote_id : Optiona[int]
            or
        quote : Optional[Quote]

        Returns
        -------
        discord.Embed
        """
        if quote_id is not None:
            quote: Quote = await self.config.guild(ctx.guild).quotations.get(quote_id)
        embed = discord.Embed()
        embed.title = f"【{QUOTE_STATUS_TYPE[quote.status]}】{quote.customer_data.name}的委託"
        embed.description = (
            f"最後更新時間: <t:{quote.last_update}:f>\n"
            f"預計開工日期: {quote.estimate_start_date}\n"
            f"聯絡方式: {quote.customer_data.contact}\n"
            f"付款方式: {PAYMENT_TYPE[quote.customer_data.payment_method]}\n"
            f"委託時間: <t:{int(quote.timestamp)}:D>\n"
            "\n"
            "**委託內容 ↓**\n"
        )
        embed.set_footer(text=f"委託編號: #{quote_id} • 訊息ID: {quote.message_id}")
        for item in quote.commission_data.commission:
            if item._count != 0:
                embed.add_field(
                    name=f"{item._type}",
                    value=(
                        f"數量: {item._count}\n" f"進度: {COMM_STATUS_TYPE[item._status]}\n"
                    ),
                    inline=True,
                )
        embed.color = QUOTE_STATUS_COLOR[quote.status]

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
        quote_data: dict = await self.config.guild(ctx.guild).quotations().get(quote_id)
        quote: Quote = Quote(**quote_data)
        channel_id: int = await self.config.guild(ctx.guild).channel()
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

        await message.edit(content=None, embed=await self.workflow_embed(ctx, quote_id=quote_id))

    @commands.check(privileged)
    @commands.group(name="workflow", aliases=["wf", "排程"], invoke_without_command=True)
    async def workflow(self, ctx: commands.Context) -> None:
        """
        顯示目前的工作排程

        """
        embed = discord.Embed()
        embed.title = "工作排程 Workflow"
        guild_data = await self.config.guild(ctx.guild).all()
        embed.description = (
            f"頻道: {ctx.guild.get_channel(guild_data['channel_id'])}\n"
            f"最後更新: <t:{int(guild_data['timestamp'])}:R>\n"
            "---\n"
            f"**總數量:** {len(guild_data['quotations'])}\n"
            f"**已完成:** {len(guild_data['finished'])}\n"
        )
        pending_quotes = []
        for item in guild_data['pending']:
            pending_quotes.append(f"#{item} {guild_data['quotations'][item].customer_data.name}\n")

        embed.add_field(
            name=QUOTE_STATUS_TYPE[1],
            value=''.join(pending_quotes) or '無項目',
            inline=False,
        )

        ongoing_quotes = []
        for item in guild_data['ongoing']:
            ongoing_quotes.append(f"#{item} {guild_data['quotations'][item].customer_data.name}\n")

        embed.add_field(
            name=QUOTE_STATUS_TYPE[2],
            value=''.join(ongoing_quotes) or '無項目',
            inline=False,
        )

        finished_quotes = []
        for item in guild_data['finished']:
            finished_quotes.append(f"#{item} {guild_data['quotations'][item].customer_data.name}\n")
        finished_quotes.reverse()
        if len(finished_quotes) > 10:
            finished_quotes = finished_quotes[:10]
            finished_quotes.append(f"...以及另 {len(finished_quotes)-10}個\n")
        embed.add_field(
            name=QUOTE_STATUS_TYPE[3],
            value=''.join(finished_quotes) or '無項目',
            inline=False,
        )
        embed.color = ctx.author.color

        await ctx.send(embed=embed, delete_after=60)

    @commands.is_owner()
    @workflow.group(name="dev")
    async def workflow_dev(self, ctx: commands.Context) -> None:
        pass

    @workflow_dev.command(name="info")
    async def workflow_dev_info(self, ctx: commands.Context) -> None:
        guild_data = await self.config.guild(ctx.guild).all()
        return_content = (
            f"channel_id: {guild_data['channel_id']}\n"
            f"timestamp: {int(guild_data['timestamp'])}\n"
            f"quote_number: {guild_data['quote_number']}\n"
            f"pending: {guild_data['pending']}\n"
            f"ongoing: {guild_data['ongoing']}\n"
            f"finished: {guild_data['finished']}\n"
            f"cancelled: {guild_data['cancelled']}\n"
            f"quotations: \n"
        )
        for item in guild_data['quotations']:
            quote: Quote = guild_data['quotations'][item]
            return_content += quote.__repr__() + "\n"
        await menu(ctx, [box(i, lang="yaml") for i in pagify(return_content)], DEFAULT_CONTROLS)

    @workflow_dev.command(name="reset")
    async def workflow_dev_reset(self, ctx: commands.Context) -> None:
        await self.config.guild(ctx.guild).clear()
        await ctx.send("工作排程已重置")

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
            await ctx.send(
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
                delete_after=120,
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

        async with self.config.guild(ctx.guild).all() as guild_data:
            guild_data["quote_number"] += 1
            next_id = guild_data["quote_number"]
            quote.id = next_id
            guild_data["quotations"][next_id] = quote.to_dict()
            if quote.status == 0:
                guild_data["cancelled"].append(next_id)
            elif quote.status == 1:
                guild_data["pending"].append(next_id)
            elif quote.status == 2:
                guild_data["ongoing"].append(next_id)
            elif quote.status == 3:
                guild_data["completed"].append(next_id)

        await self.update_workflow_message(ctx, quote_id=quote.id)

    @workflow.command(name="info", aliases=["i", "查看"])
    async def workflow_info(self, ctx: commands.Context, quote_id: int) -> None:
        """
        私訊使用者工作排程詳細內容

        """
        embed = self.workflow_embed(ctx, quote_id)
        author = ctx.author
    #     async with self.config.guild(ctx.guild).all() as guild_data:

    #     await self.update_workflow_message(ctx, quote_id=quote_id)


    # @workflow.command(name="edit", aliases=["e", "編輯", "更新"])
    # async def workflow_edit(self, ctx: commands.Context, quote_id: int, edit_type: str, *, content: str) -> None:
    #     """
    #     編輯工作排程

    #     """
    #     if edit_type not in ["status", "content", "price"]:
    #         return await ctx.send("請輸入正確的編輯類型")
    #     if edit_type == "status":
    #         if content not in ["0", "1", "2", "3"]:
    #             return await ctx.send("請輸入正確的狀態")
    #         content = int(content)
    #     elif edit_type == "price":
    #         if content == "":
    #             content = 0
    #         else:
    #             try:
    #                 content = int(content)
    #             except ValueError:
    #                 return await ctx.send("請輸入正確的價格")
    #     else:
    #         content = content.replace("\n", "")

    #     async with self.config.guild(ctx.guild).all() as guild_data:
    #         if quote_id not in guild_data["quotations"]:
    #             return await ctx.send("找不到該工作排程")
    #         quote = guild_data["quotations"][quote_id]
    #         if edit_type == "status":
    #             if quote.status == content:
    #                 return await ctx.send("該工作排程狀態已經是該狀態")
    #             if quote.status == 0:
    #                 guild_data["cancelled"].remove(quote_id)
    #             elif quote.status == 1:
    #                 guild_data["pending"].remove(quote_id)
    #             elif quote.status == 2:
    #                 guild_data["ongoing"].remove(quote_id)
    #             elif quote.status == 3:
    #                 guild_data["completed"].remove(quote_id)
