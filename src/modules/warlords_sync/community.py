from __future__ import annotations

import asyncio
import logging
import re
import sqlite3
from contextlib import closing
from pathlib import Path
from urllib.request import urlopen

import discord

from .client import WarlordsSiteClient

LOGGER = logging.getLogger(__name__)


class CommunityWorker:
    def __init__(self, client: WarlordsSiteClient, guild_id: int, path: Path) -> None:
        self.client = client
        self.guild_id = guild_id
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self._task: asyncio.Task | None = None
        self._role_cache: dict[str, object] = {}
        self._icon_versions: dict[int, str] = {}
        self._icons_supported: bool | None = None
        with closing(sqlite3.connect(path)) as db, db:
            db.execute("CREATE TABLE IF NOT EXISTS delivered (id TEXT PRIMARY KEY, delivered_at TEXT DEFAULT CURRENT_TIMESTAMP)")
            db.execute("CREATE TABLE IF NOT EXISTS owned_roles (faction_id TEXT PRIMARY KEY, role_id TEXT NOT NULL)")

    def start(self, bot) -> None:
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._run(bot), name="warlords-community-sync")

    async def _run(self, bot) -> None:
        while not bot.is_closed():
            try:
                await self.run_once(bot)
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Community synchronization failed")
            await asyncio.sleep(10)

    async def run_once(self, bot) -> None:
        self._role_cache.clear()
        guild = bot.get_guild(self.guild_id)
        capabilities = {"guild_id": str(self.guild_id)}
        if guild is not None:
            available = "ROLE_ICONS" in guild.features
            capabilities["role_icons_available"] = available
            if available != self._icons_supported:
                LOGGER.info("Discord faction role icons available: %s", available)
                self._icons_supported = available
        payload = await asyncio.to_thread(self.client._request, "/api/v1/bot/community/claim", capabilities)
        jobs = payload.get("jobs", [])
        if not isinstance(jobs, list):
            raise RuntimeError("Invalid community jobs")
        for job in jobs:
            error = ""
            role_id = ""
            try:
                if job["kind"] == "notification":
                    await self._notify(bot, job)
                elif job["kind"] == "membership":
                    if guild is None:
                        raise RuntimeError("Discord server unavailable")
                    role_id = await self._membership(guild, job)
                else:
                    raise RuntimeError("Unknown community event")
            except asyncio.CancelledError:
                raise
            except discord.HTTPException as exc:
                error = f"Discord HTTP {exc.status}"
            except Exception as exc:
                error = str(exc)[:300] or type(exc).__name__
            try:
                await asyncio.to_thread(
                    self.client._request,
                    f"/api/v1/bot/community/{job['id']}/complete",
                    {"lease_token": job["lease_token"], "succeeded": not error, "error": error, "role_id": role_id},
                    allow_empty=True,
                )
            except Exception:
                LOGGER.exception("Community acknowledgement failed for %s", job["id"])
            if error:
                LOGGER.warning("Community job %s failed: %s", job["id"], error)

    def _delivered(self, event_id: str) -> bool:
        with closing(sqlite3.connect(self.path)) as db, db:
            return db.execute("SELECT 1 FROM delivered WHERE id=?", (event_id,)).fetchone() is not None

    def _mark_delivered(self, event_id: str) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT OR IGNORE INTO delivered(id) VALUES(?)", (event_id,))
            db.execute("DELETE FROM delivered WHERE delivered_at < datetime('now','-90 days')")

    def _owned_role(self, faction_id: str) -> str:
        with closing(sqlite3.connect(self.path)) as db:
            row = db.execute("SELECT role_id FROM owned_roles WHERE faction_id=?", (faction_id,)).fetchone()
            return row[0] if row else ""

    def _record_role(self, faction_id: str, role_id: int) -> None:
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute("INSERT INTO owned_roles(faction_id,role_id) VALUES(?,?) ON CONFLICT(faction_id) DO UPDATE SET role_id=excluded.role_id", (faction_id,str(role_id)))

    async def _notify(self, bot, job: dict) -> None:
        if await asyncio.to_thread(self._delivered, job["id"]):
            return
        discord_id = job.get("discord_id", "")
        if discord_id:
            href = job.get("href", "")
            if not href.startswith("/") or href.startswith("//"):
                raise RuntimeError("Invalid notification URL")
            view = discord.ui.View()
            view.add_item(discord.ui.Button(label="Открыть на сайте", url=self.client.base_url + href))
            try:
                user = bot.get_user(int(discord_id)) or await bot.fetch_user(int(discord_id))
                await user.send(job.get("title", "Уведомление Warlords"), view=view, allowed_mentions=discord.AllowedMentions.none())
            except (discord.Forbidden, discord.NotFound):
                # A closed DM never invalidates the notification on the website.
                pass
        await asyncio.to_thread(self._mark_delivered, job["id"])

    def _icon(self, path: str) -> bytes:
        if not re.fullmatch(r"/media/faction-banners/[0-9a-f]{64}\.png", path):
            raise RuntimeError("Invalid banner path")
        url = self.client.base_url + path.removesuffix(".png") + "-icon.png"
        with urlopen(url, timeout=10) as response:
            data = response.read(256 * 1024 + 1)
        if len(data) > 256 * 1024 or not data.startswith(b"\x89PNG\r\n\x1a\n"):
            raise RuntimeError("Invalid faction icon")
        return data

    async def _membership(self, guild, job: dict) -> str:
        if not job.get("discord_id"):
            return ""
        user_id = int(job["discord_id"])
        member = guild.get_member(user_id)
        if member is None:
            try:
                member = await guild.fetch_member(user_id)
            except discord.NotFound:
                return ""
        me = guild.me
        if me is None or not me.guild_permissions.manage_roles:
            raise RuntimeError("Bot cannot manage faction roles")
        role = None
        if job.get("faction_id"):
            role_id = job.get("role_id", "")
            local_id = role_id or await asyncio.to_thread(self._owned_role,job["faction_id"])
            role = guild.get_role(int(local_id)) if local_id else None
            if role is None and not role_id:
                role = self._role_cache.get(job["faction_id"])
            role_name = ("Фракция · " + job["faction_name"])[:100]
            if role is not None and not _safe_role(role, me):
                raise RuntimeError("Faction role has unexpected permissions or hierarchy")
            if role is None:
                kwargs = {"name": role_name, "permissions": discord.Permissions.none(), "hoist": False, "mentionable": False, "reason": "Фракция Warlords: публикация на сайте"}
                if "ROLE_ICONS" in guild.features and job.get("banner_url"):
                    kwargs["display_icon"] = await asyncio.to_thread(self._icon, job["banner_url"])
                role = await guild.create_role(**kwargs)
                await asyncio.to_thread(self._record_role,job["faction_id"],role.id)
                if "display_icon" in kwargs:
                    self._icon_versions[role.id] = job["banner_url"]
            else:
                changes = {}
                if role.name != role_name:
                    changes["name"] = role_name
                if "ROLE_ICONS" in guild.features and job.get("banner_url") and self._icon_versions.get(role.id) != job["banner_url"]:
                    changes["display_icon"] = await asyncio.to_thread(self._icon, job["banner_url"])
                if changes:
                    role = await role.edit(**changes, reason="Символика фракции обновлена на сайте") or role
                    if "display_icon" in changes:
                        self._icon_versions[role.id] = job["banner_url"]
            self._role_cache[job["faction_id"]] = role
            if role not in member.roles:
                await member.add_roles(role, reason="Подтверждённое членство на сайте Warlords")
        managed = {str(value) for value in job.get("managed_role_ids", [])}
        remove = [r for r in member.roles if str(r.id) in managed and (role is None or r.id != role.id)]
        if any(not _safe_role(r, me) for r in remove):
            raise RuntimeError("An old faction role is no longer safe to manage")
        if remove:
            await member.remove_roles(*remove, reason="Состав фракций обновлён на сайте Warlords")
        return str(role.id) if role is not None else ""


def _safe_role(role, me) -> bool:
    return not role.managed and role.permissions.value == 0 and role < me.top_role
