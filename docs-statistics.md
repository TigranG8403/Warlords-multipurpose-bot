# Discord project statistics

The existing `warlords_sync` module now also sends anonymous aggregate telemetry
to the site's `/api/v1/bot/statistics` endpoint. It uses `WARLORDS_SITE_URL`,
`WARLORDS_SITE_BOT_TOKEN` and `APP_COMMAND_GUILD_ID`; no extra bot privileges,
commands, role assignments or credentials are needed. Members intent is already
enabled in `bot.py`.

Human joins, raw member removals and disconnect markers are retained in SQLite.
Once a minute, a complete guild cache produces a human member count. Snapshots
are skipped if the cache is incomplete or the bot is not ready. No user IDs,
names, message contents or other-guild data are sent.

`data/statistics.sqlite3` is a durable outbox. Production's existing data symlink
keeps it in `/var/lib/warlords-bot/data` across releases. Delivery retries reuse
UUIDs; successful batches are acknowledged by ID so concurrently queued records
are preserved. SQLite connections explicitly close after each transaction.

Gateway outages can miss events; the site marks missing/incomplete coverage
instead of reconstructing joins/leaves from a membership difference. HTTP
outages do not discard queued events. Event timestamps older than 366 days are
not accepted by the site. Deploy the site endpoint before this bot version.

Run `python -m unittest discover -s tests -q` and `python -m compileall -q src tests`.
If delivery fails, the bot logs the error and keeps the queue, without blocking
normal role synchronization. Rollback uses the existing deployment's previous
release and leaves this additional SQLite file intact.
