from __future__ import annotations

import asyncio
import logging
import os

import discord
from discord.ext import commands

from core.module import BotModule

from .client import RoleJob, WarlordsSiteClient


LOGGER = logging.getLogger(__name__)


class RoleSyncWorker:
    def __init__(self, site_url: str, token: str, guild_id: int, pass_role_id: int) -> None:
        self.client = WarlordsSiteClient(site_url, token)
        self.guild_id = guild_id
        self.pass_role_id = pass_role_id
        self._task: asyncio.Task | None = None

    def start(self, bot: commands.Bot) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(bot), name="warlords-role-sync")

    async def _run(self, bot: commands.Bot) -> None:
        while not bot.is_closed():
            delay = 5.0
            try:
                await self.run_once(bot)
            except asyncio.CancelledError:
                raise
            except Exception:
                delay = 15.0
                LOGGER.exception("Не удалось синхронизировать роли Warlords.")
            await asyncio.sleep(delay)

    async def run_once(self, bot: commands.Bot) -> None:
        if bot.user is None:
            return
        guild = bot.get_guild(self.guild_id)
        role = guild.get_role(self.pass_role_id) if guild is not None else None
        error = ""
        if guild is None:
            error = "Discord-сервер не найден"
        elif role is None:
            error = "Роль проходки не найдена"
        elif not _role_assignable(guild, role):
            error = "Роль проходки находится выше роли бота или является управляемой"

        jobs = await asyncio.to_thread(
            self.client.claim,
            bot_user_id=bot.user.id,
            guild_id=self.guild_id,
            pass_role_id=self.pass_role_id,
            pass_role_name=role.name if role is not None else "",
            role_assignable=not error,
            error=error,
        )
        if error or guild is None or role is None:
            return
        for job in jobs:
            job_error = ""
            try:
                await _apply_role(guild, role, job)
            except Exception as exc:
                job_error = _safe_error(exc)
                LOGGER.warning("Не удалось применить роль для Discord user %s: %s", job.discord_user_id, job_error)
            try:
                await asyncio.to_thread(self.client.complete, job, error=job_error)
            except Exception:
                LOGGER.exception("Не удалось подтвердить задачу роли %s.", job.id)


def _role_assignable(guild: discord.Guild, role: discord.Role) -> bool:
    member = guild.me
    return member is not None and not role.managed and role < member.top_role


async def _apply_role(guild: discord.Guild, role: discord.Role, job: RoleJob) -> None:
    try:
        user_id = int(job.discord_user_id)
    except ValueError as error:
        raise RuntimeError("Некорректный Discord user ID") from error
    member = guild.get_member(user_id)
    if member is None:
        try:
            member = await guild.fetch_member(user_id)
        except discord.NotFound:
            if not job.desired:
                return
            raise RuntimeError("Участник не найден на Discord-сервере")
    has_role = role in member.roles
    if job.desired and not has_role:
        await member.add_roles(role, reason="Действующая проходка Warlords")
    elif not job.desired and has_role:
        await member.remove_roles(role, reason="Проходка Warlords недействительна")


def _safe_error(error: Exception) -> str:
    if isinstance(error, discord.Forbidden):
        return "Discord запретил изменение роли"
    if isinstance(error, discord.NotFound):
        return "Участник или роль не найдены"
    if isinstance(error, discord.HTTPException):
        return f"Discord API временно недоступен ({error.status})"
    return str(error)[:500] or error.__class__.__name__


def build_module() -> BotModule:
    site_url = os.getenv("WARLORDS_SITE_URL", "").strip()
    token = os.getenv("WARLORDS_SITE_BOT_TOKEN", "").strip()
    guild_id = os.getenv("APP_COMMAND_GUILD_ID", "").strip()
    pass_role_id = os.getenv("WARLORDS_PASS_ROLE_ID", "").strip()
    worker = None
    if site_url and token and guild_id and pass_role_id:
        if len(token) < 32:
            raise ValueError("WARLORDS_SITE_BOT_TOKEN должен содержать не менее 32 символов.")
        worker = RoleSyncWorker(site_url, token, int(guild_id), int(pass_role_id))
    else:
        LOGGER.warning("Синхронизация ролей Warlords выключена: настройки не заполнены.")

    def register(_bot: commands.Bot) -> None:
        return None

    async def on_ready(bot: commands.Bot) -> None:
        if worker is not None:
            worker.start(bot)

    return BotModule(
        name="warlords_sync",
        description="Синхронизирует роль проходки с правами на сайте.",
        register=register,
        on_ready=on_ready,
    )
