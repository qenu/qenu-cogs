import asyncio
import hashlib
import json
import re
import time
from dataclasses import dataclass
from typing import Literal, Optional
from datetime import datetime

import discord
from discord import mentions
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config
from redbot.core.utils.chat_formatting import box, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS, menu, start_adding_reactions
from redbot.core.utils.predicates import ReactionPredicate

from .utils import GREEN_TICK, GREY_TICK, RED_TICK, replying, send_x

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]

YELLOW = 0xFFC629
GREEN = 0x31F7C6
BLUE = 0x3163F7
GREY = 0x8C8C8C

PENCIL_EMOTE = "✏️"

PRIVILEGED_USERS = [393050606828257287, 164900704526401545]


def privileged(ctx):
    return ctx.author.id in PRIVILEGED_USERS


def make_discordcolor(text: str) -> discord.Color:
    hashed = str(int(hashlib.sha1(text.encode("utf-8")).hexdigest(), 16) % (10 ** 9))
    r = int(hashed[:3]) % 100
    g = int(hashed[3:6]) % 100
    b = int(hashed[6:]) % 100

    return discord.Color.from_rgb(r + 100, g + 100, b + 100)


PAYMENT_TYPE: dict = {
    0: "其他",
    1: "轉帳",
    2: "歐富寶",
    3: "Paypal",
}

