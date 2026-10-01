from __future__ import annotations

import asyncio
import json
import logging
import sqlite3
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .client import WarlordsSiteClient

LOGGER = logging.getLogger(__name__)


class StatisticsOutbox:
    """Acknowledge only after delivery; retries keep the same event UUID."""

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute("pragma journal_mode=WAL")
            db.execute("create table if not exists records (sequence integer primary key, id text unique not null, body text not null)")

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def append(self, kind: str, *, members: int | None = None, at: datetime | None = None) -> str:
        record_id = str(uuid4())
        record = {"id": record_id, "at": (at or datetime.now(timezone.utc)).isoformat(), "kind": kind, "members": members}
        with self.connect() as db:
            db.execute("insert into records(id,body) values (?,?)", (record_id, json.dumps(record)))
        return record_id

    def pending(self, limit: int = 100) -> list[dict]:
        with self.connect() as db:
            return [json.loads(row[0]) for row in db.execute("select body from records order by sequence limit ?", (limit,))]

    def acknowledge(self, records: list[dict]) -> None:
        with self.connect() as db:
            db.executemany("delete from records where id=?", [(r["id"],) for r in records])


class StatisticsWorker:
    def __init__(self, client: WarlordsSiteClient, guild_id: int, outbox: StatisticsOutbox) -> None:
        self.client = client
        self.guild_id = guild_id
        self.outbox = outbox
        self._task: asyncio.Task | None = None
        self._last_sample = 0.0
        self._needs_gap = True

    def register(self, bot) -> None:
        bot.add_listener(self.on_member_join, "on_member_join")
        bot.add_listener(self.on_raw_member_remove, "on_raw_member_remove")
        bot.add_listener(self.on_disconnect, "on_disconnect")

    async def on_member_join(self, member) -> None:
        await self.member_event(member, "join")

    async def on_raw_member_remove(self, payload) -> None:
        if payload.guild_id == self.guild_id and not payload.user.bot:
            await asyncio.to_thread(self.outbox.append, "leave", at=datetime.now(timezone.utc))

    async def member_event(self, member, kind: str) -> None:
        if member.guild.id != self.guild_id or member.bot:
            return
        at = datetime.now(timezone.utc)
        await asyncio.to_thread(self.outbox.append, kind, at=at)

    async def on_disconnect(self) -> None:
        await asyncio.to_thread(self.outbox.append, "gap")

    def start(self, bot) -> None:
        if self._task is None or self._task.done():
            # A fresh process cannot recover events that happened while it was down.
            self._task = asyncio.create_task(self.run(bot), name="warlords-statistics")

    async def sample(self, bot) -> None:
        if not bot.is_ready():
            return
        guild = bot.get_guild(self.guild_id)
        if guild is None or guild.unavailable:
            return
        if not guild.chunked:
            await asyncio.wait_for(guild.chunk(cache=True), timeout=30)
        # No guessing from member_count: it includes bots and may not reflect the cache.
        if not guild.chunked or guild.member_count != len(guild.members):
            LOGGER.warning("Discord statistics: complete member cache unavailable")
            return
        count = sum(not member.bot for member in guild.members)
        await asyncio.to_thread(self.outbox.append, "snapshot", members=count)

    async def flush(self) -> None:
        records = await asyncio.to_thread(self.outbox.pending)
        if not records:
            return
        await asyncio.to_thread(self.client._request, "/api/v1/bot/statistics", {"guild_id": str(self.guild_id), "records": records}, allow_empty=True)
        await asyncio.to_thread(self.outbox.acknowledge, records)

    async def run(self, bot) -> None:
        while not bot.is_closed():
            try:
                if self._needs_gap:
                    await asyncio.to_thread(self.outbox.append, "gap")
                    self._needs_gap = False
                if time.monotonic() - self._last_sample >= 60:
                    await self.sample(bot)
                    self._last_sample = time.monotonic()
                await self.flush()
            except asyncio.CancelledError:
                raise
            except Exception:
                LOGGER.exception("Не удалось отправить статистику Discord; очередь сохранена.")
            await asyncio.sleep(15)
