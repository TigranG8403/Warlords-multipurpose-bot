# Website community integration

The existing `warlords_sync` module now also delivers website notifications
and synchronizes permanent faction membership. It uses the existing site
URL, bot token and guild ID; no new credential or administrator permission
is required.

The website is authoritative. The worker claims leased jobs from
`/api/v1/bot/community/claim` and acknowledges them through
`/api/v1/bot/community/{id}/complete`. Membership jobs contain the current
faction, never an instruction to blindly replay an old join event.

Faction roles are created with no permissions and no mass mentions. Only
role IDs managed by this integration are removed. Roles with unexpected
permissions/hierarchy are not altered. Name matches alone never establish
ownership of a role. Icons use the website's padded square PNG and require
the guild's ROLE_ICONS feature.

`data/community.sqlite3` stores created-role ownership and notification
delivery IDs. Keep it with the other persistent bot data across deployments.
Closed DMs are treated as a delivery limitation, not an error in website
membership; notifications remain readable on the website. Admission answers
and moderation reasons are not sent to Discord.

Tests: `PYTHONPATH=src python -m unittest discover -s tests -v`.
