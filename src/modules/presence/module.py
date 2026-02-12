from __future__ import annotations

import discord
from discord.ext import commands

from core.module import BotModule


def build_module() -> BotModule:
    async def on_ready(bot: commands.Bot) -> None:
        members = 0
        for guild in bot.guilds:
            guild_members = guild.member_count or 0
            members += max(guild_members - 1, 0)

        await bot.change_presence(
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name=f"{members} members",
            )
        )

    def register(_bot: commands.Bot) -> None:
        return None

    return BotModule(
        name="presence",
        description="Server presence updater shown on startup.",
        register=register,
        on_ready=on_ready,
    )
