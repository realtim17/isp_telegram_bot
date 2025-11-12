"""
Обработчики шагов создания подключения
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_CONNECTION_TYPE, UPLOAD_PHOTOS, ENTER_ADDRESS, SELECT_ROUTER, 
    ENTER_ROUTER_QUANTITY_CONNECTION, ROUTER_ACCESS, ENTER_PORT, ENTER_FIBER, 
    ENTER_TWISTED, CONTRACT_SIGNED, SELECT_EMPLOYEES, CONNECTION_TYPES
)
from utils.keyboards import get_main_keyboard
from handlers.connection.constants import MAX_PHOTOS, PHOTO_REQUIREMENTS
from handlers.connection.cancellation import cancel_connection
from database import Database


async def new_connection_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало создания нового подключения"""
    # Инициализация данных
    context.user_data['photos'] = []
    context.user_data['connection_data'] = {}
    
    # Создаем клавиатуру для выбора типа подключения
    keyboard = [
        [InlineKeyboardButton("1️⃣ МКД", callback_data='conn_type_mkd')],
        [InlineKeyboardButton("2️⃣ ЧС", callback_data='conn_type_chs')],
        [InlineKeyboardButton("3️⃣ Юр / Гос", callback_data='conn_type_legal')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = """
🏢 <b>Шаг 1/11: Тип подключения</b>

Выберите тип подключения:

1️⃣ МКД - многоквартирный дом
2️⃣ ЧС - частный сектор
3️⃣ Юр / Гос - юридическое лицо / государственная организация
"""
    
    # Проверяем, откуда пришел запрос
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return SELECT_CONNECTION_TYPE


async def select_connection_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение выбранного типа подключения"""
    query = update.callback_query
    await query.answer()
    
    # Извлекаем тип подключения из callback_data
    conn_type = query.data.split('_')[-1]
    context.user_data['connection_data']['connection_type'] = conn_type
    
    # Получаем читаемое название
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    text = f"""
✅ Тип подключения: <b>{type_name}</b>

📸 <b>Шаг 2/11: Загрузка фотографий</b>

Загрузите фотографии с места подключения (до {MAX_PHOTOS} штук).
После загрузки фото нажмите "Продолжить".

{PHOTO_REQUIREMENTS}

⚠️ <b>Внимание:</b> Загрузка фотографий обязательна!
"""
    
    keyboard = [
        [InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return UPLOAD_PHOTOS


async def upload_photos(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка загружаемых фотографий"""
    if update.message.photo:
        photos = context.user_data.get('photos', [])
        
        if len(photos) >= MAX_PHOTOS:
            await update.message.reply_text(f"⚠️ Достигнут лимит в {MAX_PHOTOS} фотографий.")
            return UPLOAD_PHOTOS
        
        # Сохраняем file_id самого большого размера фото
        photo_file_id = update.message.photo[-1].file_id
        photos.append(photo_file_id)
        context.user_data['photos'] = photos
        
        keyboard = [
            [InlineKeyboardButton("➡️ Продолжить", callback_data='continue_from_photos')],
            [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Если это первое фото - отправляем новое сообщение и сохраняем его ID
        if len(photos) == 1:
            sent_message = await update.message.reply_text(
                f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
                f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                reply_markup=reply_markup
            )
            context.user_data['upload_message_id'] = sent_message.message_id
        else:
            # Для последующих фото - редактируем существующее сообщение
            try:
                await context.bot.edit_message_text(
                    chat_id=update.effective_chat.id,
                    message_id=context.user_data.get('upload_message_id'),
                    text=f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
                         f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                    reply_markup=reply_markup
                )
            except Exception:
                # Если не удалось отредактировать, отправляем новое
                sent_message = await update.message.reply_text(
                    f"✅ Фото {len(photos)}/{MAX_PHOTOS} загружено.\n\n"
                    f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                    reply_markup=reply_markup
                )
                context.user_data['upload_message_id'] = sent_message.message_id
        
        return UPLOAD_PHOTOS
    
    return UPLOAD_PHOTOS


async def ask_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Запрос адреса подключения"""
    query = update.callback_query
    await query.answer()
    
    photos_count = len(context.user_data.get('photos', []))
    
    # Проверяем, что загружено хотя бы одно фото
    if photos_count == 0:
        await query.edit_message_text(
            "⚠️ <b>Ошибка:</b> Необходимо загрузить хотя бы одно фото!\n\n"
            "📸 Загрузите фотографии с места подключения.",
            parse_mode='HTML'
        )
        return UPLOAD_PHOTOS
    
    # Создаём клавиатуру с кнопкой отмены
    keyboard = [[KeyboardButton("❌ Отмена")]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await query.edit_message_text(
        f"✅ Загружено фото: {photos_count}\n\n"
        f"📍 <b>Шаг 3/11: Адрес подключения</b>\n\n"
        f"Введите адрес подключения абонента:",
        parse_mode='HTML'
    )
    
    # Отправляем сообщение с клавиатурой отмены
    await query.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=reply_markup
    )
    
    return ENTER_ADDRESS


async def enter_address(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение адреса и переход к выбору роутера"""
    address = update.message.text.strip()
    
    # Проверяем отмену
    if address == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    # Проверяем и инициализируем connection_data если нужно
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    context.user_data['connection_data']['address'] = address
    
    # Получаем список роутеров из БД
    db = Database()
    router_names = db.get_all_router_names()
    
    # Создаём клавиатуру с роутерами
    keyboard = []
    
    if router_names:
        for router_name in router_names:
            keyboard.append([InlineKeyboardButton(
                f"📡 {router_name}",
                callback_data=f"select_router_{router_name}"
            )])
    
    # Добавляем кнопку "Пропустить"
    keyboard.append([InlineKeyboardButton("⏭️ Пропустить", callback_data='router_skip')])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Убираем клавиатуру отмены и показываем inline-клавиатуру
    if router_names:
        message_text = f"✅ Адрес: {address}\n\n🌐 <b>Шаг 4/11: Модель роутера</b>\n\nВыберите роутер из списка или пропустите:"
    else:
        message_text = f"✅ Адрес: {address}\n\n🌐 <b>Шаг 4/11: Модель роутера</b>\n\n⚠️ В системе нет зарегистрированных роутеров.\nВы можете пропустить этот шаг:"
    
    await update.message.reply_text(
        message_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_ROUTER


async def select_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора роутера или пропуска"""
    query = update.callback_query
    await query.answer()
    
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    # Обработка пропуска
    if query.data == 'router_skip':
        context.user_data['connection_data']['router_model'] = '-'
        context.user_data['connection_data']['router_quantity'] = 0
        
        # Сразу переходим к шагу "Доступ на роутер"
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data='router_access_confirmed')],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data='router_access_skipped')],
            [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"⏭️ Роутер: пропущено\n\n"
            f"🔐 <b>Шаг 6/11: Доступ на роутер</b>\n\n"
            f"Подтвердите, что доступ на роутер открыт:",
            parse_mode='HTML'
        )
        
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        return ROUTER_ACCESS
    
    # Выбран роутер из списка
    router_name = query.data.replace('select_router_', '')
    context.user_data['connection_data']['router_model'] = router_name
    
    # Добавляем клавиатуру отмены для ввода количества роутеров
    keyboard = [[KeyboardButton("❌ Отмена")]]
    reply_markup_kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await query.edit_message_text(
        f"✅ Роутер: {router_name}\n\n"
        f"📦 <b>Шаг 5/11: Количество роутеров</b>\n\n"
        f"Введите количество роутеров (по умолчанию: 1):",
        parse_mode='HTML'
    )
    
    await query.message.reply_text(
        "Для отмены нажмите кнопку ниже:",
        reply_markup=reply_markup_kb
    )
    
    return ENTER_ROUTER_QUANTITY_CONNECTION


async def enter_router_quantity_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода количества роутеров"""
    text = update.message.text.strip()
    
    # Проверяем отмену
    if text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    try:
        router_quantity = int(text)
        if router_quantity <= 0:
            raise ValueError
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['router_quantity'] = router_quantity
        
        # Переход к новому шагу "Доступ на роутер"
        keyboard = [
            [InlineKeyboardButton("✅ Подтвердить", callback_data='router_access_confirmed')],
            [InlineKeyboardButton("⏭️ Пропустить", callback_data='router_access_skipped')],
            [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Количество роутеров: {router_quantity}\n\n"
            f"🔐 <b>Шаг 6/11: Доступ на роутер</b>\n\n"
            f"Подтвердите, что доступ на роутер открыт:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        await update.message.reply_text(
            "Выберите действие:",
            reply_markup=reply_markup
        )
        
        return ROUTER_ACCESS
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное целое число больше нуля (например: 1, 2, 3)"
        )
        return ENTER_ROUTER_QUANTITY_CONNECTION


async def router_access_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения доступа на роутер"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    # Сохраняем информацию о доступе на роутер
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    if query.data == 'router_access_confirmed':
        context.user_data['connection_data']['router_access'] = True
        status_text = "✅ Доступ получен"
    else:  # router_access_skipped
        context.user_data['connection_data']['router_access'] = False
        status_text = "⏭️ Пропущено"
    
    # Создаём inline клавиатуру с кнопкой "Пропустить" для порта
    keyboard = [
        [InlineKeyboardButton("⏭️ Пропустить", callback_data='port_skip')],
        [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
    ]
    reply_markup_inline = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"{status_text}\n\n"
        f"🔌 <b>Шаг 7/11: Номер порта</b>\n\n"
        f"Введите номер порта или пропустите:",
        parse_mode='HTML'
    )
    
    await query.message.reply_text(
        "Введите номер порта текстом или используйте кнопки ниже:",
        reply_markup=reply_markup_inline
    )
    
    return ENTER_PORT


async def enter_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение порта и запрос метража ВОЛС"""
    # Обработка callback (кнопка "Пропустить")
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'cancel_connection':
            return await cancel_connection(update, context)
        
        if query.data == 'port_skip':
            if 'connection_data' not in context.user_data:
                context.user_data['connection_data'] = {}
            
            context.user_data['connection_data']['port'] = '-'
            
            # Добавляем клавиатуру отмены для ввода ВОЛС
            keyboard = [[KeyboardButton("❌ Отмена")]]
            reply_markup_kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            await query.edit_message_text(
                f"⏭️ Порт: пропущено\n\n"
                f"📏 <b>Шаг 8/11: Метраж ВОЛС</b>\n\n"
                f"Введите количество метров ВОЛС (волоконно-оптической линии связи):",
                parse_mode='HTML'
            )
            
            await query.message.reply_text(
                "Для отмены нажмите кнопку ниже:",
                reply_markup=reply_markup_kb
            )
            
            return ENTER_FIBER
    
    # Обработка текстового ввода
    port = update.message.text.strip()
    
    # Проверяем отмену
    if port == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    
    context.user_data['connection_data']['port'] = port
    
    # Добавляем клавиатуру отмены для ввода ВОЛС
    keyboard = [[KeyboardButton("❌ Отмена")]]
    reply_markup_kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    
    await update.message.reply_text(
        f"✅ Порт: {port}\n\n"
        f"📏 <b>Шаг 8/11: Метраж ВОЛС</b>\n\n"
        f"Введите количество метров ВОЛС (волоконно-оптической линии связи):",
        reply_markup=reply_markup_kb,
        parse_mode='HTML'
    )
    
    return ENTER_FIBER


async def enter_fiber(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение метража ВОЛС и запрос метража витой пары"""
    text = update.message.text.strip()
    
    # Проверяем отмену
    if text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    try:
        fiber_meters = float(text.replace(',', '.'))
        if fiber_meters < 0:
            raise ValueError
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['fiber_meters'] = fiber_meters
        
        await update.message.reply_text(
            f"✅ ВОЛС: {fiber_meters} м\n\n"
            f"📏 <b>Шаг 9/11: Метраж витой пары</b>\n\n"
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
    """Сохранение метража витой пары и переход к подтверждению договора"""
    text = update.message.text.strip()
    
    # Проверяем отмену
    if text == "❌ Отмена":
        context.user_data.clear()
        await update.message.reply_text(
            "❌ <b>Создание подключения отменено</b>\n\n"
            "Все введённые данные удалены.",
            reply_markup=get_main_keyboard(),
            parse_mode='HTML'
        )
        return ConversationHandler.END
    
    try:
        twisted_meters = float(text.replace(',', '.'))
        if twisted_meters < 0:
            raise ValueError
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['twisted_pair_meters'] = twisted_meters
        
        # Переходим к подтверждению договора
        keyboard = [
            [InlineKeyboardButton("✅ Подтверждаю", callback_data='contract_confirmed')],
            [InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Витая пара: {twisted_meters} м\n\n"
            f"📄 <b>Шаг 10/11: Договор подписан</b>\n\n"
            f"Подтвердите, что договор подписан:",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        await update.message.reply_text(
            "Нажмите кнопку для подтверждения:",
            reply_markup=reply_markup
        )
        
        return CONTRACT_SIGNED
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED


async def contract_signed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка подтверждения договора и переход к выбору исполнителей"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'cancel_connection':
        return await cancel_connection(update, context)
    
    # Сохраняем подтверждение договора
    if 'connection_data' not in context.user_data:
        context.user_data['connection_data'] = {}
    context.user_data['connection_data']['contract_signed'] = True
    
    # Получаем список сотрудников
    db = Database()
    employees = db.get_all_employees()
    
    if not employees:
        await query.edit_message_text(
            "⚠️ В системе нет ни одного сотрудника!\n\n"
            "Обратитесь к администратору для добавления сотрудников.",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выберите действие:",
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
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        "✅ <b>Договор подписан</b>\n\n"
        "👥 <b>Шаг 11/11: Выбор исполнителей</b>\n\n"
        "Выберите сотрудников, которые участвовали в подключении:\n"
        "(можно выбрать нескольких)",
        parse_mode='HTML'
    )
    
    # Отправляем сообщение с inline-клавиатурой
    await query.message.reply_text(
        "Нажмите ✅ Готово после выбора:",
        reply_markup=reply_markup
    )
    
    return SELECT_EMPLOYEES

