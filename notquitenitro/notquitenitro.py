from typing import Literal, Optional

import discord
from redbot.core import commands
from redbot.core.bot import Red
from redbot.core.config import Config

RequestType = Literal["discord_deleted_user", "owner", "user", "user_strict"]


class Notquitenitro(commands.Cog):
    """
    a implementation of NQN
    """

    def __init__(self, bot: Red) -> None:
        self.bot = bot
        self.config = Config.get_conf(
            self,
            identifier=0x2957690346da936b,
            force_registration=True,
        )

        default_guild = {
            "nqn" : False
        }

        self.config.register_guild(**default_guild)

    async def red_delete_data_for_user(self, *, requester: RequestType, user_id: int) -> None:
        # TODO: Replace this with the proper end user data removal handling.
        super().red_delete_data_for_user(requester=requester, user_id=user_id)

    async def nqn_webhook(
        self, channel: discord.TextChannel
    ) -> Optional[discord.Webhook]:
        return discord.utils.get(await channel.webhooks(), name="nqn")

    @commands.command(name="nqn")
    @commands.guild_only()
    @commands.bot_has_permissions(manage_webhooks=True, manage_messages=True)
    async def nqn(self, ctx: commands.Context, emoji_name: str):
        """nqn emote from this guild"""
        pseudo = ctx.author

        emoji = discord.utils.get(ctx.guild.emojis, name=emoji_name)
        if emoji is None:
            await ctx.send(f'Emoji "{emoji_name}" not found.')
            return

        if (webhook := await self.nqn_webhook(ctx.channel)) is None:
            webhook = await ctx.channel.create_webhook(name="nqn")

        await webhook.send(
            content=emoji, username=pseudo.display_name, avatar_url=pseudo.avatar_url
        )
        await ctx.message.delete()

