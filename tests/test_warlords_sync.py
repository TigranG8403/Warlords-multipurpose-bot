from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

from modules.warlords_sync.client import RoleJob
from modules.warlords_sync.module import _apply_role, _role_assignable


class FakeRole:
    def __init__(self, role_id: int, position: int, *, managed: bool = False) -> None:
        self.id = role_id
        self.position = position
        self.managed = managed

    def __lt__(self, other) -> bool:
        return self.position < other.position

    def __eq__(self, other) -> bool:
        return isinstance(other, FakeRole) and self.id == other.id


class RoleSyncTests(unittest.IsolatedAsyncioTestCase):
    def test_role_must_be_below_bot(self) -> None:
        role = FakeRole(10, 5)
        guild = SimpleNamespace(me=SimpleNamespace(top_role=FakeRole(20, 10)))
        self.assertTrue(_role_assignable(guild, role))
        self.assertFalse(_role_assignable(guild, FakeRole(11, 10)))
        self.assertFalse(_role_assignable(guild, FakeRole(12, 4, managed=True)))

    async def test_apply_role_is_idempotent(self) -> None:
        role = FakeRole(10, 5)
        member = SimpleNamespace(roles=[], add_roles=AsyncMock(), remove_roles=AsyncMock())
        guild = SimpleNamespace(get_member=lambda _user_id: member)
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


if __name__ == "__main__":
    unittest.main()
