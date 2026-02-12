from __future__ import annotations

from typing import Iterable

from discord.ext import commands

from .module import BotModule


class ModuleBootstrapper:
    def __init__(self, bot: commands.Bot, modules: Iterable[BotModule]):
        self.bot = bot
        self.modules = list(modules)

    def register_all(self) -> None:
        for module in self.modules:
            module.register(self.bot)
            if module.persistent_views:
                for view in module.persistent_views():
                    self.bot.add_view(view)

    async def dispatch_on_ready(self) -> None:
        for module in self.modules:
            if module.on_ready:
                await module.on_ready(self.bot)
