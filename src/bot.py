import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

from core.bootstrap import ModuleBootstrapper
from modules import get_modules


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Требуется переменная окружения {name}.")
    return value


def _parse_command_prefix() -> str:
    return _require_env("BOT_PREFIX")


def _build_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.guilds = True
    intents.members = True
    intents.messages = True
    intents.message_content = True
    return intents


load_dotenv()

bot = commands.Bot(
    command_prefix=_parse_command_prefix(),
    help_command=None,
    intents=_build_intents(),
)

bootstrapper = ModuleBootstrapper(
    bot=bot,
    modules=get_modules(os.getenv("ENABLED_MODULES")),
)
bootstrapper.register_all()


@bot.event
async def on_ready() -> None:
    await bootstrapper.dispatch_on_ready()
    print("Бот готов к работе ✅")


bot.run(_require_env("DISCORD_TOKEN"))
