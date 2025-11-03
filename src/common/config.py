import os
import datetime
from dotenv import load_dotenv
from io import BytesIO

load_dotenv()

# ID из .env
id_ticket_category = int(os.getenv('TICKET_CATEGORY_ID'))
id_fraction_category = int(os.getenv('FRACTION_CATEGORY_ID'))
id_rp_category = int(os.getenv('RP_CATEGORY_ID'))
id_channel_ticket_logs = int(os.getenv('LOG_CHANNEL_ID'))
id_staff_role = int(os.getenv('SUPPORT_ROLE_ID'))

# Цвета для категорий обращений
embed_color = 0xfcd005
main_color = 0xfcd005
rp_color = 0x27ae60
fraction_color = 0x3498db

# Картинка для категорий обращений
img = 'https://media.discordapp.net/attachments/1077268549371965493/1426205017223856320/img.png?ex=68ea606d&is=68e90eed&hm=740c9377ee444b8c147ad7df00715be59fa7fbc8007aac41fc41d6c754e7a920&=&format=webp&quality=lossless'

# Хранение создателей обращений
ticket_creators = {}

MSK_TIMEZONE = datetime.timezone(datetime.timedelta(hours=3))

def get_msk_time():
    return datetime.datetime.now(MSK_TIMEZONE)

def convert_to_msk(utc_time):
    return utc_time.replace(tzinfo=datetime.timezone.utc).astimezone(MSK_TIMEZONE)

# Функция для создания транскрипта
async def create_transcript(channel, ticket_creator):
    messages = []
    
    # Получение всех сообщений из канала
    async for message in channel.history(limit=None, oldest_first=True):
        msk_time = convert_to_msk(message.created_at)
        time_str = msk_time.strftime("%Y-%m-%d %H:%M:%S МСК")
        
        # Обработка вложений
        attachments = ""
        if message.attachments:
            attachments = " [Вложения: " + ", ".join([att.url for att in message.attachments]) + "]"
        
        message_content = message.clean_content if message.clean_content else "[Сообщение без текста]"

        message_content = message_content.encode('utf-8', errors='replace').decode('utf-8')
        
        author_name = message.author.display_name.encode('utf-8', errors='replace').decode('utf-8')
        
        messages.append(f"[{time_str}] {author_name}: {message_content}{attachments}")
    
    # Конечное содержание файла
    current_time = get_msk_time()
    channel_created_msk = convert_to_msk(channel.created_at)
    
    transcript_content = '\ufeff'
    transcript_content += f"Транскрипт обращения: {channel.name}\n"  
    transcript_content += f"Создатель: {ticket_creator.display_name} ({ticket_creator.id})\n"
    transcript_content += f"Канал: {channel.name} ({channel.id})\n"
    transcript_content += f"Дата создания: {channel_created_msk.strftime('%Y-%m-%d %H:%M:%S МСК')}\n"
    transcript_content += f"Дата закрытия: {current_time.strftime('%Y-%m-%d %H:%M:%S МСК')}\n"
    transcript_content += "=" * 50 + "\n\n"
    transcript_content += "\n".join(messages)
    
    return transcript_content
