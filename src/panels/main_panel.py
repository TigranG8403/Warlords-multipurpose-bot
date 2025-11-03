import discord
from discord.ui import Button, Select, View
from common.config import id_ticket_category, id_staff_role, ticket_creators, embed_color, main_color
from common.views import TicketInsideView

class TicketMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    # Выбор категорий обращения
    @discord.ui.select(
        placeholder="Выберите тему для создания обращения",
        options=[
            discord.SelectOption(label="Проходка", value="pass", description='Для всех вопросов по проходкам', emoji='🎫'),
            discord.SelectOption(label="Жалоба на игрока", value="report", description='Для подачи жалобы в связи с нарушением правил проекта', emoji='📕'),
            discord.SelectOption(label="Обжалование решения администрации", value="appeal", description='Для апеллирования решений администрации проекта', emoji='⚖️'),
            discord.SelectOption(label="Баги, недочеты, тех. проблемы", value="bugs", description='Для уведомления администрации проекта о технических проблемах', emoji='⚙️'),
            discord.SelectOption(label="Другое", value="other", description='Для решения иных вопросов', emoji='🪇'),
        ],
        custom_id="ticket_menu"
    )
    async def select_callback(self, interaction, select):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=id_ticket_category)
        rol_staff = discord.utils.get(guild.roles, id=id_staff_role)
        
        # Создание обращения
        if select.values[0] == 'pass':
            channel = await guild.create_text_channel(name=f'🎫┃{interaction.user.name}-ticket-pass', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            # Сообщение в канале
            embed_pass = discord.Embed(
                title=f'**Проходка** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Задавайте Ваш вопрос!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=main_color
            )
            embed_pass.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed_pass, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)

        elif select.values[0] == 'report':
            channel = await guild.create_text_channel(name=f'📕┃{interaction.user.name}-ticket-report', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed_report = discord.Embed(
                title=f'**Жалоба на игрока** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Отправьте Вашу жалобу на игрока проекта!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=main_color
            )
            embed_report.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed_report, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)
        
        elif select.values[0] == 'appeal':
            channel = await guild.create_text_channel(name=f'⚖️┃{interaction.user.name}-ticket-appeal', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed_appeal = discord.Embed(
                title=f'**Обжалование решения администрации** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Опишите Вашу претензию!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=main_color
            )
            embed_appeal.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed_appeal, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)

        elif select.values[0] == 'bugs':
            channel = await guild.create_text_channel(name=f'⚙️┃{interaction.user.name}-ticket-bugs', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed_bugs = discord.Embed(
                title=f'**Баги, недочеты, тех. проблемы** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Сообщите о технической проблеме!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=main_color
            )
            embed_bugs.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed_bugs, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)

        elif select.values[0] == 'other':
            channel = await guild.create_text_channel(name=f'🪇┃{interaction.user.name}-ticket-other', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed_other = discord.Embed(
                title=f'**Другое** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Задайте свой вопрос!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=main_color
            )
            embed_other.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed_other, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)
    
    async def setup_channel_permissions(self, channel, user, staff_role):
        await channel.set_permissions(channel.guild.default_role,
                        send_messages=False,
                        read_messages=False)
        await channel.set_permissions(user, 
                            send_messages=True,
                            read_messages=True,
                            add_reactions=True,
                            embed_links=True,
                            attach_files=True,
                            read_message_history=True,
                            external_emojis=True)
        await channel.set_permissions(staff_role,
                            send_messages=True,
                            read_messages=True,
                            add_reactions=True,
                            embed_links=True,
                            attach_files=True,
                            read_message_history=True,
                            external_emojis=True,
                            manage_messages=True)
        
class CreateTicketView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Создать обращение", style=discord.ButtonStyle.success, emoji='📝', custom_id="create_ticket")
    async def create_ticket_button(self, interaction, button):
        view = TicketMenuView()
        await interaction.response.send_message(
            content="Чем мы можем Вам помочь?",
            view=view,
            ephemeral=True
        )
