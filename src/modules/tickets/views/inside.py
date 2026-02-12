from __future__ import annotations

import asyncio
import logging
from io import BytesIO

import discord
from discord.ui import View

from ..config import get_msk_time
from ..service import TicketService

logger = logging.getLogger(__name__)


class TicketInsideView(View):
    def __init__(self, service: TicketService):
        super().__init__(timeout=None)
        self.service = service

    @discord.ui.button(
        label="Закрыть обращение",
        style=discord.ButtonStyle.danger,
        emoji="🔐",
        custom_id="close_ticket",
    )
    async def close_ticket_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        embed_close = discord.Embed(
            description="⚠️ Вы уверены, что хотите закрыть обращение?",
            color=self.service.settings.embed_color,
        )
        await interaction.response.send_message(
            embed=embed_close,
            view=ConfirmCloseView(self.service),
            ephemeral=True,
        )

    @discord.ui.button(
        label="Позвать на помощь",
        style=discord.ButtonStyle.primary,
        emoji="🔔",
        custom_id="call_staff",
    )
    async def call_staff_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        if interaction.channel is None:
            await interaction.response.send_message("❌ Канал обращения недоступен.", ephemeral=True)
            return

        embed_call = discord.Embed(
            description=f"🔔 {interaction.user.mention} позвал(-а) на помощь.",
            color=self.service.settings.embed_color,
        )

        ping_message = await interaction.channel.send(f"<@&{self.service.settings.support_role_id}>")
        staff_message = await interaction.channel.send(embed=embed_call)
        await interaction.response.send_message("✅ Помощь вызвана!", ephemeral=True)

        await asyncio.sleep(20)
        try:
            await ping_message.delete()
            await staff_message.delete()
        except discord.Forbidden as error:
            logger.warning("Не удалось удалить сообщения вызова помощи в канале %s: %s", interaction.channel.id, error)
        except discord.HTTPException as error:
            logger.warning("Ошибка Discord API при удалении сообщений вызова помощи в канале %s: %s", interaction.channel.id, error)


class ConfirmCloseView(View):
    def __init__(self, service: TicketService):
        super().__init__(timeout=60)
        self.service = service

    @discord.ui.button(label="Да", style=discord.ButtonStyle.success, custom_id="close_yes")
    async def close_yes_button(self, interaction: discord.Interaction, _button: discord.ui.Button) -> None:
        if not await self.service.can_close_ticket(interaction):
            await interaction.response.send_message("❌ У вас нет прав для закрытия этого обращения.", ephemeral=True)
            return

        channel = interaction.channel
        if channel is None or not isinstance(channel, discord.TextChannel):
            await interaction.response.send_message("❌ Канал обращения недоступен.", ephemeral=True)
            return

        if interaction.guild is None:
            await interaction.response.send_message("❌ Действие доступно только на сервере.", ephemeral=True)
            return

        logs_channel = interaction.guild.get_channel(self.service.settings.log_channel_id)
        ticket_creator = self.service.resolve_ticket_creator(channel)

        if not ticket_creator:
            await interaction.response.send_message("⚠️ Не удалось определить создателя обращения.", ephemeral=True)
            return

        transcript_content = await self.service.create_transcript(channel, ticket_creator)
        transcript_file = self.service.make_transcript_file(transcript_content, channel.name)

        embed_logs = discord.Embed(
            title="Обращения",
            description="",
            timestamp=get_msk_time(),
            color=self.service.settings.embed_color,
        )
        embed_logs.add_field(name="Обращение", value=f"{channel.name}", inline=True)
        embed_logs.add_field(name="Закрыто", value=f"{interaction.user.mention}", inline=False)
        embed_logs.add_field(name="Транскрипт", value="Прикреплен выше", inline=False)
        embed_logs.set_footer(text="МСК (UTC+3)")

        if logs_channel:
            await logs_channel.send(embed=embed_logs, file=transcript_file)

        try:
            transcript_bytes_dm = BytesIO(transcript_content.encode("utf-8"))
            dm_embed = discord.Embed(
                title="Транскрипт обращения",
                description=f"Вот транскрипт Вашего обращения **{channel.name}**, которое было закрыто.",
                color=self.service.settings.embed_color,
                timestamp=get_msk_time(),
            )
            dm_embed.add_field(name="Обращение", value=channel.name, inline=True)
            dm_embed.add_field(name="Закрыто", value=interaction.user.display_name, inline=True)
            dm_embed.set_footer(text="До новых встреч!")

            await ticket_creator.send(
                embed=dm_embed,
                file=discord.File(transcript_bytes_dm, filename=f"transcript_{channel.name}.txt"),
            )
        except discord.Forbidden:
            if logs_channel:
                await logs_channel.send(
                    f"⚠️ Не удалось отправить транскрипт пользователю {ticket_creator.mention} (личные сообщения закрыты)"
                )

        self.service.ticket_creators.pop(channel.id, None)
        await channel.delete()
