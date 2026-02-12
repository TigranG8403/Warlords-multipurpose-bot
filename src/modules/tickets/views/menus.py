from __future__ import annotations

import discord
from discord.ui import View

from ..config import TicketsSettings
from ..service import TicketService
from .channel_factory import create_ticket_channel


class TicketMenuView(View):
    def __init__(self, service: TicketService, settings: TicketsSettings):
        super().__init__(timeout=None)
        self.service = service
        self.settings = settings

    @discord.ui.select(
        placeholder="Выберите тему для создания обращения",
        options=[
            discord.SelectOption(label="Проходка", value="pass", description="Для всех вопросов по проходкам", emoji="🎫"),
            discord.SelectOption(
                label="Жалоба на игрока",
                value="report",
                description="Для подачи жалобы в связи с нарушением правил проекта",
                emoji="📕",
            ),
            discord.SelectOption(
                label="Обжалование решения администрации",
                value="appeal",
                description="Для апеллирования решений администрации проекта",
                emoji="⚖️",
            ),
            discord.SelectOption(
                label="Баги, недочеты, тех. проблемы",
                value="bugs",
                description="Для уведомления администрации проекта о технических проблемах",
                emoji="⚙️",
            ),
            discord.SelectOption(label="Другое", value="other", description="Для решения иных вопросов", emoji="🪇"),
        ],
        custom_id="ticket_menu",
    )
    async def select_callback(self, interaction, select):
        mapping = {
            "pass": ("🎫┃{name}-ticket-pass", "**Проходка**", "Задавайте Ваш вопрос!", self.settings.main_color),
            "report": (
                "📕┃{name}-ticket-report",
                "**Жалоба на игрока**",
                "Отправьте Вашу жалобу на игрока проекта!",
                self.settings.main_color,
            ),
            "appeal": (
                "⚖️┃{name}-ticket-appeal",
                "**Обжалование решения администрации**",
                "Опишите Вашу претензию!",
                self.settings.main_color,
            ),
            "bugs": (
                "⚙️┃{name}-ticket-bugs",
                "**Баги, недочеты, тех. проблемы**",
                "Сообщите о технической проблеме!",
                self.settings.main_color,
            ),
            "other": ("🪇┃{name}-ticket-other", "**Другое**", "Задайте свой вопрос!", self.settings.main_color),
        }
        pattern, title, desc, color = mapping[select.values[0]]
        await create_ticket_channel(
            interaction=interaction,
            service=self.service,
            category_id=self.settings.ticket_category_id,
            channel_name=pattern.format(name=interaction.user.name),
            embed_title=title,
            embed_description=desc,
            color=color,
        )


class CreateTicketView(View):
    def __init__(self, service: TicketService, settings: TicketsSettings):
        super().__init__(timeout=None)
        self.service = service
        self.settings = settings

    @discord.ui.button(label="Создать обращение", style=discord.ButtonStyle.success, emoji="📝", custom_id="create_ticket")
    async def create_ticket_button(self, interaction, _button):
        await interaction.response.send_message(
            content="Чем мы можем Вам помочь?",
            view=TicketMenuView(self.service, self.settings),
            ephemeral=True,
        )


class CreateFractionView(View):
    def __init__(self, service: TicketService, settings: TicketsSettings):
        super().__init__(timeout=None)
        self.service = service
        self.settings = settings

    @discord.ui.button(label="Создать обращение", style=discord.ButtonStyle.success, emoji="📢", custom_id="create_fraction")
    async def create_fraction_button(self, interaction, _button):
        await create_ticket_channel(
            interaction=interaction,
            service=self.service,
            category_id=self.settings.fraction_category_id,
            channel_name=f"📢┃{interaction.user.name}-ticket-ad-fr",
            embed_title="**Реклама фракций**",
            embed_description="Опишите Вашу фракцию для рекламы!",
            color=self.settings.fraction_color,
        )


class RPMenuView(View):
    def __init__(self, service: TicketService, settings: TicketsSettings):
        super().__init__(timeout=None)
        self.service = service
        self.settings = settings

    @discord.ui.select(
        placeholder="Выберите тему для создания обращения",
        options=[
            discord.SelectOption(
                label="Регистрация фракции",
                value="fraction_reg",
                description="Для официальной регистрации фракции",
                emoji="👑",
            ),
            discord.SelectOption(
                label="Регистрация города",
                value="city_reg",
                description="Для регистрации города/поселения",
                emoji="🏘️",
            ),
            discord.SelectOption(
                label="RP-обращение",
                value="rp_appeal",
                description="Для решения RP-вопросов",
                emoji="🎭",
            ),
        ],
        custom_id="RP_menu",
    )
    async def select_callback(self, interaction, select):
        mapping = {
            "fraction_reg": ("👑┃{name}-ticket-reg-fr", "**Регистрация фракции**", "Заполните заявку на регистрацию фракции!"),
            "city_reg": ("🏘️┃{name}-ticket-reg-town", "**Регистрация города**", "Заполните заявку на регистрацию города!"),
            "rp_appeal": ("🎭┃{name}-ticket-rp", "**RP-обращение**", "Напишите Ваше RP-обращение!"),
        }
        pattern, title, desc = mapping[select.values[0]]
        await create_ticket_channel(
            interaction=interaction,
            service=self.service,
            category_id=self.settings.rp_category_id,
            channel_name=pattern.format(name=interaction.user.name),
            embed_title=title,
            embed_description=desc,
            color=self.settings.rp_color,
        )


class CreateRPView(View):
    def __init__(self, service: TicketService, settings: TicketsSettings):
        super().__init__(timeout=None)
        self.service = service
        self.settings = settings

    @discord.ui.button(label="Создать обращение", style=discord.ButtonStyle.success, emoji="🎭", custom_id="create_register")
    async def create_rp_button(self, interaction, _button):
        await interaction.response.send_message(
            content="Чем мы можем Вам помочь?",
            view=RPMenuView(self.service, self.settings),
            ephemeral=True,
        )
