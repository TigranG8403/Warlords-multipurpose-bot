from __future__ import annotations

import discord
from discord.ext import commands

from core.module import BotModule

from .config import load_tickets_settings
from .service import TicketService
from .views import (
    ConfirmCloseView,
    CreateFractionView,
    CreateRPView,
    CreateTicketView,
    RPMenuView,
    TicketInsideView,
    TicketMenuView,
)


def build_module() -> BotModule:
    settings = load_tickets_settings()
    service = TicketService(settings)

    def register(bot: commands.Bot) -> None:
        @bot.command(name="ticket")
        @commands.has_permissions(administrator=True)
        async def ticket_command(ctx: commands.Context):
            await ctx.message.delete()
            embed = discord.Embed(
                title="📝 Обращения",
                description=(
                    "Для связи с командой проекта.\n\n"
                    "📌 Выберите тип обращения и создайте тикет\n"
                    "⏰ Постараемся ответить как можно быстрее!"
                ),
                color=settings.main_color,
            )
            embed.set_image(url=settings.panel_image_url)
            await ctx.send(embed=embed, view=CreateTicketView(service, settings))

        @bot.command(name="fraction")
        @commands.has_permissions(administrator=True)
        async def fraction_command(ctx: commands.Context):
            await ctx.message.delete()
            embed = discord.Embed(
                title="📢 Реклама фракций",
                description=(
                    "Для подачи заявки на рекламу Вашей фракции.\n\n"
                    "⏰ Постараемся ответить как можно быстрее!"
                ),
                color=settings.fraction_color,
            )
            embed.set_image(url=settings.panel_image_url)
            await ctx.send(embed=embed, view=CreateFractionView(service, settings))

        @bot.command(name="RP")
        @commands.has_permissions(administrator=True)
        async def rp_command(ctx: commands.Context):
            await ctx.message.delete()
            embed = discord.Embed(
                title="🎭 RP-обращения",
                description=(
                    "Для регистрации города, фракции или решения иных RP-вопросов.\n\n"
                    "📌 Выберите тип обращения и создайте тикет\n"
                    "⏰ Постараемся ответить как можно быстрее!"
                ),
                color=settings.rp_color,
            )
            embed.set_image(url=settings.panel_image_url)
            await ctx.send(embed=embed, view=CreateRPView(service, settings))

    def persistent_views():
        return [
            CreateTicketView(service, settings),
            TicketInsideView(service),
            TicketMenuView(service, settings),
            CreateFractionView(service, settings),
            CreateRPView(service, settings),
            RPMenuView(service, settings),
            ConfirmCloseView(service),
        ]

    return BotModule(
        name="tickets",
        description="Система тикетов.",
        register=register,
        persistent_views=persistent_views,
    )
