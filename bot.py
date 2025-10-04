"""
Telegram-бот для интернет-провайдера
Автоматизация отчетности по подключению новых абонентов
"""
import os
import logging
from typing import Dict, List
from datetime import datetime

from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

from database import Database
from report_generator import ReportGenerator

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Константы состояний для ConversationHandler
# Создание подключения
UPLOAD_PHOTOS, ENTER_ADDRESS, ENTER_ROUTER, ENTER_PORT, ENTER_FIBER, ENTER_TWISTED, SELECT_EMPLOYEES, CONFIRM = range(8)

# Управление сотрудниками
MANAGE_ACTION, ADD_EMPLOYEE_NAME, DELETE_EMPLOYEE_SELECT = range(8, 11)

# Отчеты
SELECT_REPORT_EMPLOYEE, SELECT_REPORT_PERIOD = range(11, 13)

# Инициализация БД
db = Database()

# Загрузка ID администраторов
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id.strip()]

# ID канала для отправки отчетов (опционально)
REPORTS_CHANNEL_ID = os.getenv('REPORTS_CHANNEL_ID', '').strip()
if REPORTS_CHANNEL_ID:
    try:
        REPORTS_CHANNEL_ID = int(REPORTS_CHANNEL_ID)
        logger.info(f"Канал для отчетов настроен: {REPORTS_CHANNEL_ID}")
    except ValueError:
        REPORTS_CHANNEL_ID = None
        logger.warning("REPORTS_CHANNEL_ID имеет неверный формат")
else:
    REPORTS_CHANNEL_ID = None


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создать главную клавиатуру"""
    keyboard = [
        [KeyboardButton("📝 Новое подключение")],
        [KeyboardButton("📊 Сводный отчет")],
        [KeyboardButton("👥 Управление сотрудниками")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)


# ==================== КОМАНДЫ ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /start"""
    user = update.effective_user
    welcome_text = f"""
👋 Добро пожаловать, {user.first_name}!

Это бот для автоматизации отчетности по подключению новых абонентов.

🔹 Основные функции:
• Создание отчетов о подключении с фотографиями
• Выбор исполнителей из списка
• Автоматический расчет метража на каждого исполнителя
• Формирование сводных отчетов в Excel

📋 Доступные команды:
/new - Создать новый отчет
/report - Получить сводный отчет
/manage_employees - Управление сотрудниками
/cancel - Отменить текущую операцию
/help - Справка

Выберите действие на клавиатуре ниже:
"""
    await update.message.reply_text(welcome_text, reply_markup=get_main_keyboard())


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка команды /help"""
    help_text = """
📚 <b>Справка по использованию бота</b>

<b>Создание отчета о подключении:</b>
1. Нажмите "📝 Новое подключение" или /new
2. Загрузите фотографии (до 10 штук)
3. Нажмите "Продолжить"
4. Заполните данные о подключении
5. Выберите исполнителей
6. Подтвердите создание

<b>Получение сводного отчета:</b>
1. Нажмите "📊 Сводный отчет" или /report
2. Выберите сотрудника
3. Выберите период
4. Получите Excel-файл

<b>Управление сотрудниками:</b>
(только для администраторов)
1. Нажмите "👥 Управление сотрудниками"
2. Добавьте или удалите сотрудников

<b>Логика расчета метража:</b>
Метраж делится поровну между всеми исполнителями.
Например: 100м ВОЛС на 2 исполнителей = по 50м каждому

