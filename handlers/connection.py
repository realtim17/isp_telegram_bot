"""
Обработчики для создания подключений
"""
from datetime import datetime

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from config import (
    SELECT_CONNECTION_TYPE, UPLOAD_PHOTOS, ENTER_ADDRESS, SELECT_ROUTER, ENTER_PORT,
    ENTER_FIBER, ENTER_TWISTED, SELECT_EMPLOYEES, SELECT_MATERIAL_PAYER, SELECT_ROUTER_PAYER, CONFIRM, CONNECTION_TYPES,
    logger
)
from utils.keyboards import get_main_keyboard
from utils.helpers import send_connection_report
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
🏢 <b>Шаг 1/8: Тип подключения</b>

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
    conn_type = query.data.split('_')[-1]  # mkd, chs, или legal
    context.user_data['connection_data']['connection_type'] = conn_type
    
    # Получаем читаемое название
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    text = f"""
✅ Тип подключения: <b>{type_name}</b>

📸 <b>Шаг 2/8: Загрузка фотографий</b>

Загрузите фотографии с места подключения (до 10 штук).
После загрузки фото нажмите "Продолжить".

📋 <b>Фотоотчет ОБЯЗАТЕЛЬНО должен содержать:</b>

1️⃣ Маршрут линии
2️⃣ ОРК (разварка) / Коммутатор (порт)
3️⃣ Место входа (сверление в помещение)
4️⃣ Внутренняя укладка в помещении, если есть
5️⃣ Места установки WiFi роутера, оконечивание провода
6️⃣ Замер скорости, если есть
7️⃣ Настройки роутера, если есть

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
        
        if len(photos) >= 10:
            await update.message.reply_text("⚠️ Достигнут лимит в 10 фотографий.")
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
                f"✅ Фото {len(photos)}/10 загружено.\n\n"
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
                    text=f"✅ Фото {len(photos)}/10 загружено.\n\n"
                         f"Можете загрузить еще фото или нажмите 'Продолжить'.",
                    reply_markup=reply_markup
                )
            except Exception as e:
                # Если не удалось отредактировать (например, сообщение удалено), отправляем новое
                sent_message = await update.message.reply_text(
                    f"✅ Фото {len(photos)}/10 загружено.\n\n"
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
        f"📍 <b>Шаг 3/8: Адрес подключения</b>\n\n"
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
    
    if not router_names:
        # Если роутеров нет, предлагаем ввести вручную
        # Оставляем клавиатуру отмены для ввода вручную
        await update.message.reply_text(
            f"✅ Адрес: {address}\n\n"
            f"🌐 <b>Шаг 4/8: Модель роутера</b>\n\n"
            f"⚠️ В системе нет зарегистрированных роутеров.\n"
            f"Введите модель роутера вручную:",
            parse_mode='HTML'
        )
        return SELECT_ROUTER
    
    # Создаём клавиатуру с роутерами
    keyboard = []
    for router_name in router_names:
        keyboard.append([InlineKeyboardButton(
            f"📡 {router_name}",
            callback_data=f"select_router_{router_name}"
        )])
    
    keyboard.append([InlineKeyboardButton("✏️ Ввести вручную", callback_data='router_manual')])
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Убираем клавиатуру отмены и показываем inline-клавиатуру
    await update.message.reply_text(
        f"✅ Адрес: {address}\n\n"
        f"🌐 <b>Шаг 4/8: Модель роутера</b>\n\n"
        f"Выберите роутер из списка или введите вручную:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_ROUTER


async def select_router(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора роутера или ввод вручную"""
    # Если это callback (выбор из списка)
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        if query.data == 'router_manual':
            # Ввод вручную - добавляем клавиатуру отмены
            keyboard = [[KeyboardButton("❌ Отмена")]]
            reply_markup_kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
            
            await query.edit_message_text(
                "🌐 <b>Шаг 4/8: Модель роутера</b>\n\n"
                "Введите модель роутера:",
                parse_mode='HTML'
            )
            
            await query.message.reply_text(
                "Для отмены нажмите кнопку ниже:",
                reply_markup=reply_markup_kb
            )
            return SELECT_ROUTER
        
        # Выбран роутер из списка
        router_name = query.data.replace('select_router_', '')
        
        if 'connection_data' not in context.user_data:
            context.user_data['connection_data'] = {}
        
        context.user_data['connection_data']['router_model'] = router_name
        
        # Добавляем клавиатуру отмены для ввода порта
        keyboard = [[KeyboardButton("❌ Отмена")]]
        reply_markup_kb = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
        
        await query.edit_message_text(
            f"✅ Роутер: {router_name}\n\n"
            f"🔌 <b>Шаг 5/8: Номер порта</b>\n\n"
            f"Введите номер порта:",
            parse_mode='HTML'
        )
        
        await query.message.reply_text(
            "Для отмены нажмите кнопку ниже:",
            reply_markup=reply_markup_kb
        )
        
        return ENTER_PORT
    
    # Если это текстовое сообщение (ввод вручную)
    router = update.message.text.strip()
    
    # Проверяем отмену
    if router == "❌ Отмена":
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
    
    context.user_data['connection_data']['router_model'] = router
    
    # Клавиатура отмены уже есть, просто переходим к следующему шагу
    await update.message.reply_text(
        f"✅ Роутер: {router}\n\n"
        f"🔌 <b>Шаг 5/8: Номер порта</b>\n\n"
        f"Введите номер порта:",
        parse_mode='HTML'
    )
    
    return ENTER_PORT


