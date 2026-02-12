from __future__ import annotations

import logging

import discord

from ..service import TicketService

logger = logging.getLogger(__name__)


async def create_ticket_channel(
    interaction: discord.Interaction,
    service: TicketService,
    category_id: int,
    channel_name: str,
    embed_title: str,
    embed_description: str,
    color: int,
) -> None:
    guild = interaction.guild
    if guild is None:
        logger.error("Не удалось создать обращение: взаимодействие вне контекста сервера (user_id=%s)", interaction.user.id)
        await interaction.response.send_message(
            "❌ Невозможно создать обращение вне сервера.",
            ephemeral=True,
        )
        return

    category = discord.utils.get(guild.categories, id=category_id)
    if category is None:
        logger.error("Не удалось создать обращение: категория %s не найдена на сервере %s", category_id, guild.id)
        await interaction.response.send_message(
            "❌ Категория для обращений не настроена. Сообщите администрации.",
            ephemeral=True,
        )
        return

    staff_role = discord.utils.get(guild.roles, id=service.settings.support_role_id)
    if staff_role is None:
        logger.error("Не удалось создать обращение: роль поддержки %s не найдена на сервере %s", service.settings.support_role_id, guild.id)
        await interaction.response.send_message(
            "❌ Роль поддержки не найдена. Сообщите администрации.",
            ephemeral=True,
        )
        return

    if not isinstance(interaction.user, discord.Member):
        logger.error("Не удалось создать обращение: пользователь взаимодействия не является участником сервера (user_id=%s)", interaction.user.id)
        await interaction.response.send_message(
            "❌ Не удалось определить участника сервера.",
            ephemeral=True,
        )
        return

    channel = await guild.create_text_channel(name=channel_name, category=category)
    await service.setup_channel_permissions(channel, interaction.user, staff_role)
    service.ticket_creators[channel.id] = interaction.user

    embed = discord.Embed(
        title=f"{embed_title} — Здравствуйте, {interaction.user.name}!",
        description=(
            f"{embed_description}\n\n"
            "Если Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, "
            "пожалуйста, нажмите `🔔 Позвать на помощь`."
        ),
        color=color,
    )
    embed.set_thumbnail(url=interaction.user.display_avatar.url)

    from .inside import TicketInsideView

    await channel.send(interaction.user.mention, embed=embed, view=TicketInsideView(service))
    await interaction.response.send_message(f"> Обращение {channel.mention} создано для решения Вашего вопроса.", ephemeral=True)