COMM_STATUS_TYPE: dict = {
    0: "(無)",
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

COMM_DATA_LIST: dict = {
    "客製貼圖": 0,
    "訂閱徽章": 1,
    "小奇點圖": 2,
    "資訊大圖": 3,
    "實況圖層": 4,
    "其他委託": 5,
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

QUOTE_STATUS_EMOJI: dict = {
    0: RED_TICK,
    1: GREY_TICK,
    2: PENCIL_EMOTE,
    3: GREEN_TICK,
}


@dataclass
class Commission(dict):
    """
    Commission store each individual type of commission

    Parameters:
        _type (str): commission type in COMM_TYPE key
        _count (int): number of commission
        per (int): commission price per unit in COMM_TYPE[_type]
        _status (int): commission status in COMM_STATUS_TYPE key
    """

    def __init__(self, **kwargs) -> None:
        self._type: str = kwargs.get("_type")
        self._count: int = kwargs.get("_count", 0)
        self.per: int = kwargs.get("per", 0)
        self._status: int = kwargs.get("_status", 0)

    @property
    def json(self) -> str:
        return json.dumps(self.__dict__)

    @classmethod
    def from_dict(cls, d: dict) -> "Commission":
        return cls(
            _type=d.get("_type"),
            _count=d.get("_count", 0),
            per=d.get("per", 0),
            _status=d.get("_status", 0),
        )

    def to_dict(self) -> dict:
        return {
            "_type": self._type,
            "_count": self._count,
            "per": self.per,
            "_status": self._status,
        }


@dataclass
class CustomerData:
    """
    Customer's data

    Parameters:
        name (str): customer's name
        contact (str): customer's way of contact
        contact_info (str): customer's contact info
        payment_type (int): customer's payment type in PAYMENT_TYPE key
    """

    name: str  # 委託人姓名
    contact: str  # 聯絡方式
    payment_method: int  # 付款方式
    contact_info: str = ""  # 委託人聯絡資訊


@dataclass
class Quote:
    """
    Stores an individual quotation

    Parameters:
        id (str): quotation id
        message_id (int): quotation message id
        status (int): quotation status in QUOTE_STATUS_TYPE key
        last_update (float): last update timestamp
        estimate_start_date (str): estimated start date
        timestamp (int): quotation creation timestamp
        customer_data (CustomerData): customer's info
        commission_data (list): list of Commission
        comment (str): additional comments
    """

    status: int  # 委託狀態
    last_update: float  # 最後更新時間
    estimate_start_date: str  # 預計開始日期
    timestamp: int  # 時間戳記
    customer_data: CustomerData
    commission_data: list
    payment_received: bool  # 是否已經付款
    comment: str = ""  # 委託備註
    id: Optional[str] = None
    message_id: int = None  # discord.Message.id

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "message_id": self.message_id,
            "status": self.status,
            "last_update": self.last_update,
            "estimate_start_date": self.estimate_start_date,
            "payment_received": self.payment_received,
            "timestamp": self.timestamp,
            "customer_data": self.customer_data.__dict__,
            "commission_data": [item.to_dict() for item in self.commission_data],
            "comment": self.comment,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Quote":
        return cls(
            id=data.get("id"),
            message_id=data.get("message_id"),
            status=data.get("status"),
            last_update=data.get("last_update"),
            estimate_start_date=data.get("estimate_start_date"),
            payment_received=data.get("payment_received", False),
            timestamp=data.get("timestamp"),
            customer_data=CustomerData(**data.get("customer_data")),
            commission_data=[
                Commission(**item) for item in data.get("commission_data")
            ],
            comment=data.get("comment"),
        )


# regex compiles
CUSTOMER_NAME_REGEX = re.compile("委託人:.*\n")
CUSTOMER_CONTACT_REGEX = re.compile("聯絡方式:.*\n")
CUSTOMER_CONTACT_INFO_REGEX = re.compile("聯絡資訊:.*\n")
CUSTOMER_PAYMENT_REGEX = re.compile("付款方式:.*\n")
ESTIMATE_DATE_REGEX = re.compile("預計開始日期:.*\n")
QUOTE_STATUS_REGEX = re.compile("訂單狀態:.*\n")
RECEIVABLE_REGEX = re.compile("付款狀態:.*\n")

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
            "timestamp": int(time.time()),  # last update timestamp
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
        quote_data["timestamp"] = int(time.time())
        quote_data["last_update"] = time.time()

        quote_status = QUOTE_STATUS_REGEX.search(content)
        if quote_status is None:
            raise ValueError("找不到`訂單狀態`。")
        quote_data["status"] = int(quote_status.group().split(":")[1].strip())

        estimate_start_date = ESTIMATE_DATE_REGEX.search(content)
        if estimate_start_date is None:
            raise ValueError("找不到`預計開始日期`。")
        quote_data["estimate_start_date"] = (
            estimate_start_date.group().split(":")[1].strip()
        )

        payment_received = RECEIVABLE_REGEX.search(content)
        if payment_received is None:
            raise ValueError("找不到`付款狀態`。")
        quote_data["payment_received"] = bool(
            int(payment_received.group().split(":")[1].strip())
        )

        name = CUSTOMER_NAME_REGEX.search(content)
        if name is None:
            raise ValueError("找不到`委託人`。")
        customer_name = (
            name.group().split(":")[1].strip()
        )

        contact = CUSTOMER_CONTACT_REGEX.search(content)
        if contact is None:
            raise ValueError("找不到`聯絡方式`。")
        customer_contact = (
            contact.group().split(":")[1].strip()
        )

        contact_info = CUSTOMER_CONTACT_INFO_REGEX.search(content)
        if contact_info is None:
            raise ValueError("找不到`聯絡資訊`。")
        customer_contact_info = (
            contact_info.group().split(":")[1].strip()
        )

        payment = CUSTOMER_PAYMENT_REGEX.search(content)
        if payment is None:
            raise ValueError("找不到`付款方式`。")
        customer_payment = (
            payment.group().split(":")[1].strip()
        )

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
            per = COMM_TYPE.get(commission_type, 0)
            if len(commission_list) == 2:
                per = int(commission_list[1])

            return Commission(
                _type=commission_type,
                per=per,
                _count=int(commission_list[0]),
            )

        emote = EMOTE_REGEX.search(content)
        subscribe = SUBSCRIBE_REGEX.search(content)
        bits = BITS_REGEX.search(content)
        panel = PANEL_REGEX.search(content)
        layer = LAYER_REGEX.search(content)
        other = OTHER_REGEX.search(content)

        if any([result is None for result in [emote, subscribe, bits, panel, layer, other]]):
            raise ValueError("缺少委託項目，請重新確認。")

        commission = []
        commission.append(convert_commission(emote.group()))
        commission.append(convert_commission(subscribe.group()))
        commission.append(convert_commission(bits.group()))
        commission.append(convert_commission(panel.group()))
        commission.append(convert_commission(layer.group()))
        commission.append(convert_commission(other.group()))

        quote_data["commission_data"] = commission

        comment = COMMENT_REGEX.search(content)
        if comment is None:
            raise ValueError("找不到`備註`。")
        quote_data["comment"] = (
            comment.group().split(":")[1].strip()
        )

        return Quote(**quote_data)

    async def workflow_embed(self, ctx: commands.Context, **kwargs) -> discord.Embed:
        """
        Creates the workflow embed

        Parameters
        ----------
        ctx : commands.Context
        quote_id : Optiona[int]
            or
        quote : Optional[Quote]
        detail : Optional[bool]

        Returns
        -------
        discord.Embed
        """
        no_update: bool = kwargs.get("no_update", False)
        quote: Quote = kwargs.get("quote", None)
        if quote is None and (quote_id := kwargs.get("quote_id")) is not None:
            quotes_data: dict = await self.config.guild(ctx.guild).quotations()
            quote_data: dict = quotes_data.get(str(quote_id), {})
            quote = Quote.from_dict(quote_data)
        else:
            return await ctx.send("Missing both quote and quote_id")

        detail = kwargs.get("detail", False)
        channel_id = await self.config.guild(ctx.guild).channel_id()

        embed = discord.Embed()
        embed.title = f"{QUOTE_STATUS_EMOJI[quote.status]}【{QUOTE_STATUS_TYPE[quote.status]}】{quote.customer_data.name}的委託"

        embed.description = (
            f"預計開工日期: {quote.estimate_start_date}\n"
            f"委託時間: <t:{int(quote.timestamp)}:D>\n"
        )
        if detail:
            embed.description += (
                f"聯絡方式: {quote.customer_data.contact}\n"
                f"付款方式: {PAYMENT_TYPE[quote.customer_data.payment_method]}\n"
                f"備註: {quote.comment}\n"
                f"[原始訊息超連結](https://discordapp.com/channels/{ctx.guild.id}/{channel_id}/{quote.message_id})\n"
            )
        embed.description += "\n" "**↓ 委託內容 ↓**\n"
        embed.set_footer(
            text=(
                f"委託編號: #{quote_id} • "
                f"{'已付款 👌' if quote.payment_received else '未付款 🤏'}\n"
                "最後更新時間"
            )
        )
        embed.timestamp = datetime.fromtimestamp(int(quote.last_update))
        total_commission = 0
        for item in quote.commission_data:
            if item._count != 0:
                value_content = (
                    f"數量: {item._count}\n" f"進度: {COMM_STATUS_TYPE[item._status]}\n"
                )
                if detail:
                    value_content += (
                        f"單價: {item.per}\n" if item.per != 0 else "單價: 報價\n"
                    )
                    value_content += (
                        f"總價: {item.per * item._count}\n"
                        if item.per != 0
                        else f"總價: 報價x{item._count}\n"
                    )
                    total_commission += item.per * item._count
                embed.add_field(
                    name=f"{item._type}",
                    value=value_content,
                    inline=True,
                )

        if detail:
            embed.add_field(
                name="總價(不包含報價)",
                value=f"{total_commission or '報價'}",
                inline=False,
            )
            embed.add_field(
                name="聯絡資訊",
                value=quote.customer_data.contact_info or "無",
                inline=False,
            )

        # embed.color = QUOTE_STATUS_COLOR[quote.status]
        embed.color = make_discordcolor(quote.customer_data.name)

        return embed

    async def update_workflow_message(
        self, ctx: commands.Context, quote_id: int, **kwargs
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
        no_update: bool = kwargs.get("no_pdate", False)
        quotes_data: dict = await self.config.guild(ctx.guild).quotations()
        quote_data: dict = quotes_data.get(str(quote_id))
        quote = Quote.from_dict(quote_data)
        channel_id: int = await self.config.guild(ctx.guild).channel_id()
        if not channel_id:
            channel = ctx.channel
        else:
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
            return await ctx.send(f"未知錯誤: `{e}`")

        await message.edit(
            content=None, embed=await self.workflow_embed(ctx, quote_id=quote_id, no_update=no_update)
        )
        if not no_update:
            await self.config.guild(ctx.guild).timestamp.set(int(time.time()))

    @commands.check(privileged)
    @commands.group(name="workflow", aliases=["wf", "排程"], invoke_without_command=True)
    async def workflow(self, ctx: commands.Context) -> None:
        """
        顯示目前的工作排程

        """
        embed = discord.Embed()
        embed.title = "工作排程 Workflow"
        guild_data = await self.config.guild(ctx.guild).all()
        embed.set_footer(text=f"頻道: {ctx.guild.get_channel(guild_data['channel_id'])}")
        embed.description = (
            f"最後更新: <t:{int(guild_data['timestamp'])}:R>\n"
            "---\n"
            f"**總數量:** {len(guild_data['quotations'])}\n"
            f"**已完成:** {len(guild_data['finished'])}\n"
        )
        pending_quotes = []
        for item in guild_data["pending"]:
            pending_quotes.append(
                f"#{item} {guild_data['quotations'][item]['customer_data']['name']}\n"
            )

        embed.add_field(
            name=QUOTE_STATUS_TYPE[1],
            value="".join(pending_quotes) or "(無)",
            inline=True,
        )

        ongoing_quotes = []
        for item in guild_data["ongoing"]:
            ongoing_quotes.append(
                f"#{item} {guild_data['quotations'][item]['customer_data']['name']}\n"
            )

        embed.add_field(
            name=QUOTE_STATUS_TYPE[2],
            value="".join(ongoing_quotes) or "(無)",
            inline=True,
        )

        finished_quotes = []
        for item in guild_data["finished"]:
            finished_quotes.append(
                f"#{item} {guild_data['quotations'][item]['customer_data']['name']}\n"
            )
        finished_quotes.reverse()
        if len(finished_quotes) > 10:
            finished_quotes = finished_quotes[:10]
            finished_quotes.append(f"...以及另 {len(finished_quotes)-10}個\n")
        embed.add_field(
            name=QUOTE_STATUS_TYPE[3],
            value="".join(finished_quotes) or "(無)",
            inline=True,
        )
        embed.color = ctx.author.color

        await ctx.message.delete()
        await send_x(ctx=ctx, embed=embed)

    @commands.is_owner()
    @workflow.group(name="dev")
    async def workflow_dev(self, ctx: commands.Context) -> None:
        pass

    @workflow_dev.command(name="info")
    async def workflow_dev_info(self, ctx: commands.Context) -> None:
        """
        Show data stored in workflow config
        """
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
        for item in guild_data["quotations"]:
            quote: Quote = guild_data["quotations"][item]
            return_content += f"{item} : " + quote.__repr__() + "\n"
        await menu(
            ctx, [box(i, lang="yaml") for i in pagify(return_content)], DEFAULT_CONTROLS
        )

    @workflow_dev.command(name="update")
    async def workflow_dev_update(self, ctx: commands.Context, quote_id: int) -> None:
        """Force updates a message"""
        await self.update_workflow_message(ctx, quote_id, no_update=True)
        await ctx.tick()
        await ctx.message.delete(delay=5)

    @workflow_dev.command(name="reset")
    async def workflow_dev_reset(self, ctx: commands.Context) -> None:
        """Resets the whole workflow config"""
        await self.config.guild(ctx.guild).clear()
        await replying(ctx=ctx, content="已重置排程。")

    @workflow_dev.command(name="channel")
    async def workflow_dev_channel(
        self, ctx: commands.Context, *, channel: Optional[discord.TextChannel]
    ) -> None:
        """Sets the channel for quotes"""
        if channel is None:
            await self.config.guild(ctx.guild).channel_id.clear()
            await send_x(ctx=ctx, content="已重置頻道。")
        else:
            await self.config.guild(ctx.guild).channel_id.set(channel.id)
            await send_x(ctx=ctx, content="已設定頻道。")

    @workflow.command(name="command", aliases=["cmd", "指令"])
    async def workflow_command(self, ctx: commands.Context) -> None:
        """顯示排程指令列表"""
        embed = discord.Embed()
        embed.title = "排程指令列表"
        embed.description = (
            "**顯示排程表**\n"
            f"`{ctx.clean_prefix}排程`\n"
            "顯示目前的工作排程數量\n\n"
            "**新增排程**\n"
            f"`{ctx.clean_prefix}排程 新增`\n"
            "新增一個排程工作\n\n"
            "**更新排程**\n"
            f"`{ctx.clean_prefix}排程 更新 <委託編號> <內容>`\n"
            "**排成後台**\n"
            f"`{ctx.clean_prefix}排程 dev`\n"
            "=====\n"
            "**快速指令**\n"
            f"`{ctx.clean_prefix}委託`\n"
        )
        embed.color = ctx.me.color
        await ctx.message.delete()
        await send_x(ctx=ctx, embed=embed)

    @commands.max_concurrency(1, commands.BucketType.guild)
    @workflow.command(name="add", aliases=["a", "新增"])
    async def workflow_add(
        self, ctx: commands.Context, *, content: Optional[str] = None
    ) -> None:
        """
        新增排程工作

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
            e.color = ctx.me.color
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
            e.add_field(
                name="付款狀態",
                value=("   1: 已付款\n" "   0: 未付款\n"),
                inline=True,
            )
            fmt_message = await ctx.send(
                content=(
                    "```\n"
                    "委託人:\n"
                    "聯絡方式: \n"
                    "聯絡資訊: \n"
                    "付款方式: 1\n"
                    "預計開始日期: \n"
                    "訂單狀態: 1\n"
                    "付款狀態: 0\n"
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
            else:
                await msg.delete()

        try:
            quote: Quote = self.parse_content(content)
        except AttributeError as e:
            await fmt_message.delete()
            return await ctx.send(f"輸入格式錯誤!\n`{e}`", delete_after=15)
        except ValueError as e:
            await fmt_message.delete()
            return await ctx.send(f"輸入格式錯誤!\n`{e}`", delete_after=15)

        if quote.customer_data.name == "":
            await fmt_message.delete()
            return await ctx.send("委託人不能為空白", delete_after=15)
        if quote.customer_data.contact_info == "":
            await fmt_message.delete()
            return await ctx.send("聯絡資訊不能為空白", delete_after=15)

        channel_id = await self.config.guild(ctx.guild).channel_id()
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
        else:
            channel = ctx.channel

        message = await channel.send("新增工作排程中...")
        quote.message_id = message.id

        async with self.config.guild(ctx.guild).all() as guild_data:
            guild_data["quote_number"] += 1
            next_id = str(guild_data["quote_number"])
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

        await self.update_workflow_message(ctx, quote.id)
        await fmt_message.delete()

    @workflow.command(name="info", aliases=["i", "查看"])
    async def workflow_info(self, ctx: commands.Context, quote_id: int) -> None:
        """
        取得排程詳細內容

        """
        embed = await self.workflow_embed(ctx, quote_id=quote_id, detail=True)
        author = ctx.author
        await author.send(embed=embed)
        await ctx.tick()
        await ctx.message.delete(delay=5)

    @workflow.command(name="edit", aliases=["e", "編輯", "更新"])
    async def workflow_edit(
        self,
        ctx: commands.Context,
        quote_id: int,
        edit_type: str,
        *,
        content: str,
    ) -> None:
        """
        更新委託內容
        ---
        下面有詳細解釋

        **項目:**
            委託人, 聯絡方式, 聯絡資訊, 開工日期, 備註

        **特別項目:**
            付款方式: [1: 轉帳, 2: 歐富寶, 3: Paypal, 0: 其他]
            進度: [1: 等待中, 2: 進行中, 3: 已完成, 0: 取消]
            付款狀態: [1: 已付款, 0: 未付款]

        **委託細項:**
            客製貼圖, 訂閱徽章, 小奇點圖, 資訊大圖, 實況圖層, 其他委託
        **委託項目:**
            數量, 價格
            進度: [1: 草稿, 2: 線搞, 3: 上色, 4: 完工, 0: 無]

        **範例:**
            `o.排程 更新 <#編號> 委託人 <委託人名稱>`
            `o.排程 更新 <#編號> 付款方式 3`
            `o.排程 更新 <#編號> 客製貼圖 進度 4`
            `o.排程 更新 <#編號> 資訊大圖 價格 800`
        """
        if edit_type not in [
            "委託人",
            "聯絡方式",
            "聯絡資訊",
            "開工日期",
            "備註",
            "付款方式",
            "付款狀態",
            "進度",
            "客製貼圖",
            "訂閱徽章",
            "小奇點圖",
            "資訊大圖",
            "實況圖層",
            "其他委託",
        ]:
            return await ctx.send(f"{edit_type}不是正確的項目，請輸入正確的項目名稱")

        quotation_edit: bool = edit_type in [
            "客製貼圖",
            "訂閱徽章",
            "小奇點圖",
            "資訊大圖",
            "實況圖層",
            "其他委託",
        ]

        async with self.config.guild(ctx.guild).quotations() as quotations:
            quote_data = quotations.get(str(quote_id))
            if not quote_data:
                return await ctx.send(f"找不到該委託編號 #{quote_id}", delete_after=15)
            quote: Quote = Quote.from_dict(quote_data)
            new_status = None
            if quote.status == 1:
                old_status = "pending"
            elif quote.status == 2:
                old_status = "ongoing"
            elif quote.status == 3:
                old_status = "completed"
            elif quote.status == 0:
                old_status = "cancelled"

            if quotation_edit:
                quote_type, val = content.split()
                if quote_type == "價格":
                    quote.commission_data[COMM_DATA_LIST[edit_type]]._per = val
                elif quote_type == "數量":
                    quote.commission_data[COMM_DATA_LIST[edit_type]]._count = val
                elif quote_type == "進度":
                    val = int(val)
                    if val not in [1, 2, 3, 4, 0]:
                        return await ctx.send(f"進度代號錯誤，請輸入正確的代號")
                    quote.commission_data[COMM_DATA_LIST[edit_type]]._status = int(val)
            elif edit_type == "委託人":
                quote.customer_data.name = content
            elif edit_type == "聯絡方式":
                quote.customer_data.contact = content
            elif edit_type == "聯絡資訊":
                quote.customer_data.contact_info = content
            elif edit_type == "開工日期":
                quote.estimate_start_date = content
            elif edit_type == "備註":
                quote.comment = content
            elif edit_type == "付款狀態":
                quote.payment_received = bool(content)
            elif edit_type == "付款方式":
                quote.customer_data.payment_method = int(content)
            elif edit_type == "進度":
                quote.status = int(content)
                if quote.status == 1:
                    new_status = "pending"
                elif quote.status == 2:
                    new_status = "ongoing"
                elif quote.status == 3:
                    new_status = "completed"
                elif quote.status == 0:
                    new_status = "cancelled"

            quote.last_update = time.time()
            quotations[str(quote_id)] = quote.to_dict()

        if new_status:
            async with self.config.guild(ctx.guild).all() as guild_data:
                guild_data[old_status].remove(str(quote_id))
                guild_data[new_status].append(str(quote_id))

        await self.update_workflow_message(ctx, quote.id)
        await ctx.tick()
        await ctx.message.delete(delay=10)

    @commands.check(privileged)
    @commands.command(name="workflowutil", aliases=["wfu", "委託"])
    async def workflow_utility(
        self, ctx: commands.Context, quote_id: int, *, content: Optional[str] = None
    ) -> None:
        """
        排程委託快速指令
        ---
        輸入關鍵字可以快速操作

        **關鍵字:**
        進度類別:
        > 等待中, 進行中, 已完成, 取消
        > 已付款, 未付款

        委託分類:
        > 客製貼圖, 訂閱徽章, 小奇點圖, 資訊大圖, 實況圖層, 其他委託
        委託進度:
        > 草稿, 線搞, 上色, 完工, 無

        **範例:**
        `o.委託 <#編號> 進行中`
        `o.委託 <#編號> 資訊大圖 上色`
        """
        if content is None:
            embed = await self.workflow_embed(ctx, quote_id=quote_id, detail=True)
            return await ctx.author.send(embed=embed)

        async with self.config.guild(ctx.guild).quotations() as quotations:
            quote_data = quotations.get(str(quote_id))
            if not quote_data:
                return await ctx.send(f"找不到該委託編號 #{quote_id}", delete_after=15)
            quote: Quote = Quote.from_dict(quote_data)
            new_status = None
            if content == "等待中":
                quote.status = 1
                new_status = "pending"
            elif content == "進行中":
                quote.status = 2
                new_status = "ongoing"
            elif content == "已完成":
                quote.status = 3
                new_status = "finished"
                # if the quote is finished
                # then all commissions should be finished
                for item in quote.commission_data:
                    if item._count != 0:
                        item._status = 4
            elif content == "取消":
                quote.status = 0
                new_status = "cancelled"

            elif content == "已付款":
                quote.payment_received = True
            elif content == "未付款":
                quote.payment_received = False
            else:
                try:
                    quote_type, status_val = content.split()
                except ValueError:
                    return await send_x(ctx=ctx, content=f"{content} 這個關鍵字不存在")
                if status_val is None or status_val not in [
                    "草稿",
                    "線搞",
                    "上色",
                    "完工",
                    "無",
                ]:
                    return await send_x(
                        ctx=ctx, content=f"{status_val} 關鍵字錯誤，請輸入正確的關鍵字"
                    )
                val = 0
                if status_val == "草稿":
                    val = 1
                elif status_val == "線搞":
                    val = 2
                elif status_val == "上色":
                    val = 3
                elif status_val == "完工":
                    val = 4

                quote.commission_data[COMM_DATA_LIST[quote_type]]._status = val

                # if commission status is within working range
                # then change quote status to ongoing
                if val != 0 and val != 4:
                    if quote.status != 2:
                        quote.status = 2
                        new_status = "ongoing"

            quote.last_update = time.time()
            quotations[str(quote_id)] = quote.to_dict()

        if new_status:
            async with self.config.guild(ctx.guild).all() as guild_data:
                not_quote_id = lambda x: x != str(quote_id)

                guild_data["pending"] = list(
                    filter(not_quote_id, guild_data["pending"])
                )
                guild_data["ongoing"] = list(
                    filter(not_quote_id, guild_data["ongoing"])
                )
                guild_data["finished"] = list(
                    filter(not_quote_id, guild_data["finished"])
                )
                guild_data["cancelled"] = list(
                    filter(not_quote_id, guild_data["cancelled"])
                )

                guild_data[new_status].append(str(quote_id))

        await self.update_workflow_message(ctx, quote.id)
        await ctx.tick()

    @commands.check(privileged)
    @commands.command(name="workflowcreate", aliases=["wfc", "新委託"])
    async def workflow_create(
        self,
        ctx: commands.Context,
    ) -> None:
        """
        新增委託
        """
        await ctx.message.delete(delay=10)
        return await ctx.invoke(self.bot.get_command("workflow add"))

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot:
            return
        if message.author.id not in PRIVILEGED_USERS:
            return
        if message.channel.id not in [874511958563491861, 901016201566769152]:
            return
        if message.content.startswith("委託人"):
            confirmation = await message.reply(content="請問要增加委託嗎?")
            start_adding_reactions(confirmation, ReactionPredicate.YES_OR_NO_EMOJIS)
            pred = ReactionPredicate.yes_or_no(confirmation, user=message.author)
            try:
                await self.bot.wait_for("reaction_add", check=pred, timeout=20)
            except asyncio.TimeoutError:
                await confirmation.delete()
                return
            if pred.result:
                await confirmation.clear_reactions()
                await self.workflow_add(message.channel, message.content)
                return
            else:
                await confirmation.delete()
                return