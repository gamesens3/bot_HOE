import os
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters, CallbackQueryHandler
import random
from datetime import datetime
import requests
from bs4 import BeautifulSoup
import asyncio

# Загружаем переменные окружения
load_dotenv()

# Получаем токен бота из переменных окружения
TOKEN = os.getenv('BOT_TOKEN')

# Словарь для хранения настроек пользователей
user_settings = {}

# Словарь для хранения последней показанной шутки для каждого пользователя
last_jokes = {}

# Словарь для хранения статистики активности пользователей
user_activity = {}

# Словарь для хранения данных о регистрации пользователей
user_registration = {}

# Словарь для хранения расширенной статистики пользователей
user_extended_stats = {}

# Словарь для хранения последней отправленной картинки Unsplash для каждого пользователя
last_unsplash_url = {}

# Словарь для хранения последнего отправленного мема для каждого пользователя
last_meme_url = {}

# Словарь для хранения всех отправленных мемов для каждого пользователя
sent_memes = {}

# Список шуток про картавых
kartaviy_jokes = [
    "Можно уже вовгемя выходить, ебаная 4 гуппа",
    "Если не можешь ногмально сфогмиговать мысль - не говоги, хуесос",
    "Жек, дай покугить",
    "Блять, мы можем скидываться не по гублю уже???",
    "Ты ебанутая, аничототфактчто я твой гот ебал?",
    "Здагова чегти!",
    "Блять, мы опять постоять вышли?",
    "Ебаный начфак, я его гот ебал",
    "Завали ебало даунннн",
    "Да не токсик я блятььь!"
]

# Глобальный список мемов с imgflip
imgflip_memes = []
imgflip_loaded = False

async def get_random_pinterest_image():
    """Получить случайную картинку с Pinterest по случайному запросу"""
    # Список случайных запросов для разнообразия
    queries = [
        'funny', 'cat', 'dog', 'nature', 'art', 'meme', 'car', 'anime', 'travel', 'food', 'abstract', 'wallpaper'
    ]
    import random
    query = random.choice(queries)
    url = f'https://www.pinterest.com/search/pins/?q={query}'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, 'html.parser')
    images = [img['src'] for img in soup.find_all('img', src=True) if '236x' in img['src']]
    if images:
        return random.choice(images)
    return None

async def send_random_picture(update, context):
    import asyncio
    msg = await update.message.reply_text('🔄 Генерирую случайную картинку...')
    url = f'https://picsum.photos/1920/1080?random={random.randint(1, 1000000)}'
    try:
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=url)
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f'Ошибка при отправке картинки: {e}')
    await asyncio.sleep(1)

