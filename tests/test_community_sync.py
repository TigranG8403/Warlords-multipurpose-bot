from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import discord

from modules.warlords_sync.client import WarlordsSiteClient
from modules.warlords_sync.community import CommunityWorker


class Role:
    def __init__(self, role_id, name, *, permissions=0, managed=False, position=1):
        self.id = role_id
        self.name = name
        self.permissions = discord.Permissions(permissions)
        self.managed = managed
        self.position = position
        self.edit = AsyncMock(return_value=None)

    def __lt__(self, other):
        return self.position < other.position


class CommunityTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.client = WarlordsSiteClient("https://warlords.test", "test-token")
        self.worker = CommunityWorker(self.client, 1, Path(self.tmp.name) / "community.sqlite3")
        self.me = SimpleNamespace(guild_permissions=discord.Permissions(manage_roles=True), top_role=Role(99999,"Bot",position=10))
        self.member = SimpleNamespace(roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
        self.roles = []
        self.guild = SimpleNamespace(me=self.me, roles=self.roles, features=[], get_member=lambda _:self.member, fetch_member=AsyncMock(), get_role=lambda value:next((r for r in self.roles if r.id==value),None))
        async def create(**kwargs):
            role = Role(50000 + len(self.roles), kwargs["name"])
            self.roles.append(role)
            return role
        self.guild.create_role = AsyncMock(side_effect=create)

    def job(self, **kwargs):
        return {"id":"job", "kind":"membership", "discord_id":"123456", "faction_id":"faction", "faction_name":"Объединение", "role_id":"", "banner_url":"", "managed_role_ids":[], "lease_token":"lease", **kwargs}

    async def test_creates_role_without_permissions_and_reuses_within_batch(self):
        first = await self.worker._membership(self.guild, self.job())
        second = await self.worker._membership(self.guild, self.job())
        self.assertEqual(first, second)
        self.guild.create_role.assert_awaited_once()
        kwargs = self.guild.create_role.call_args.kwargs
        self.assertEqual(kwargs["permissions"].value, 0)
        self.assertFalse(kwargs["mentionable"])

    async def test_removes_only_known_faction_roles(self):
        faction = Role(55555,"Фракция")
        unrelated = Role(66666,"Модератор",permissions=8)
        self.roles.extend([faction,unrelated])
        self.member.roles = [faction,unrelated]
        await self.worker._membership(self.guild,self.job(faction_id="", managed_role_ids=["55555"]))
        self.member.remove_roles.assert_awaited_once_with(faction,reason="Состав фракций обновлён на сайте Warlords")

    async def test_never_adopts_role_with_permissions(self):
        elevated = Role(55555,"Фракция · Объединение",permissions=8)
        self.roles.append(elevated)
        with self.assertRaisesRegex(RuntimeError,"unexpected permissions"):
            await self.worker._membership(self.guild,self.job(role_id="55555"))
        self.member.add_roles.assert_not_awaited()
        self.guild.create_role.assert_not_awaited()

    async def test_notification_ack_retry_does_not_send_twice(self):
        user = SimpleNamespace(send=AsyncMock())
        bot = SimpleNamespace(get_user=lambda _:user,fetch_user=AsyncMock())
        job = self.job(kind="notification",title="Приглашение",href="/account/faction")
        await self.worker._notify(bot,job)
        await self.worker._notify(bot,job)
        user.send.assert_awaited_once()
        self.assertEqual(user.send.call_args.kwargs["allowed_mentions"].to_dict(),{"parse":[]})

    async def test_closed_dm_is_not_retried_forever(self):
        response=SimpleNamespace(status=403,reason="Forbidden")
        user=SimpleNamespace(send=AsyncMock(side_effect=discord.Forbidden(response,"Closed DMs")))
        bot=SimpleNamespace(get_user=lambda _:user)
        await self.worker._notify(bot,self.job(kind="notification",title="Приглашение",href="/account/faction"))
        self.assertTrue(self.worker._delivered("job"))

    async def test_notification_rejects_external_urls(self):
        with self.assertRaisesRegex(RuntimeError,"Invalid notification URL"):
            await self.worker._notify(SimpleNamespace(),self.job(kind="notification",href="//evil.test"))

    def test_icon_rejects_external_path(self):
        with self.assertRaisesRegex(RuntimeError,"Invalid banner path"):
            self.worker._icon("https://evil.test/track")

    async def test_failed_ack_contains_no_private_answers(self):
        job=self.job(kind="notification",title="Решение по анкете",href="/account/applications")
        bot=SimpleNamespace(get_guild=lambda _:self.guild,get_user=lambda _:SimpleNamespace(send=AsyncMock()))
        with patch.object(self.client,"_request",side_effect=[{"jobs":[job]},{}]) as request:
            await self.worker.run_once(bot)
        self.assertTrue(request.call_args.args[1]["succeeded"])
        self.assertNotIn("answers",str(request.call_args))

    async def test_reports_icon_capability_even_without_jobs(self):
        bot = SimpleNamespace(get_guild=lambda _: self.guild)
        for enabled in (False, True):
            self.guild.features = ["ROLE_ICONS"] if enabled else []
            with patch.object(self.client, "_request", return_value={"jobs": []}) as request:
                await self.worker.run_once(bot)
            self.assertEqual(request.call_args.args[1], {
                "guild_id": "1", "role_icons_available": enabled,
            })

    async def test_disconnected_guild_does_not_report_feature_loss(self):
        bot = SimpleNamespace(get_guild=lambda _: None)
        with patch.object(self.client, "_request", return_value={"jobs": []}) as request:
            await self.worker.run_once(bot)
        self.assertNotIn("role_icons_available", request.call_args.args[1])

    async def test_unlocked_icons_update_existing_role_without_rejoining(self):
        role = Role(55555, "Фракция · Объединение")
        self.roles.append(role)
        self.member.roles = [role]
        job = self.job(role_id="55555", banner_url="/media/faction-banners/" + "a" * 64 + ".png")
        with patch.object(self.worker, "_icon", return_value=b"png") as icon:
            await self.worker._membership(self.guild, job)
            role.edit.assert_not_awaited()
            self.guild.features = ["ROLE_ICONS"]
            await self.worker._membership(self.guild, job)
        icon.assert_called_once()
        role.edit.assert_awaited_once_with(display_icon=b"png", reason="Символика фракции обновлена на сайте")
        self.guild.create_role.assert_not_awaited()
        self.member.add_roles.assert_not_awaited()
