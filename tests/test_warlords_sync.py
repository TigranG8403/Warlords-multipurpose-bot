from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from modules.warlords_sync.client import GuildRoleState, RoleJob, RoleTarget, WarlordsSiteClient
from modules.warlords_sync.module import _apply_role, _apply_roles, _role_assignable


class FakeRole:
    def __init__(self, role_id: int, position: int, *, managed: bool = False, name: str = "Role") -> None:
        self.id = role_id
        self.position = position
        self.managed = managed
        self.name = name

    def __lt__(self, other) -> bool:
        return self.position < other.position

    def __eq__(self, other) -> bool:
        return isinstance(other, FakeRole) and self.id == other.id


class RoleSyncTests(unittest.IsolatedAsyncioTestCase):
    def test_client_sends_catalog_and_parses_role_targets(self) -> None:
        client = WarlordsSiteClient("https://warlords.test", "secret")
        response = {
            "jobs": [
                {
                    "id": "job",
                    "lease_token": "lease",
                    "discord_user_id": "123",
                    "desired": True,
                    "roles": [
                        {"role_id": "10", "desired": True},
                        {"role_id": "11", "desired": False},
                    ],
                }
            ]
        }
        with patch.object(client, "_request", return_value=response) as request:
            jobs = client.claim(
                bot_user_id=1,
                guild_id=2,
                pass_role_id=10,
                pass_role_name="Проходка",
                role_assignable=True,
                roles=(GuildRoleState(id="11", name="Команда", position=5, assignable=True),),
            )

        payload = request.call_args.args[1]
        self.assertEqual(payload["roles"], [{"id": "11", "name": "Команда", "position": 5, "assignable": True}])
        self.assertEqual(jobs[0].roles[1], RoleTarget(role_id="11", desired=False))

    def test_role_must_be_below_bot(self) -> None:
        role = FakeRole(10, 5)
        guild = SimpleNamespace(me=SimpleNamespace(top_role=FakeRole(20, 10)))
        self.assertTrue(_role_assignable(guild, role))
        self.assertFalse(_role_assignable(guild, FakeRole(11, 10)))
        self.assertFalse(_role_assignable(guild, FakeRole(12, 4, managed=True)))

    async def test_apply_role_is_idempotent(self) -> None:
        role = FakeRole(10, 5)
        member = SimpleNamespace(roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
        guild = SimpleNamespace(
            me=SimpleNamespace(top_role=FakeRole(20, 10)),
            get_member=lambda _user_id: member,
            get_role=lambda role_id: role if role_id == role.id else None,
        )
        job = RoleJob(id="job", lease_token="lease", discord_user_id="123", desired=True)

        await _apply_role(guild, role, job)
        member.add_roles.assert_awaited_once()
        member.add_roles.reset_mock()
        member.roles = [role]
        await _apply_role(guild, role, job)
        member.add_roles.assert_not_awaited()

        remove = RoleJob(id="job", lease_token="lease", discord_user_id="123", desired=False)
        await _apply_role(guild, role, remove)
        member.remove_roles.assert_awaited_once()

    async def test_apply_multiple_roles_in_one_job(self) -> None:
        pass_role = FakeRole(10, 5)
        staff_role = FakeRole(11, 6)
        old_role = FakeRole(12, 4)
        member = SimpleNamespace(roles=[old_role], add_roles=AsyncMock(), remove_roles=AsyncMock())
        roles = {role.id: role for role in (pass_role, staff_role, old_role)}
        guild = SimpleNamespace(
            me=SimpleNamespace(top_role=FakeRole(20, 10)),
            get_member=lambda _user_id: member,
            get_role=lambda role_id: roles.get(role_id),
        )
        job = RoleJob(
            id="job",
            lease_token="lease",
            discord_user_id="123",
            desired=True,
            roles=(
                RoleTarget(role_id="10", desired=True),
                RoleTarget(role_id="11", desired=True),
                RoleTarget(role_id="12", desired=False),
                RoleTarget(role_id="404", desired=False),
            ),
        )

        await _apply_roles(guild, pass_role, job)

        member.add_roles.assert_awaited_once_with(pass_role, staff_role, reason="Синхронизация ролей Warlords")
        member.remove_roles.assert_awaited_once_with(old_role, reason="Синхронизация ролей Warlords")

    async def test_missing_identity_is_valid_when_all_roles_are_removed(self) -> None:
        pass_role = FakeRole(10, 5)
        guild = SimpleNamespace()
        job = RoleJob(
            id="job",
            lease_token="lease",
            discord_user_id="",
            desired=False,
            roles=(RoleTarget(role_id="10", desired=False),),
        )

        await _apply_roles(guild, pass_role, job)


if __name__ == "__main__":
    unittest.main()