async def send_random_meme(update, context):
    import asyncio
    import random
    global imgflip_memes, imgflip_loaded
    user_id = update.effective_user.id
    sent = sent_memes.setdefault(user_id, set())
    msg = await update.message.reply_text('🌀 Ищу мем...')
    try:
        # Загружаем мемы с imgflip только один раз
        if not imgflip_loaded or not imgflip_memes:
            response = requests.get('https://api.imgflip.com/get_memes', timeout=10)
            data = response.json()
            if data.get('success'):
                imgflip_memes = data['data']['memes']
                imgflip_loaded = True
        # Фильтруем только неотправленные мемы
        available_memes = [m for m in imgflip_memes if m['url'] not in sent]
        if not available_memes:
            await msg.edit_text('Все мемы из пула уже были отправлены!')
            return
        meme = random.choice(available_memes)
        sent.add(meme['url'])
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=meme['url'], caption=meme['name'])
        await msg.delete()
    except Exception as e:
        await msg.edit_text(f'Ошибка при отправке мема: {e}')
    await asyncio.sleep(1)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start и кнопки 'Ехала!'"""
    user = update.effective_user
    user_id = user.id
    username = user.username
    now = datetime.now()
    chat = update.message.chat if update.message else None
    chat_type = chat.type if chat else None
    
    # Инициализируем настройки для нового пользователя
    if user_id not in user_settings:
        user_settings[user_id] = {
            'min': 1,
            'max': 100,
            'exclude': []
        }
    
    # Сохраняем или обновляем данные о регистрации пользователя
    user_registration[user_id] = {
        'registration_date': user_registration[user_id]['registration_date'] if user_id in user_registration else now,
        'username': username,
        'first_name': user.first_name,
        'last_name': user.last_name,
        'language_code': user.language_code,
        'is_bot': user.is_bot,
        'is_premium': getattr(user, 'is_premium', False),
        'last_message_date': now,
        'chat_type': chat_type,
        'last_command': '/start',
    }
    
    # Обновляем расширенную статистику
    ext = user_extended_stats.setdefault(user_id, {
        'messages_count': 0,
        'unique_days': set(),
        'last_streak_day': None,
        'streak': 0,
        'commands_usage': {},
        'last_inline_button': None,
        'last_message': None,
    })
    ext['messages_count'] += 1
    ext['unique_days'].add(now.date())
    # streak
    if ext['last_streak_day'] is None or (now.date() - ext['last_streak_day']).days == 1:
        ext['streak'] += 1
    elif (now.date() - ext['last_streak_day']).days > 1:
        ext['streak'] = 1
    ext['last_streak_day'] = now.date()
    ext['last_message'] = update.message.text if update.message else None
    ext['commands_usage']['/start'] = ext['commands_usage'].get('/start', 0) + 1
    
    # Создаем клавиатуру с кнопками
    keyboard = [
        [KeyboardButton("Анализировать информацию"), KeyboardButton("Ехала!")],
        [KeyboardButton("🎭 Попуск Михалыча"), KeyboardButton("🎲 Случайное число")],
        [KeyboardButton("Случайная картинка"), KeyboardButton("Случайный мем")]
    ]
    
    # Добавляем специальную кнопку для администратора
    if username == "sobsna_eto_moi_tg":
        keyboard.append([KeyboardButton("📊 Расширенная статистика")])
    
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    # Специальное приветствие для конкретного пользователя
    if username == "Danila_a_a_a":
        welcome_message = f'Пгиветствуем тея кагтавый бгат! Кгуто отдохнул? С каким настгоением пожаловал к нам?'
    else:
        welcome_message = f'Салам алейкум, Бродяга! С чем пожаловал?'
    
    await update.message.reply_text(welcome_message, reply_markup=reply_markup)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    # Создаем инлайн-кнопки
    keyboard = [
        [
            InlineKeyboardButton("Команды", callback_data='commands'),
            InlineKeyboardButton("Информация", callback_data='info')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    help_text = """
Доступные команды:
/start - Начать работу с ботом
/help - Показать это сообщение
/info - Информация о боте
/mihalich - Получить шутку про картавых или черный юмор
/random - Настройка генератора случайных чисел