async def enter_port(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Сохранение порта и запрос метража ВОЛС"""
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
    
    await update.message.reply_text(
        f"✅ Порт: {port}\n\n"
        f"📏 <b>Шаг 6/8: Метраж ВОЛС</b>\n\n"
        f"Введите количество метров ВОЛС (волоконно-оптической линии связи):",
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
            f"📏 <b>Шаг 7/8: Метраж витой пары</b>\n\n"
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
        
        # Получаем список сотрудников
        db = Database()
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
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Убираем reply-клавиатуру и показываем inline-клавиатуру
        await update.message.reply_text(
            f"✅ Витая пара: {twisted_meters} м\n\n"
            f"👥 <b>Шаг 8/8: Выбор исполнителей</b>\n\n"
            f"Выберите сотрудников, которые участвовали в подключении:\n"
            f"(можно выбрать нескольких)",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )
        
        # Отправляем сообщение с inline-клавиатурой
        await update.message.reply_text(
            "Нажмите ✅ Готово после выбора:",
            reply_markup=reply_markup
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
        
        # Проверяем балансы и определяем, кто будет платить за материалы
        db = Database()
        return await check_materials_and_proceed(update, context, db)
    
    # Переключаем выбор сотрудника
    emp_id = int(query.data.split('_')[1])
    selected = context.user_data.get('selected_employees', [])
    
    if emp_id in selected:
        selected.remove(emp_id)
    else:
        selected.append(emp_id)
    
    context.user_data['selected_employees'] = selected
    
    # Обновляем клавиатуру
    db = Database()
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
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    try:
        await query.edit_message_reply_markup(reply_markup=reply_markup)
    except Exception:
        pass
    
    return SELECT_EMPLOYEES


async def check_materials_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить балансы материалов и определить плательщика"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    fiber_meters = data['fiber_meters']
    twisted_pair_meters = data['twisted_pair_meters']
    
    # Получаем балансы всех выбранных сотрудников
    employees_with_balance = []
    for emp_id in selected_employees:
        emp = db.get_employee_by_id(emp_id)
        if emp:
            fiber_balance = emp.get('fiber_balance', 0) or 0
            twisted_balance = emp.get('twisted_pair_balance', 0) or 0
            has_enough = (fiber_balance >= fiber_meters and twisted_balance >= twisted_pair_meters)
            employees_with_balance.append({
                'id': emp_id,
                'name': emp['full_name'],
                'fiber': fiber_balance,
                'twisted': twisted_balance,
                'has_enough': has_enough
            })
    
    # Определяем, у кого есть достаточно материалов
    employees_with_enough = [e for e in employees_with_balance if e['has_enough']]
    
    if len(employees_with_enough) == 0:
        # Ни у кого нет достаточно материалов
        emp_list = '\n'.join([
            f"• {e['name']}: ВОЛС {e['fiber']}м, ВП {e['twisted']}м"
            for e in employees_with_balance
        ])
        
        await query.edit_message_text(
            f"❌ <b>Недостаточно материалов!</b>\n\n"
            f"Требуется:\n"
            f"• ВОЛС: {fiber_meters} м\n"
            f"• Витая пара: {twisted_pair_meters} м\n\n"
            f"Балансы исполнителей:\n{emp_list}\n\n"
            f"Добавьте материалы через:\n"
            f"Управление сотрудниками → Управление материалами",
            parse_mode='HTML'
        )
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    elif len(employees_with_enough) == 1:
        # Только у одного есть материалы - списываем с него автоматически
        context.user_data['material_payer_id'] = employees_with_enough[0]['id']
        # Переходим к проверке роутеров
        return await check_routers_and_proceed(update, context, db)
    
    else:
        # У нескольких есть материалы - предлагаем выбрать
        keyboard = []
        for emp in employees_with_enough:
            keyboard.append([InlineKeyboardButton(
                f"💰 {emp['name']} (ВОЛС: {emp['fiber']}м, ВП: {emp['twisted']}м)",
                callback_data=f"payer_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"💰 <b>Выбор плательщика материалов</b>\n\n"
            f"Требуется:\n"
            f"• ВОЛС: {fiber_meters} м\n"
            f"• Витая пара: {twisted_pair_meters} м\n\n"
            f"У нескольких исполнителей есть достаточно материалов.\n"
            f"Выберите, с кого списать материалы:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return SELECT_MATERIAL_PAYER


async def select_material_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора плательщика материалов"""
    query = update.callback_query
    await query.answer()
    
    payer_id = int(query.data.split('_')[1])
    context.user_data['material_payer_id'] = payer_id
    
    db = Database()
    # Переходим к проверке роутеров
    return await check_routers_and_proceed(update, context, db)


async def check_routers_and_proceed(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Проверить наличие роутеров и определить плательщика"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    selected_employees = context.user_data.get('selected_employees', [])
    router_model = data['router_model']
    
    # Получаем информацию о роутерах у сотрудников
    employees_with_router = []
    for emp_id in selected_employees:
        emp = db.get_employee_by_id(emp_id)
        if emp:
            router_quantity = db.get_router_quantity(emp_id, router_model)
            has_router = router_quantity > 0
            employees_with_router.append({
                'id': emp_id,
                'name': emp['full_name'],
                'quantity': router_quantity,
                'has_router': has_router
            })
    
    # Определяем, у кого есть роутер
    employees_with_enough = [e for e in employees_with_router if e['has_router']]
    
    if len(employees_with_enough) == 0:
        # Ни у кого нет роутера - это нормально, переходим к подтверждению
        context.user_data['router_payer_id'] = None
        return await show_confirmation(update, context, db)
    
    elif len(employees_with_enough) == 1:
        # Только у одного есть роутер - списываем с него автоматически
        context.user_data['router_payer_id'] = employees_with_enough[0]['id']
        return await show_confirmation(update, context, db)
    
    else:
        # У нескольких есть роутер - предлагаем выбрать
        keyboard = []
        for emp in employees_with_enough:
            keyboard.append([InlineKeyboardButton(
                f"📡 {emp['name']} ({emp['quantity']} шт.)",
                callback_data=f"router_payer_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            f"📡 <b>Выбор плательщика роутера</b>\n\n"
            f"Роутер: {router_model}\n\n"
            f"У нескольких исполнителей есть этот роутер.\n"
            f"Выберите, с кого списать роутер:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        return SELECT_ROUTER_PAYER


async def select_router_payer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора плательщика роутера"""
    query = update.callback_query
    await query.answer()
    
    payer_id = int(query.data.split('_')[-1])
    context.user_data['router_payer_id'] = payer_id
    
    db = Database()
    return await show_confirmation(update, context, db)


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Показать подтверждение перед сохранением"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    
    # Получаем имена выбранных сотрудников
    employees = db.get_all_employees()
    employee_names = [emp['full_name'] for emp in employees if emp['id'] in selected_employees]
    
    # Получаем читаемое название типа подключения
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    # Рассчитываем долю на каждого (для отчёта)
    emp_count = len(selected_employees)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
    
    # Получаем информацию о плательщиках
    material_payer_id = context.user_data.get('material_payer_id')
    router_payer_id = context.user_data.get('router_payer_id')
    
    payer_info = ""
    if material_payer_id:
        payer = db.get_employee_by_id(material_payer_id)
        if payer:
            payer_info += f"\n\n💰 <b>Материалы списываются с:</b> {payer['full_name']}"
    
    if router_payer_id:
        router_payer = db.get_employee_by_id(router_payer_id)
        if router_payer:
            payer_info += f"\n📡 <b>Роутер списывается с:</b> {router_payer['full_name']}"
    
    confirmation_text = f"""
📋 <b>Подтверждение данных</b>

🏢 <b>Тип:</b> {type_name}
📍 <b>Адрес:</b> {data['address']}
🌐 <b>Роутер:</b> {data['router_model']}
🔌 <b>Порт:</b> {data['port']}

📏 <b>Метраж:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

👥 <b>Исполнители ({emp_count}):</b>
{chr(10).join([f"  • {name}" for name in employee_names])}

<b>Метраж на каждого (для зарплаты):</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м{payer_info}

📸 <b>Фото:</b> {len(photos)} шт.

Всё верно? Подтвердите создание отчета.
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
    db = Database()
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    material_payer_id = context.user_data.get('material_payer_id')
    router_payer_id = context.user_data.get('router_payer_id')
    user_id = update.effective_user.id
    
    connection_id = db.create_connection(
        connection_type=data.get('connection_type', 'mkd'),
        address=data['address'],
        router_model=data['router_model'],
        port=data['port'],
        fiber_meters=data['fiber_meters'],
        twisted_pair_meters=data['twisted_pair_meters'],
        employee_ids=selected_employees,
        photo_file_ids=photos,
        created_by=user_id,
        material_payer_id=material_payer_id
    )
    
    if connection_id:
        # Списываем роутер, если указан плательщик
        if router_payer_id:
            router_model = data['router_model']
            success = db.deduct_router_from_employee(router_payer_id, router_model, 1)
            if success:
                logger.info(f"Роутер '{router_model}' списан с сотрудника ID {router_payer_id}")
            else:
                logger.warning(f"Не удалось списать роутер '{router_model}' с сотрудника ID {router_payer_id}")
        
        # Отправляем подтверждение
        await query.edit_message_text(
            f"✅ <b>Отчет успешно создан!</b>\n\n"
            f"ID подключения: #{connection_id}\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
        # Отправляем отчет с фотографиями
        await send_connection_report(query.message, connection_id, data, photos, selected_employees, db)
        
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


async def cancel_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена создания подключения через кнопку"""
    query = update.callback_query
    await query.answer()
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    await query.edit_message_text(
        "❌ <b>Создание подключения отменено</b>\n\n"
        "Все введённые данные удалены.\n"
        "Выберите действие из меню:",
        parse_mode='HTML'
    )
    
    # Отправляем главное меню
    await query.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    
    return ConversationHandler.END


async def cancel_by_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена при переходе в другой раздел через меню"""
    context.user_data.clear()
    await update.message.reply_text(
        "⚠️ <b>Создание подключения прервано</b>\n\n"
        "Вы перешли в другой раздел.\n"
        "Все несохранённые данные удалены.",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    return ConversationHandler.END


async def cancel_by_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена через команду /cancel"""
    context.user_data.clear()
    await update.message.reply_text(
        "❌ <b>Создание подключения отменено</b>\n\n"
        "Все введённые данные удалены.",
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    return ConversationHandler.END


# Создаем ConversationHandler для подключений
db = Database()

connection_conv = ConversationHandler(
    entry_points=[
        MessageHandler(filters.Regex('^📝 Новое подключение$'), new_connection_start),
        CallbackQueryHandler(new_connection_start, pattern='^start_new_connection$')
    ],
    states={
        SELECT_CONNECTION_TYPE: [
            CallbackQueryHandler(select_connection_type, pattern='^conn_type_'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
        ],
        UPLOAD_PHOTOS: [
            MessageHandler(filters.PHOTO, upload_photos),
            CallbackQueryHandler(ask_address, pattern='^continue_from_photos$'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
        ],
        ENTER_ADDRESS: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_address)
        ],
        SELECT_ROUTER: [
            CallbackQueryHandler(select_router, pattern='^(select_router_|router_manual)'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, select_router)
        ],
        ENTER_PORT: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_port)
        ],
        ENTER_FIBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_fiber)
        ],
        ENTER_TWISTED: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_twisted)
        ],
        SELECT_EMPLOYEES: [
            CallbackQueryHandler(select_employee_toggle, pattern='^(emp_.*|employees_done)$'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
        ],
        SELECT_MATERIAL_PAYER: [
            CallbackQueryHandler(select_material_payer, pattern='^payer_'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
        ],
        SELECT_ROUTER_PAYER: [
            CallbackQueryHandler(select_router_payer, pattern='^router_payer_'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
        ],
        CONFIRM: [
            CallbackQueryHandler(confirm_connection, pattern='^confirm_')
        ]
    },
    fallbacks=[
        MessageHandler(
            filters.Regex('^(📝 Новое подключение|📊 Сводный отчет|👥 Управление сотрудниками|ℹ️ Помощь)$'),
            cancel_by_menu
        ),
        MessageHandler(filters.COMMAND, cancel_by_command)
    ],
    name='connection_conversation',
    persistent=False
)
