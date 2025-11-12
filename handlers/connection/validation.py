"""
Проверка наличия материалов и роутеров у исполнителей
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import SELECT_MATERIAL_PAYER, SELECT_ROUTER_PAYER
from utils.keyboards import get_main_keyboard
from database import Database


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
    required_quantity = data.get('router_quantity', 1)
    
    # Если роутер пропущен, сразу переходим к подтверждению
    if router_model == '-' or not router_model:
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)
    
    # Получаем информацию о роутерах у сотрудников
    employees_with_router = []
    for emp_id in selected_employees:
        emp = db.get_employee_by_id(emp_id)
        if emp:
            router_quantity = db.get_router_quantity(emp_id, router_model)
            has_enough = router_quantity >= required_quantity
            employees_with_router.append({
                'id': emp_id,
                'name': emp['full_name'],
                'quantity': router_quantity,
                'has_enough': has_enough
            })
    
    # Определяем, у кого есть достаточно роутеров
    employees_with_enough = [e for e in employees_with_router if e['has_enough']]
    
    if len(employees_with_enough) == 0:
        # Ни у кого нет достаточно роутеров
        emp_list = '\n'.join([
            f"• {e['name']}: {e['quantity']} шт."
            for e in employees_with_router
        ])
        
        quantity_text = f"{required_quantity} шт." if required_quantity > 1 else "1 шт."
        await query.edit_message_text(
            f"❌ <b>Недостаточно роутеров!</b>\n\n"
            f"Требуется роутер: <b>{router_model}</b> - {quantity_text}\n\n"
            f"Балансы исполнителей:\n{emp_list}\n\n"
            f"Добавьте роутеры через:\n"
            f"Управление сотрудниками → Управление роутерами",
            parse_mode='HTML'
        )
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    elif len(employees_with_enough) == 1:
        # Только у одного есть достаточно роутеров
        context.user_data['router_payer_id'] = employees_with_enough[0]['id']
        from handlers.connection.confirmation import show_confirmation
        return await show_confirmation(update, context, db)
    
    else:
        # У нескольких есть достаточно роутеров - предлагаем выбрать
        keyboard = []
        for emp in employees_with_enough:
            keyboard.append([InlineKeyboardButton(
                f"📡 {emp['name']} ({emp['quantity']} шт.)",
                callback_data=f"router_payer_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='cancel_connection')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        quantity_text = f"{required_quantity} шт." if required_quantity > 1 else "1 шт."
        await query.edit_message_text(
            f"📡 <b>Выбор плательщика роутера</b>\n\n"
            f"Роутер: {router_model} - {quantity_text}\n\n"
            f"У нескольких исполнителей есть достаточно роутеров.\n"
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
    from handlers.connection.confirmation import show_confirmation
    return await show_confirmation(update, context, db)