Также вы можете использовать кнопки на клавиатуре!
    """
    await update.message.reply_text(help_text, reply_markup=reply_markup)

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /info"""
    # Создаем инлайн-кнопки
    keyboard = [
        [
            InlineKeyboardButton("GitHub", url="https://github.com"),
            InlineKeyboardButton("Написать разработчику", url="https://t.me/username")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    info_text = """
🤖 Информация о боте:
Версия: 1.0
Разработчик: Ваше имя
Описание: Простой Telegram бот на Python с кнопками
    """
    await update.message.reply_text(info_text, reply_markup=reply_markup)

async def mihalich(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /mihalich и кнопки Попуск Михалыча"""
    user_id = update.effective_user.id
    
    # Получаем доступные шутки (исключая последнюю показанную)
    available_jokes = [joke for joke in kartaviy_jokes if joke != last_jokes.get(user_id)]
    
    # Если все шутки были показаны, сбрасываем историю
    if not available_jokes:
        available_jokes = kartaviy_jokes.copy()
        last_jokes[user_id] = None
    
    # Выбираем случайную шутку из доступных
    joke = random.choice(available_jokes)
    last_jokes[user_id] = joke
    
    # Создаем инлайн-кнопки
    keyboard = [
        [
            InlineKeyboardButton("Ещё шутка", callback_data='more_joke'),
            InlineKeyboardButton("Спасибо", callback_data='cancel')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(f"😄 {joke}", reply_markup=reply_markup)

async def random_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /random и кнопки случайного числа"""
    user_id = update.effective_user.id
    
    # Инициализируем настройки для пользователя, если их нет
    if user_id not in user_settings:
        user_settings[user_id] = {
            'min': 1,
            'max': 100,
            'exclude': []
        }
    
    # Создаем клавиатуру для настройки диапазона
    keyboard = [
        [
            InlineKeyboardButton("Изменить диапазон", callback_data='change_range'),
            InlineKeyboardButton("Исключить числа", callback_data='exclude_numbers')
        ],
        [
            InlineKeyboardButton("Сгенерировать число", callback_data='generate'),
            InlineKeyboardButton("Сбросить настройки", callback_data='reset_settings')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    settings = user_settings[user_id]
    await update.message.reply_text(
        f"🎲 Текущие настройки генератора:\n"
        f"Диапазон: от {settings['min']} до {settings['max']}\n"
        f"Исключенные числа: {', '.join(map(str, settings['exclude'])) if settings['exclude'] else 'нет'}\n\n"
        f"Выберите действие:",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик нажатий на инлайн-кнопки"""
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username
    now = datetime.now()
    # Сохраняем последнюю нажатую inline-кнопку
    ext = user_extended_stats.setdefault(user_id, {
        'messages_count': 0,
        'unique_days': set(),
        'last_streak_day': None,
        'streak': 0,
        'commands_usage': {},
        'last_inline_button': None,
        'last_message': None,
    })
    ext['last_inline_button'] = query.data
    
    if query.data == 'commands':
        await help_command(update, context)
    elif query.data == 'info':
        await info(update, context)
    elif query.data == 'cancel':
        await query.message.delete()
    elif query.data == 'more_joke':
        # Получаем доступные шутки (исключая последнюю показанную)
        available_jokes = [joke for joke in kartaviy_jokes if joke != last_jokes.get(user_id)]
        
        # Если все шутки были показаны, сбрасываем историю
        if not available_jokes:
            available_jokes = kartaviy_jokes.copy()
            last_jokes[user_id] = None
        
        # Выбираем случайную шутку из доступных
        joke = random.choice(available_jokes)
        last_jokes[user_id] = joke
        
        keyboard = [
            [
                InlineKeyboardButton("Ещё шутка", callback_data='more_joke'),
                InlineKeyboardButton("Спасибо", callback_data='cancel')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.message.edit_text(f"😄 {joke}", reply_markup=reply_markup)
    elif query.data == 'change_range':
        await query.message.reply_text(
            "Введите новый диапазон в формате: мин макс\n"
            "Например: 1 100"
        )
        context.user_data['waiting_for_range'] = True
    elif query.data == 'exclude_numbers':
        await query.message.reply_text(
            "Введите числа для исключения через пробел\n"
            "Например: 1 2 3"
        )
        context.user_data['waiting_for_exclude'] = True
    elif query.data == 'generate':
        settings = user_settings[user_id]
        available_numbers = [x for x in range(settings['min'], settings['max'] + 1) 
                           if x not in settings['exclude']]
        if not available_numbers:
            await query.message.reply_text("❌ Нет доступных чисел в выбранном диапазоне!")
            return
        number = random.choice(available_numbers)
        await query.message.reply_text(f"🎲 Ваше случайное число: {number}")
    elif query.data == 'reset_settings':
        user_settings[user_id] = {
            'min': 1,
            'max': 100,
            'exclude': []
        }
        await query.message.reply_text("✅ Настройки сброшены к значениям по умолчанию")

async def analyze_activity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Анализ статистики активности пользователя"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    
    # Если у пользователя нет истории активности, инициализируем её
    if user_id not in user_activity:
        user_activity[user_id] = {
            'first_visit': datetime.now(),
            'last_visit': datetime.now(),
            'total_visits': 1,
            'commands_used': {},
            'active_hours': [0] * 24  # Счетчик активности по часам
        }
    else:
        # Обновляем статистику
        user_activity[user_id]['last_visit'] = datetime.now()
        user_activity[user_id]['total_visits'] += 1
        current_hour = datetime.now().hour
        user_activity[user_id]['active_hours'][current_hour] += 1
    
    # Анализируем активность
    stats = user_activity[user_id]
    reg_data = user_registration.get(user_id, {})
    days_since_first_visit = (datetime.now() - stats['first_visit']).days
    avg_visits_per_day = stats['total_visits'] / max(1, days_since_first_visit)
    
    # Определяем самое активное время
    max_hour = stats['active_hours'].index(max(stats['active_hours']))
    active_time = f"{max_hour:02d}:00 - {max_hour+1:02d}:00"
    
    # Формируем сообщение с анализом
    analysis_message = (
        f"📊 Анализ активности пользователя @{username}:\n\n"
        f"📅 Первый визит: {stats['first_visit'].strftime('%d.%m.%Y %H:%M')}\n"
        f"🕒 Последний визит: {stats['last_visit'].strftime('%d.%m.%Y %H:%M')}\n"
        f"🔢 Всего визитов: {stats['total_visits']}\n"
        f"📈 Среднее количество визитов в день: {avg_visits_per_day:.1f}\n"
        f"⏰ Самое активное время: {active_time}\n\n"
    )
    
    # Добавляем информацию о регистрации
    if reg_data:
        reg_date = reg_data['registration_date'].strftime('%d.%m.%Y %H:%M')
        analysis_message += (
            f"📝 Данные о регистрации:\n"
            f"📅 Дата регистрации: {reg_date}\n"
            f"👤 Имя: {reg_data['first_name']}\n"
            f"🌐 Язык: {reg_data['language_code']}\n"
        )
    
    # Добавляем забавный комментарий на основе активности
    if avg_visits_per_day > 5:
        comment = "Ты что, живешь в этом боте? 😄"
    elif avg_visits_per_day > 2:
        comment = "Неплохая активность, продолжаем! 👍"
    else:
        comment = "Может быть, стоит заходить почаще? 🤔"
    
    analysis_message += f"\n💭 {comment}"
    
    await update.message.reply_text(analysis_message)

async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Вывод расширенной статистики для администратора"""
    user_id = update.effective_user.id
    username = update.effective_user.username
    if username != "sobsna_eto_moi_tg":
        await update.message.reply_text("У вас нет доступа к этой функции.")
        return
    total_users = len(user_registration)
    total_activity = sum(stats['total_visits'] for stats in user_activity.values())
    avg_visits_per_user = total_activity / max(1, total_users)
    stats_message = (
        f"📊 Расширенная статистика бота:\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"📈 Всего визитов: {total_activity}\n"
        f"📊 Среднее количество визитов на пользователя: {avg_visits_per_user:.1f}\n\n"
        f"📝 Последние зарегистрированные пользователи:\n"
    )
    recent_users = sorted(
        user_registration.items(),
        key=lambda x: x[1]['registration_date'],
        reverse=True
    )[:5]
    for uid, data in recent_users:
        ext = user_extended_stats.get(uid, {})
        reg_date = data['registration_date'].strftime('%d.%m.%Y %H:%M')
        visits = user_activity.get(uid, {}).get('total_visits', 0)
        streak = ext.get('streak', 0)
        unique_days = len(ext.get('unique_days', set()))
        last_message = ext.get('last_message', '-')
        last_inline = ext.get('last_inline_button', '-')
        commands_usage = ext.get('commands_usage', {})
        fav_command = max(commands_usage, key=commands_usage.get) if commands_usage else '-'
        stats_message += (
            f"👤 @{data['username']} ({data['first_name']})\n"
            f"🆔 ID: {uid}\n"
            f"📅 Регистрация: {reg_date}\n"
            f"🔢 Визитов: {visits}\n"
            f"🌐 Язык: {data['language_code']}\n"
            f"⭐ Premium: {'Да' if data.get('is_premium') else 'Нет'}\n"
            f"💬 Последнее сообщение: {last_message}\n"
            f"📅 Уникальных дней активности: {unique_days}\n"
            f"🔥 Стрик: {streak} дней\n"
            f"📋 Любимая команда: {fav_command}\n"
            f"🔘 Последняя inline-кнопка: {last_inline}\n"
            f"Тип чата: {data.get('chat_type', '-')}\n\n"
        )
    await update.message.reply_text(stats_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обычных сообщений"""
    text = update.message.text
    user_id = update.effective_user.id
    username = update.effective_user.username
    now = datetime.now()
    chat = update.message.chat if update.message else None
    chat_type = chat.type if chat else None
    
    # Обновляем статистику использования команд
    if user_id not in user_activity:
        user_activity[user_id] = {
            'first_visit': now,
            'last_visit': now,
            'total_visits': 1,
            'commands_used': {},
            'active_hours': [0] * 24
        }
    else:
        user_activity[user_id]['last_visit'] = now
        user_activity[user_id]['total_visits'] += 1
        current_hour = now.hour
        user_activity[user_id]['active_hours'][current_hour] += 1
    
    # Обновляем user_registration
    if user_id in user_registration:
        user_registration[user_id]['last_message_date'] = now
        user_registration[user_id]['chat_type'] = chat_type
        user_registration[user_id]['last_command'] = text if text.startswith('/') else user_registration[user_id].get('last_command')
    
    # Обновляем расширенную статистику
    ext = user_extended_stats.setdefault(user_id, {
        'messages_count': 0,
        'unique_days': set(),
        'last_streak_day': None,
        'streak': 0,
        'commands_usage': {},
        'last_inline_button': None,
        'last_message': None,
    })
    ext['messages_count'] += 1
    ext['unique_days'].add(now.date())
    # streak
    if ext['last_streak_day'] is None or (now.date() - ext['last_streak_day']).days == 1:
        ext['streak'] += 1
    elif (now.date() - ext['last_streak_day']).days > 1:
        ext['streak'] = 1
    ext['last_streak_day'] = now.date()
    ext['last_message'] = text
    if text.startswith('/'):
        ext['commands_usage'][text] = ext['commands_usage'].get(text, 0) + 1
    
    if text == "Анализировать информацию":
        await analyze_activity(update, context)
    elif text == "Ехала!":
        await start(update, context)
    elif text == "🎭 Попуск Михалыча":
        await mihalich(update, context)
    elif text == "🎲 Случайное число":
        await random_number(update, context)
    elif text == "📊 Расширенная статистика":
        await admin_stats(update, context)
    elif text == "Случайная картинка":
        await send_random_picture(update, context)
    elif text == "Случайный мем":
        await send_random_meme(update, context)
    elif context.user_data.get('waiting_for_range'):
        try:
            min_val, max_val = map(int, text.split())
            if min_val >= max_val:
                await update.message.reply_text("❌ Минимальное значение должно быть меньше максимального!")
            else:
                user_settings[user_id]['min'] = min_val
                user_settings[user_id]['max'] = max_val
                await update.message.reply_text(f"✅ Диапазон изменен: от {min_val} до {max_val}")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат! Введите два числа через пробел")
        context.user_data['waiting_for_range'] = False
    elif context.user_data.get('waiting_for_exclude'):
        try:
            exclude = list(map(int, text.split()))
            user_settings[user_id]['exclude'] = exclude
            await update.message.reply_text(f"✅ Исключенные числа: {', '.join(map(str, exclude))}")
        except ValueError:
            await update.message.reply_text("❌ Неверный формат! Введите числа через пробел")
        context.user_data['waiting_for_exclude'] = False
    else:
        await update.message.reply_text(f'Вы написали: {text}')

def main():
    """Основная функция запуска бота"""
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()

    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("info", info))
    application.add_handler(CommandHandler("mihalich", mihalich))
    application.add_handler(CommandHandler("random", random_number))
    
    # Добавляем обработчик инлайн-кнопок
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Добавляем обработчик обычных сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Запускаем бота
    print("Бот запущен...")
    application.run_polling()

if __name__ == '__main__':
    main() 