❓ Если возникли вопросы - обратитесь к администратору.
"""
    await update.message.reply_text(help_text, parse_mode='HTML')


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущей операции"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ Операция отменена.",
        reply_markup=get_main_keyboard()
    )
    return ConversationHandler.END


# ==================== СОЗДАНИЕ ПОДКЛЮЧЕНИЯ ====================

async def new_connection_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания нового подключения"""
    # Инициализация данных
    context.user_data['photos'] = []
    context.user_data['connection_data'] = {}
    
    keyboard = [[InlineKeyboardButton("➡️ Продолжить без фото", callback_data='skip_photos')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
📸 <b>Шаг 1/7: Загрузка фотографий</b>

Загрузите фотографии с места подключения (до 10 штук).
После загрузки всех фото нажмите "Продолжить".

Можете пропустить этот шаг, если фото не требуются.
"""
    
    # Проверяем, откуда пришел запрос
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return UPLOAD_PHOTOS


async def upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка загружаемых фотографий"""
    if update.message.photo:
        photos = context.user_data.get('photos', [])
        
        if len(photos) >= 10:
            await update.message.reply_text("⚠️ Достигнут лимит в 10 фотографий.")
            return UPLOAD_PHOTOS
        
        # Сохраняем file_id самого большого размера фото
        photo_file_id = update.message.photo[-1].file_id
        photos.append(photo_file_id)
        context.user_data['photos'] = photos
        
        keyboard = [[InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Фото {len(photos)}/10 загружено.\n\n"
            f"Можете загрузить еще фото или нажмите 'Продолжить'.",
            reply_markup=reply_markup
        )
        return UPLOAD_PHOTOS
    
    return UPLOAD_PHOTOS


async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос адреса подключения"""
    query = update.callback_query
    await query.answer()
    
    photos_count = len(context.user_data.get('photos', []))
    await query.edit_message_text(
        f"✅ Загружено фото: {photos_count}\n\n"
        f"📍 <b>Шаг 2/7: Адрес подключения</b>\n\n"
        f"Введите адрес подключения абонента:",
        parse_mode='HTML'
    )
    
    return ENTER_ADDRESS


async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение адреса и запрос модели роутера"""
    address = update.message.text.strip()
    context.user_data['connection_data']['address'] = address
    
    await update.message.reply_text(
        f"✅ Адрес: {address}\n\n"
        f"🌐 <b>Шаг 3/7: Модель роутера</b>\n\n"
        f"Введите модель роутера:",
        parse_mode='HTML'
    )
    
    return ENTER_ROUTER


async def enter_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение модели роутера и запрос порта"""
    router = update.message.text.strip()
    context.user_data['connection_data']['router_model'] = router
    
    await update.message.reply_text(
        f"✅ Роутер: {router}\n\n"
        f"🔌 <b>Шаг 4/7: Номер порта</b>\n\n"
        f"Введите номер порта:",
        parse_mode='HTML'
    )
    
    return ENTER_PORT


async def enter_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение порта и запрос метража ВОЛС"""
    port = update.message.text.strip()
    context.user_data['connection_data']['port'] = port
    
    await update.message.reply_text(
        f"✅ Порт: {port}\n\n"
        f"📏 <b>Шаг 5/7: Метраж ВОЛС</b>\n\n"
        f"Введите количество метров ВОЛС (волоконно-оптической линии связи):",
        parse_mode='HTML'
    )
    
    return ENTER_FIBER


async def enter_fiber(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение метража ВОЛС и запрос метража витой пары"""
    try:
        fiber_meters = float(update.message.text.strip().replace(',', '.'))
        if fiber_meters < 0:
            raise ValueError
        
        context.user_data['connection_data']['fiber_meters'] = fiber_meters
        
        await update.message.reply_text(
            f"✅ ВОЛС: {fiber_meters} м\n\n"
            f"📏 <b>Шаг 6/7: Метраж витой пары</b>\n\n"
            f"Введите количество метров витой пары:",
            parse_mode='HTML'
        )
        
        return ENTER_TWISTED
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_FIBER


async def enter_twisted(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение метража витой пары и переход к выбору сотрудников"""
    try:
        twisted_meters = float(update.message.text.strip().replace(',', '.'))
        if twisted_meters < 0:
            raise ValueError
        
        context.user_data['connection_data']['twisted_pair_meters'] = twisted_meters
        
        # Получаем список сотрудников
        employees = db.get_all_employees()
        
        if not employees:
            await update.message.reply_text(
                "⚠️ В системе нет ни одного сотрудника!\n\n"
                "Обратитесь к администратору для добавления сотрудников.",
                reply_markup=get_main_keyboard()
            )
            return ConversationHandler.END
        
        # Создаем клавиатуру для выбора сотрудников
        context.user_data['selected_employees'] = []
        keyboard = []
        
        for emp in employees:
            keyboard.append([InlineKeyboardButton(
                f"☐ {emp['full_name']}", 
                callback_data=f"emp_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("✅ Готово", callback_data='employees_done')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Витая пара: {twisted_meters} м\n\n"
            f"👥 <b>Шаг 7/7: Выбор исполнителей</b>\n\n"
            f"Выберите сотрудников, которые участвовали в подключении:\n"
            f"(можно выбрать нескольких)",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return SELECT_EMPLOYEES
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED


async def select_employee_toggle(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Переключение выбора сотрудника"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'employees_done':
        selected = context.user_data.get('selected_employees', [])
        
        if not selected:
            await query.answer("⚠️ Выберите хотя бы одного сотрудника!", show_alert=True)
            return SELECT_EMPLOYEES
        
        # Показываем подтверждение
        return await show_confirmation(update, context)
    
    # Переключаем выбор сотрудника
    emp_id = int(query.data.split('_')[1])
    selected = context.user_data.get('selected_employees', [])
    
    if emp_id in selected:
        selected.remove(emp_id)
    else:
        selected.append(emp_id)
    
    context.user_data['selected_employees'] = selected
    
    # Обновляем клавиатуру
    employees = db.get_all_employees()
    keyboard = []
    
    for emp in employees:
        is_selected = emp['id'] in selected
        checkbox = "☑" if is_selected else "☐"
        keyboard.append([InlineKeyboardButton(
            f"{checkbox} {emp['full_name']}", 
            callback_data=f"emp_{emp['id']}"
        )])
    
    keyboard.append([InlineKeyboardButton("✅ Готово", callback_data='employees_done')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except:
        pass  # Игнорируем ошибку, если сообщение не изменилось
    
    return SELECT_EMPLOYEES


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показать данные для подтверждения"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    photos_count = len(context.user_data.get('photos', []))
    selected_emp_ids = context.user_data.get('selected_employees', [])
    
    # Получаем имена выбранных сотрудников
    employees = db.get_all_employees()
    selected_names = [emp['full_name'] for emp in employees if emp['id'] in selected_emp_ids]
    
    # Рассчитываем долю на каждого
    emp_count = len(selected_emp_ids)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
    
    confirmation_text = f"""
📋 <b>Проверьте данные перед сохранением:</b>

📸 Фотографий: {photos_count}
📍 Адрес: {data['address']}
🌐 Роутер: {data['router_model']}
🔌 Порт: {data['port']}
📏 ВОЛС: {data['fiber_meters']} м
📏 Витая пара: {data['twisted_pair_meters']} м

👥 <b>Исполнители ({emp_count}):</b>
{chr(10).join(['• ' + name for name in selected_names])}

💡 <b>Расчет на каждого:</b>
• ВОЛС: {fiber_per_emp} м
• Витая пара: {twisted_per_emp} м

Все верно?
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm_yes')],
        [InlineKeyboardButton("❌ Отменить", callback_data='confirm_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        confirmation_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return CONFIRM


async def send_connection_report(message, connection_id: int, data: Dict, photos: List[str], employee_ids: List[int]) -> None:
    """Отправить красиво отформатированный отчет о подключении с фотографиями"""
    try:
        # Получаем имена сотрудников
        employees = db.get_all_employees()
        employee_names = [emp['full_name'] for emp in employees if emp['id'] in employee_ids]
        
        # Рассчитываем долю на каждого
        emp_count = len(employee_ids)
        fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
        twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
        
        # Формируем текст отчета
        report_text = f"""
📋 <b>ОТЧЕТ О ПОДКЛЮЧЕНИИ #{connection_id}</b>

📍 <b>Адрес:</b> {data['address']}
🌐 <b>Модель роутера:</b> {data['router_model']}
🔌 <b>Порт:</b> {data['port']}

📏 <b>Проложенный кабель:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

👥 <b>Исполнители ({emp_count}):</b>
{chr(10).join(['  • ' + name for name in employee_names])}

💡 <b>Расчет на каждого исполнителя:</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м

📅 <b>Дата подключения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        
        # Отправляем отчет пользователю
        if photos:
            # Создаем медиа-группу
            media_group = []
            for idx, photo_id in enumerate(photos):
                if idx == 0:
                    # К первому фото прикрепляем описание
                    media_group.append(InputMediaPhoto(media=photo_id, caption=report_text, parse_mode='HTML'))
                else:
                    media_group.append(InputMediaPhoto(media=photo_id))
            
            # Отправляем альбом пользователю
            await message.reply_media_group(media=media_group)
            logger.info(f"Отправлен отчет #{connection_id} пользователю с {len(photos)} фото")
        else:
            # Если фото нет, просто отправляем текст
            await message.reply_text(report_text, parse_mode='HTML')
            logger.info(f"Отправлен отчет #{connection_id} пользователю без фото")
        
        # Отправляем отчет в канал, если он настроен
        if REPORTS_CHANNEL_ID:
            try:
                bot = message.get_bot()
                if photos:
                    # Создаем медиа-группу для канала
                    channel_media_group = []
                    for idx, photo_id in enumerate(photos):
                        if idx == 0:
                            channel_media_group.append(InputMediaPhoto(media=photo_id, caption=report_text, parse_mode='HTML'))
                        else:
                            channel_media_group.append(InputMediaPhoto(media=photo_id))
                    
                    await bot.send_media_group(chat_id=REPORTS_CHANNEL_ID, media=channel_media_group)
                    logger.info(f"Отчет #{connection_id} отправлен в канал с {len(photos)} фото")
                else:
                    await bot.send_message(chat_id=REPORTS_CHANNEL_ID, text=report_text, parse_mode='HTML')
                    logger.info(f"Отчет #{connection_id} отправлен в канал без фото")
            except Exception as channel_error:
                logger.error(f"Ошибка при отправке отчета в канал: {channel_error}")
                # Не показываем ошибку пользователю, т.к. отчет ему уже отправлен
            
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета о подключении: {e}")
        await message.reply_text(
            "⚠️ Отчет создан, но возникла ошибка при отправке фотографий.",
            parse_mode='HTML'
        )


async def confirm_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и сохранение подключения"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm_no':
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Создание отчета отменено.",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем в БД
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    user_id = update.effective_user.id
    
    connection_id = db.create_connection(
        address=data['address'],
        router_model=data['router_model'],
        port=data['port'],
        fiber_meters=data['fiber_meters'],
        twisted_pair_meters=data['twisted_pair_meters'],
        employee_ids=selected_employees,
        photo_file_ids=photos,
        created_by=user_id
    )
    
    if connection_id:
        await query.edit_message_text(
            f"✅ <b>Отчет успешно создан!</b>\n\n"
            f"ID подключения: #{connection_id}\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
        # Отправляем отчет с фотографиями
        await send_connection_report(query.message, connection_id, data, photos, selected_employees)
        
        await query.message.reply_text(
            "Выберите следующее действие:",
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при создании отчета. Попробуйте позже.",
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END


# ==================== СВОДНЫЕ ОТЧЕТЫ ====================

async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало формирования отчета"""
    employees = db.get_all_employees()
    
    if not employees:
        text = "⚠️ В системе нет ни одного сотрудника!"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    keyboard = []
    for emp in employees:
        keyboard.append([InlineKeyboardButton(emp['full_name'], callback_data=f"rep_emp_{emp['id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='report_cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📊 <b>Сводный отчет</b>\n\nВыберите сотрудника:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return SELECT_REPORT_EMPLOYEE


async def report_select_period(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Выбор периода для отчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'report_cancel':
        await query.edit_message_text("❌ Формирование отчета отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    # Сохраняем выбранного сотрудника
    emp_id = int(query.data.split('_')[2])
    context.user_data['report_employee_id'] = emp_id
    
    employee = db.get_employee_by_id(emp_id)
    
    keyboard = [
        [InlineKeyboardButton("📅 Последняя неделя", callback_data='period_7')],
        [InlineKeyboardButton("📅 Последний месяц", callback_data='period_30')],
        [InlineKeyboardButton("📅 Все время", callback_data='period_all')],
        [InlineKeyboardButton("❌ Отмена", callback_data='period_cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Выбран сотрудник: <b>{employee['full_name']}</b>\n\n"
        f"Выберите период для отчета:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_REPORT_PERIOD


async def report_generate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Генерация и отправка отчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'period_cancel':
        await query.edit_message_text("❌ Формирование отчета отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END
    
    # Определяем период
    period_map = {
        'period_7': (7, 'Последняя неделя'),
        'period_30': (30, 'Последний месяц'),
        'period_all': (None, 'Все время')
    }
    
    days, period_name = period_map[query.data]
    emp_id = context.user_data['report_employee_id']
    employee = db.get_employee_by_id(emp_id)
    
    await query.edit_message_text("⏳ Формирую отчет, подождите...")
    
    # Получаем данные из БД
    connections, stats = db.get_employee_report(emp_id, days)
    
    if not connections:
        await query.message.reply_text(
            f"ℹ️ У сотрудника <b>{employee['full_name']}</b> нет подключений за выбранный период.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Генерируем Excel-отчет
    try:
        filename = ReportGenerator.generate_employee_report(
            employee_name=employee['full_name'],
            connections=connections,
            stats=stats,
            period_name=period_name
        )
        
        # Отправляем файл
        with open(filename, 'rb') as file:
            await query.message.reply_document(
                document=file,
                filename=filename,
                caption=f"📊 Отчет по сотруднику: <b>{employee['full_name']}</b>\n"
                        f"Период: {period_name}\n"
                        f"Подключений: {stats['total_connections']}\n"
                        f"ВОЛС: {stats['total_fiber_meters']} м\n"
                        f"Витая пара: {stats['total_twisted_pair_meters']} м",
                parse_mode='HTML'
            )
        
        # Удаляем временный файл
        os.remove(filename)
        
        await query.message.reply_text(
            "✅ Отчет сформирован!",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}")
        await query.message.reply_text(
            "❌ Ошибка при формировании отчета. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END


# ==================== УПРАВЛЕНИЕ СОТРУДНИКАМИ ====================

async def manage_employees_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало управления сотрудниками"""
    user_id = update.effective_user.id
    
    if not is_admin(user_id):
        text = "⛔ У вас нет прав для управления сотрудниками."
        if update.callback_query:
            await update.callback_query.answer(text, show_alert=True)
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить сотрудника", callback_data='manage_add')],
        [InlineKeyboardButton("➖ Удалить сотрудника", callback_data='manage_delete')],
        [InlineKeyboardButton("📋 Список сотрудников", callback_data='manage_list')],
        [InlineKeyboardButton("❌ Отмена", callback_data='manage_cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "👥 <b>Управление сотрудниками</b>\n\nВыберите действие:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return MANAGE_ACTION


async def manage_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора действия"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'manage_cancel':
        await query.edit_message_text("❌ Управление сотрудниками отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    if query.data == 'back_to_manage':
        # Возврат к главному меню управления сотрудниками
        keyboard = [
            [InlineKeyboardButton("➕ Добавить сотрудника", callback_data='manage_add')],
            [InlineKeyboardButton("➖ Удалить сотрудника", callback_data='manage_delete')],
            [InlineKeyboardButton("📋 Список сотрудников", callback_data='manage_list')],
            [InlineKeyboardButton("❌ Отмена", callback_data='manage_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "👥 <b>Управление сотрудниками</b>\n\nВыберите действие:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return MANAGE_ACTION
    
    if query.data == 'manage_add':
        await query.edit_message_text(
            "➕ <b>Добавление сотрудника</b>\n\n"
            "Введите ФИО сотрудника:",
            parse_mode='HTML'
        )
        return ADD_EMPLOYEE_NAME
    
    if query.data == 'manage_delete':
        employees = db.get_all_employees()
        
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников для удаления.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        
        keyboard = []
        for emp in employees:
            keyboard.append([InlineKeyboardButton(
                f"🗑 {emp['full_name']}", 
                callback_data=f"del_emp_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='delete_cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➖ <b>Удаление сотрудника</b>\n\n"
            "Выберите сотрудника для удаления:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return DELETE_EMPLOYEE_SELECT
    
    if query.data == 'manage_list':
        employees = db.get_all_employees()
        
        if not employees:
            text = "📋 <b>Список сотрудников</b>\n\nСписок пуст."
        else:
            emp_list = '\n'.join([f"{idx}. {emp['full_name']}" for idx, emp in enumerate(employees, 1)])
            text = f"📋 <b>Список сотрудников ({len(employees)}):</b>\n\n{emp_list}"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_manage')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return MANAGE_ACTION


async def add_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавление нового сотрудника"""
    full_name = update.message.text.strip()
    
    if len(full_name) < 3:
        await update.message.reply_text("⚠️ ФИО должно содержать минимум 3 символа. Попробуйте еще раз:")
        return ADD_EMPLOYEE_NAME
    
    employee_id = db.add_employee(full_name)
    
    if employee_id:
        await update.message.reply_text(
            f"✅ Сотрудник <b>{full_name}</b> успешно добавлен!",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            f"⚠️ Сотрудник <b>{full_name}</b> уже существует в системе!",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
    
    return ConversationHandler.END


async def delete_employee_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Удаление сотрудника"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'delete_cancel':
        await query.edit_message_text("❌ Удаление отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    emp_id = int(query.data.split('_')[2])
    employee = db.get_employee_by_id(emp_id)
    
    if db.delete_employee(emp_id):
        await query.edit_message_text(
            f"✅ Сотрудник <b>{employee['full_name']}</b> удален!",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text("❌ Ошибка при удалении сотрудника.")
    
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END


# ==================== ОБРАБОТЧИКИ КНОПОК КЛАВИАТУРЫ ====================

async def handle_keyboard_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатий кнопок основной клавиатуры"""
    text = update.message.text
    
    if text == "📝 Новое подключение":
        return await new_connection_start(update, context)
    elif text == "📊 Сводный отчет":
        return await report_start(update, context)
    elif text == "👥 Управление сотрудниками":
        return await manage_employees_start(update, context)
    elif text == "ℹ️ Помощь":
        return await help_command(update, context)


# ==================== ГЛАВНАЯ ФУНКЦИЯ ====================

def main():
    """Запуск бота"""
    token = os.getenv('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return
    
    # Создаем приложение
    application = Application.builder().token(token).build()
    
    # Обработчик создания подключения
    connection_conv = ConversationHandler(
        entry_points=[
            CommandHandler('new', new_connection_start),
            MessageHandler(filters.Regex('^📝 Новое подключение$'), new_connection_start)
        ],
        states={
            UPLOAD_PHOTOS: [
                MessageHandler(filters.PHOTO, upload_photos),
                CallbackQueryHandler(ask_address, pattern='^(skip_photos|continue_from_photos)$')
            ],
            ENTER_ADDRESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_address)],
            ENTER_ROUTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_router)],
            ENTER_PORT: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_port)],
            ENTER_FIBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_fiber)],
            ENTER_TWISTED: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_twisted)],
            SELECT_EMPLOYEES: [CallbackQueryHandler(select_employee_toggle, pattern='^(emp_|employees_done)')],
            CONFIRM: [CallbackQueryHandler(confirm_connection, pattern='^confirm_')]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # Обработчик отчетов
    report_conv = ConversationHandler(
        entry_points=[
            CommandHandler('report', report_start),
            MessageHandler(filters.Regex('^📊 Сводный отчет$'), report_start)
        ],
        states={
            SELECT_REPORT_EMPLOYEE: [CallbackQueryHandler(report_select_period, pattern='^(rep_emp_|report_cancel)')],
            SELECT_REPORT_PERIOD: [CallbackQueryHandler(report_generate, pattern='^(period_|period_cancel)')]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # Обработчик управления сотрудниками
    manage_conv = ConversationHandler(
        entry_points=[
            CommandHandler('manage_employees', manage_employees_start),
            MessageHandler(filters.Regex('^👥 Управление сотрудниками$'), manage_employees_start)
        ],
        states={
            MANAGE_ACTION: [CallbackQueryHandler(manage_action, pattern='^(manage_|back_to_manage)')],
            ADD_EMPLOYEE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_employee_name)],
            DELETE_EMPLOYEE_SELECT: [CallbackQueryHandler(delete_employee_confirm, pattern='^(del_emp_|delete_cancel)')]
        },
        fallbacks=[CommandHandler('cancel', cancel_command)]
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(connection_conv)
    application.add_handler(report_conv)
    application.add_handler(manage_conv)
    application.add_handler(MessageHandler(filters.Regex('^ℹ️ Помощь$'), help_command))
    
    # Запускаем бота
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
