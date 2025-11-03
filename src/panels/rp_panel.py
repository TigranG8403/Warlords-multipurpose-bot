import discord
from discord.ui import Button, Select, View
from common.config import id_rp_category, id_staff_role, ticket_creators, rp_color
from common.views import TicketInsideView

class RPMenuView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    # Выбор категорий обращения
    @discord.ui.select(
        placeholder="Выберите тему для создания обращения",
        options=[
            discord.SelectOption(label="Регистрация фракции", value="fraction_reg", description='Для официальной регистрации фракции', emoji='👑'),
            discord.SelectOption(label="Регистрация города", value="city_reg", description='Для регистрации города/поселения', emoji='🏘️'),
            discord.SelectOption(label="RP-обращение", value="rp_appeal", description='Для решения RP-вопросов', emoji='🎭'),
        ],
        custom_id="RP_menu"
    )
    async def select_callback(self, interaction, select):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, id=id_rp_category)
        rol_staff = discord.utils.get(guild.roles, id=id_staff_role)
        
        # Создание обращения
        if select.values[0] == 'fraction_reg':
            channel = await guild.create_text_channel(name=f'👑┃{interaction.user.name}-ticket-reg-fr', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed = discord.Embed(
                title=f'**Регистрация фракции** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Заполните заявку на регистрацию фракции!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=rp_color 
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)

        elif select.values[0] == 'city_reg':
            channel = await guild.create_text_channel(name=f'🏘️┃{interaction.user.name}-ticket-reg-town', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed = discord.Embed(
                title=f'**Регистрация города** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Заполните заявку на регистрацию города!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=rp_color
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed, view=view)
            await interaction.response.send_message(f'> Обращение {channel.mention} создано для решения Вашего вопроса.', ephemeral=True)

        elif select.values[0] == 'rp_appeal':
            channel = await guild.create_text_channel(name=f'🎭┃{interaction.user.name}-ticket-rp', category=category)
            await self.setup_channel_permissions(channel, interaction.user, rol_staff)
            
            ticket_creators[channel.id] = interaction.user
            
            embed = discord.Embed(
                title=f'**RP-обращение** — ¡Здравствуйте, {interaction.user.name}!', 
                description='Напишите Ваше RP-обращение!\n\nЕсли Ваше обращение является неотложным или Вы ожидаете ответа слишком долго, пожалуйста, нажмите `🔔 Позвать на помощь`.', 
                color=rp_color
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            view = TicketInsideView()
            await channel.send(interaction.user.mention, embed=embed, view=view)
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

class CreateRPView(View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Создать обращение", style=discord.ButtonStyle.success, emoji='🎭', custom_id="create_register")
    async def create_RP_button(self, interaction, button):
        view = RPMenuView()
        await interaction.response.send_message(
            content="Чем мы можем Вам помочь?",
            view=view,
            ephemeral=True
        )
