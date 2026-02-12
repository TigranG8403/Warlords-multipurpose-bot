from __future__ import annotations

from io import BytesIO

import discord

from .config import TicketsSettings, convert_to_msk, get_msk_time


class TicketService:
    def __init__(self, settings: TicketsSettings):
        self.settings = settings
        self.ticket_creators: dict[int, discord.Member] = {}

    async def setup_channel_permissions(
        self,
        channel: discord.TextChannel,
        user: discord.Member,
        staff_role: discord.Role,
    ) -> None:
        await channel.set_permissions(channel.guild.default_role, send_messages=False, read_messages=False)
        await channel.set_permissions(
            user,
            send_messages=True,
            read_messages=True,
            add_reactions=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            external_emojis=True,
        )
        await channel.set_permissions(
            staff_role,
            send_messages=True,
            read_messages=True,
            add_reactions=True,
            embed_links=True,
            attach_files=True,
            read_message_history=True,
            external_emojis=True,
            manage_messages=True,
        )

    async def create_transcript(self, channel: discord.TextChannel, ticket_creator: discord.Member) -> str:
        messages: list[str] = []
        async for message in channel.history(limit=None, oldest_first=True):
            msk_time = convert_to_msk(message.created_at)
            time_str = msk_time.strftime("%Y-%m-%d %H:%M:%S МСК")

            attachments = ""
            if message.attachments:
                attachments = " [Вложения: " + ", ".join([att.url for att in message.attachments]) + "]"

            message_content = message.clean_content if message.clean_content else "[Сообщение без текста]"
            message_content = message_content.encode("utf-8", errors="replace").decode("utf-8")
            author_name = message.author.display_name.encode("utf-8", errors="replace").decode("utf-8")
            messages.append(f"[{time_str}] {author_name}: {message_content}{attachments}")

        current_time = get_msk_time()
        channel_created_msk = convert_to_msk(channel.created_at)

        transcript_content = "\ufeff"
        transcript_content += f"Транскрипт обращения: {channel.name}\n"
        transcript_content += f"Создатель: {ticket_creator.display_name} ({ticket_creator.id})\n"
        transcript_content += f"Канал: {channel.name} ({channel.id})\n"
        transcript_content += f"Дата создания: {channel_created_msk.strftime('%Y-%m-%d %H:%M:%S МСК')}\n"
        transcript_content += f"Дата закрытия: {current_time.strftime('%Y-%m-%d %H:%M:%S МСК')}\n"
        transcript_content += "=" * 50 + "\n\n"
        transcript_content += "\n".join(messages)

        return transcript_content

    async def can_close_ticket(self, interaction: discord.Interaction) -> bool:
        member_roles = [role.id for role in interaction.user.roles]
        if self.settings.support_role_id in member_roles:
            return True
        return interaction.channel.permissions_for(interaction.user).manage_channels

    def resolve_ticket_creator(self, channel: discord.TextChannel) -> discord.Member | None:
        ticket_creator = self.ticket_creators.get(channel.id)
        if ticket_creator:
            return ticket_creator

        for member in channel.members:
            if not member.bot and channel.permissions_for(member).read_messages:
                return member
        return None

    def make_transcript_file(self, transcript_content: str, channel_name: str) -> discord.File:
        transcript_bytes = BytesIO(transcript_content.encode("utf-8"))
        current_time = get_msk_time()
        return discord.File(
            transcript_bytes,
            filename=f"transcript_{channel_name}_{current_time.strftime('%Y%m%d_%H%M%S')}.txt",
        )
