from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from modules.warlords_sync.statistics import StatisticsOutbox, StatisticsWorker


class StatisticsTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "stats.sqlite3"
        self.outbox = StatisticsOutbox(self.path)
        self.client = Mock()
        self.worker = StatisticsWorker(self.client, 123, self.outbox)

    async def test_delivery_failure_retains_stable_ids_across_restart(self):
        event = self.outbox.append("join")
        self.client._request.side_effect = RuntimeError("offline")
        with self.assertRaises(RuntimeError):
            await self.worker.flush()
        reopened = StatisticsOutbox(self.path)
        self.assertEqual(reopened.pending()[0]["id"], event)
        self.client._request.side_effect = None
        self.outbox.append("leave")
        await self.worker.flush()
        self.assertEqual(self.outbox.pending(), [])
        records = self.client._request.call_args.args[1]["records"]
        self.assertEqual(records[0]["id"], event)
        self.assertNotIn("user_id", records[0])

    async def test_ack_does_not_delete_new_events(self):
        self.outbox.append("join")
        sent = self.outbox.pending()
        self.outbox.append("leave")
        self.outbox.acknowledge(sent)
        self.assertEqual([r["kind"] for r in self.outbox.pending()], ["leave"])

    async def test_other_guild_and_bots_ignored(self):
        for guild, bot in [(123, True), (999, False)]:
            await self.worker.on_member_join(SimpleNamespace(guild=SimpleNamespace(id=guild), bot=bot))
        self.assertEqual(self.outbox.pending(), [])
        member = SimpleNamespace(guild=SimpleNamespace(id=123), bot=False)
        await self.worker.on_member_join(member)
        await self.worker.on_raw_member_remove(SimpleNamespace(guild_id=123, user=SimpleNamespace(bot=False)))
        await self.worker.on_disconnect()
        self.assertEqual([r["kind"] for r in self.outbox.pending()], ["join", "leave", "gap"])

    async def test_count_excludes_bots_requires_complete_cache(self):
        guild = SimpleNamespace(chunked=True, unavailable=False, members=[SimpleNamespace(bot=False),SimpleNamespace(bot=True)], member_count=2)
        bot = SimpleNamespace(is_ready=lambda:True, get_guild=lambda _:guild)
        await self.worker.sample(bot)
        self.assertEqual(self.outbox.pending()[0]["members"], 1)
        self.outbox.acknowledge(self.outbox.pending())
        guild.member_count = 3
        await self.worker.sample(bot)
        self.assertEqual(self.outbox.pending(), [])
        guild.chunked = False
        guild.chunk = AsyncMock()
        await self.worker.sample(bot)
        guild.chunk.assert_awaited_once_with(cache=True)
        self.assertEqual(self.outbox.pending(), [])
