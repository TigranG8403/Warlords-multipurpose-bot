from __future__ import annotations

import json
from dataclasses import dataclass
from urllib.error import HTTPError
from urllib.request import Request, urlopen


@dataclass(frozen=True, slots=True)
class GuildRoleState:
    id: str
    name: str
    position: int
    assignable: bool


@dataclass(frozen=True, slots=True)
class RoleTarget:
    role_id: str
    desired: bool


@dataclass(frozen=True, slots=True)
class RoleJob:
    id: str
    lease_token: str
    discord_user_id: str
    desired: bool
    roles: tuple[RoleTarget, ...] = ()


class WarlordsSiteClient:
    def __init__(self, base_url: str, token: str, *, timeout: float = 10.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def claim(
        self,
        *,
        bot_user_id: int,
        guild_id: int,
        pass_role_id: int,
        pass_role_name: str,
        role_assignable: bool,
        roles: tuple[GuildRoleState, ...] = (),
        error: str = "",
        limit: int = 20,
    ) -> list[RoleJob]:
        payload = self._request(
            "/api/v1/bot/role-jobs/claim",
            {
                "bot_user_id": str(bot_user_id),
                "guild_id": str(guild_id),
                "pass_role_id": str(pass_role_id),
                "pass_role_name": pass_role_name,
                "role_assignable": role_assignable,
                "roles": [
                    {
                        "id": role.id,
                        "name": role.name,
                        "position": role.position,
                        "assignable": role.assignable,
                    }
                    for role in roles
                ],
                "error": error,
                "limit": limit,
            },
        )
        jobs = payload.get("jobs", [])
        if jobs is None:
            jobs = []
        if not isinstance(jobs, list):
            raise RuntimeError("Warlords site returned an invalid role job list")
        parsed: list[RoleJob] = []
        for job in jobs:
            targets = job.get("roles", [])
            if not isinstance(targets, list):
                raise RuntimeError("Warlords site returned an invalid role target list")
            parsed.append(
                RoleJob(
                    id=str(job["id"]),
                    lease_token=str(job["lease_token"]),
                    discord_user_id=str(job["discord_user_id"]),
                    desired=bool(job["desired"]),
                    roles=tuple(
                        RoleTarget(role_id=str(target["role_id"]), desired=bool(target["desired"]))
                        for target in targets
                    ),
                )
            )
        return parsed

    def complete(self, job: RoleJob, *, error: str = "") -> None:
        self._request(
            f"/api/v1/bot/role-jobs/{job.id}/complete",
            {"lease_token": job.lease_token, "succeeded": not error, "error": error},
            allow_empty=True,
        )

    def _request(self, path: str, payload: dict, *, allow_empty: bool = False) -> dict:
        request = Request(
            self.base_url + path,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "WarlordsBot/role-sync",
            },
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                body = response.read()
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")[:500]
            raise RuntimeError(f"Warlords site returned HTTP {error.code}: {body}") from error
        if not body and allow_empty:
            return {}
        try:
            decoded = json.loads(body)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise RuntimeError("Warlords site returned invalid JSON") from error
        if not isinstance(decoded, dict):
            raise RuntimeError("Warlords site returned an invalid response")
        return decoded
