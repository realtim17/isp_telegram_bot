"""
Обработчики для управления сотрудниками
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    is_admin, MANAGE_ACTION, ADD_EMPLOYEE_NAME, DELETE_EMPLOYEE_SELECT,
    SELECT_EMPLOYEE_FOR_MATERIAL, SELECT_MATERIAL_ACTION, 
    ENTER_FIBER_AMOUNT, ENTER_TWISTED_AMOUNT,
    SELECT_EMPLOYEE_FOR_ROUTER, SELECT_ROUTER_ACTION,
    ENTER_ROUTER_NAME, ENTER_ROUTER_QUANTITY
)
from utils.keyboards import get_main_keyboard


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
        [InlineKeyboardButton("📦 Управление материалами", callback_data='manage_materials')],
        [InlineKeyboardButton("📡 Управление роутерами", callback_data='manage_routers')],
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


async def manage_action(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
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
            [InlineKeyboardButton("📦 Управление материалами", callback_data='manage_materials')],
            [InlineKeyboardButton("📡 Управление роутерами", callback_data='manage_routers')],
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
    
    if query.data == 'manage_materials':
        employees = db.get_all_employees()
        
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        
        keyboard = []
        for emp in employees:
            fiber = emp.get('fiber_balance', 0) or 0
            twisted = emp.get('twisted_pair_balance', 0) or 0
            keyboard.append([InlineKeyboardButton(
                f"📦 {emp['full_name']} (ВОЛС: {fiber}м, ВП: {twisted}м)",
                callback_data=f"mat_emp_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_manage')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📦 <b>Управление материалами</b>\n\n"
            "Выберите сотрудника:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return SELECT_EMPLOYEE_FOR_MATERIAL
    
    if query.data == 'manage_routers':
        employees = db.get_all_employees()
        
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END
        
        keyboard = []
        for emp in employees:
            routers = db.get_employee_routers(emp['id'])
            router_count = sum(r['quantity'] for r in routers)
            router_text = f"{router_count} шт." if router_count > 0 else "нет"
            keyboard.append([InlineKeyboardButton(
                f"📡 {emp['full_name']} ({router_text})",
                callback_data=f"rtr_emp_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_manage')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📡 <b>Управление роутерами</b>\n\n"
            "Выберите сотрудника:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return SELECT_EMPLOYEE_FOR_ROUTER
    
    if query.data == 'manage_list':
        employees = db.get_all_employees()
        
        if not employees:
            text = "📋 <b>Список сотрудников</b>\n\nСписок пуст."
        else:
            emp_lines = []
            for idx, emp in enumerate(employees, 1):
                fiber = emp.get('fiber_balance', 0) or 0
                twisted = emp.get('twisted_pair_balance', 0) or 0
                emp_lines.append(
                    f"{idx}. {emp['full_name']}\n"
                    f"   📦 ВОЛС: {fiber}м | Витая пара: {twisted}м"
                )
            emp_list = '\n\n'.join(emp_lines)
            text = f"📋 <b>Список сотрудников ({len(employees)}):</b>\n\n{emp_list}"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data='back_to_manage')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
        return MANAGE_ACTION


async def add_employee_name(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
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


async def delete_employee_confirm(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
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


async def select_employee_for_material(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор сотрудника для управления материалами"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back_to_manage':
        return await manage_action(update, context, db)
    
    emp_id = int(query.data.split('_')[2])
    employee = db.get_employee_by_id(emp_id)
    
    if not employee:
        await query.edit_message_text("❌ Сотрудник не найден.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    # Сохраняем ID сотрудника в контексте
    context.user_data['selected_employee_id'] = emp_id
    
    fiber = employee.get('fiber_balance', 0) or 0
    twisted = employee.get('twisted_pair_balance', 0) or 0
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить материалы", callback_data='mat_action_add')],
        [InlineKeyboardButton("➖ Списать материалы", callback_data='mat_action_deduct')],
        [InlineKeyboardButton("◀️ Назад", callback_data='mat_back_to_list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = f"""
📦 <b>Управление материалами</b>

👤 <b>Сотрудник:</b> {employee['full_name']}

📊 <b>Текущий баланс:</b>
  • ВОЛС: {fiber} м
  • Витая пара: {twisted} м

Выберите действие:
"""
    
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    return SELECT_MATERIAL_ACTION


async def select_material_action(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор действия с материалами"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'mat_back_to_list':
        # Возврат к списку сотрудников
        employees = db.get_all_employees()
        keyboard = []
        for emp in employees:
            fiber = emp.get('fiber_balance', 0) or 0
            twisted = emp.get('twisted_pair_balance', 0) or 0
            keyboard.append([InlineKeyboardButton(
                f"📦 {emp['full_name']} (ВОЛС: {fiber}м, ВП: {twisted}м)",
                callback_data=f"mat_emp_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_manage')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📦 <b>Управление материалами</b>\n\n"
            "Выберите сотрудника:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return SELECT_EMPLOYEE_FOR_MATERIAL
    
    emp_id = context.user_data.get('selected_employee_id')
    employee = db.get_employee_by_id(emp_id)
    
    if query.data == 'mat_action_add':
        context.user_data['material_action'] = 'add'
        await query.edit_message_text(
            f"➕ <b>Добавление материалов</b>\n\n"
            f"👤 Сотрудник: {employee['full_name']}\n\n"
            f"Введите количество метров <b>ВОЛС</b> для добавления:\n"
            f"(Введите 0, если не нужно добавлять)",
            parse_mode='HTML'
        )
        return ENTER_FIBER_AMOUNT
    
    if query.data == 'mat_action_deduct':
        context.user_data['material_action'] = 'deduct'
        await query.edit_message_text(
            f"➖ <b>Списание материалов</b>\n\n"
            f"👤 Сотрудник: {employee['full_name']}\n\n"
            f"Введите количество метров <b>ВОЛС</b> для списания:\n"
            f"(Введите 0, если не нужно списывать)",
            parse_mode='HTML'
        )
        return ENTER_FIBER_AMOUNT
    
    return SELECT_MATERIAL_ACTION


async def enter_fiber_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод количества ВОЛС"""
    try:
        fiber_amount = float(update.message.text.strip().replace(',', '.'))
        if fiber_amount < 0:
            raise ValueError
        
        context.user_data['fiber_amount'] = fiber_amount
        
        emp_id = context.user_data.get('selected_employee_id')
        employee = db.get_employee_by_id(emp_id)
        action = context.user_data.get('material_action')
        action_text = "добавления" if action == 'add' else "списания"
        
        await update.message.reply_text(
            f"✅ ВОЛС: {fiber_amount} м\n\n"
            f"Теперь введите количество метров <b>витой пары</b> для {action_text}:\n"
            f"(Введите 0, если не нужно)",
            parse_mode='HTML'
        )
        return ENTER_TWISTED_AMOUNT
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_FIBER_AMOUNT


async def enter_twisted_amount(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод количества витой пары и выполнение операции"""
    try:
        twisted_amount = float(update.message.text.strip().replace(',', '.'))
        if twisted_amount < 0:
            raise ValueError
        
        emp_id = context.user_data.get('selected_employee_id')
        fiber_amount = context.user_data.get('fiber_amount', 0)
        action = context.user_data.get('material_action')
        
        employee = db.get_employee_by_id(emp_id)
        
        if action == 'add':
            success = db.add_material_to_employee(emp_id, fiber_amount, twisted_amount)
            if success:
                updated_emp = db.get_employee_by_id(emp_id)
                new_fiber = updated_emp.get('fiber_balance', 0) or 0
                new_twisted = updated_emp.get('twisted_pair_balance', 0) or 0
                
                await update.message.reply_text(
                    f"✅ <b>Материалы добавлены!</b>\n\n"
                    f"👤 Сотрудник: {employee['full_name']}\n\n"
                    f"➕ Добавлено:\n"
                    f"  • ВОЛС: +{fiber_amount} м\n"
                    f"  • Витая пара: +{twisted_amount} м\n\n"
                    f"📊 Новый баланс:\n"
                    f"  • ВОЛС: {new_fiber} м\n"
                    f"  • Витая пара: {new_twisted} м",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при добавлении материалов.",
                    reply_markup=get_main_keyboard()
                )
        else:  # deduct
            success = db.deduct_material_from_employee(emp_id, fiber_amount, twisted_amount)
            if success:
                updated_emp = db.get_employee_by_id(emp_id)
                new_fiber = updated_emp.get('fiber_balance', 0) or 0
                new_twisted = updated_emp.get('twisted_pair_balance', 0) or 0
                
                await update.message.reply_text(
                    f"✅ <b>Материалы списаны!</b>\n\n"
                    f"👤 Сотрудник: {employee['full_name']}\n\n"
                    f"➖ Списано:\n"
                    f"  • ВОЛС: -{fiber_amount} м\n"
                    f"  • Витая пара: -{twisted_amount} м\n\n"
                    f"📊 Новый баланс:\n"
                    f"  • ВОЛС: {new_fiber} м\n"
                    f"  • Витая пара: {new_twisted} м",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
            else:
                old_fiber = employee.get('fiber_balance', 0) or 0
                old_twisted = employee.get('twisted_pair_balance', 0) or 0
                await update.message.reply_text(
                    f"❌ <b>Недостаточно материалов!</b>\n\n"
                    f"👤 Сотрудник: {employee['full_name']}\n\n"
                    f"📊 Текущий баланс:\n"
                    f"  • ВОЛС: {old_fiber} м\n"
                    f"  • Витая пара: {old_twisted} м\n\n"
                    f"❗ Требуется:\n"
                    f"  • ВОЛС: {fiber_amount} м\n"
                    f"  • Витая пара: {twisted_amount} м",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
        
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
        )
        return ENTER_TWISTED_AMOUNT


# ==================== УПРАВЛЕНИЕ РОУТЕРАМИ ====================

async def select_employee_for_router(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор сотрудника для управления роутерами"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'back_to_manage':
        return await manage_employees_start(update, context)
    
    # Извлекаем ID сотрудника
    emp_id = int(query.data.split('_')[-1])
    context.user_data['selected_employee_id'] = emp_id
    
    employee = db.get_employee_by_id(emp_id)
    routers = db.get_employee_routers(emp_id)
    
    # Формируем текст с роутерами
    router_text = ""
    if routers:
        for router in routers:
            router_text += f"  • {router['router_name']}: {router['quantity']} шт.\n"
    else:
        router_text = "  Роутеров нет\n"
    
    keyboard = [
        [InlineKeyboardButton("➕ Добавить роутеры", callback_data='rtr_action_add')],
        [InlineKeyboardButton("➖ Списать роутер", callback_data='rtr_action_deduct')],
        [InlineKeyboardButton("◀️ Назад", callback_data='rtr_back_to_list')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"📡 <b>Роутеры сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущие роутеры:\n{router_text}\n"
        f"Выберите действие:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_ROUTER_ACTION


async def select_router_action(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор действия с роутерами"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'rtr_back_to_list':
        # Возврат к списку сотрудников
        employees = db.get_all_employees()
        keyboard = []
        for emp in employees:
            routers = db.get_employee_routers(emp['id'])
            router_count = sum(r['quantity'] for r in routers)
            router_text = f"{router_count} шт." if router_count > 0 else "нет"
            keyboard.append([InlineKeyboardButton(
                f"📡 {emp['full_name']} ({router_text})",
                callback_data=f"rtr_emp_{emp['id']}"
            )])
        
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data='back_to_manage')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "📡 <b>Управление роутерами</b>\n\n"
            "Выберите сотрудника:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        return SELECT_EMPLOYEE_FOR_ROUTER
    
    action = query.data.split('_')[-1]  # add или deduct
    context.user_data['router_action'] = action
    
    if action == 'add':
        # Предлагаем выбор из популярных моделей или ручной ввод
        keyboard = [
            [InlineKeyboardButton("📡 SNR AX 2", callback_data='router_model_SNR AX 2')],
            [InlineKeyboardButton("📡 TP-Link AX 12", callback_data='router_model_TP-Link AX 12')],
            [InlineKeyboardButton("📡 Keenetic Speedster", callback_data='router_model_Keenetic Speedster')],
            [InlineKeyboardButton("✏️ Ввести вручную", callback_data='router_model_manual')],
            [InlineKeyboardButton("❌ Отмена", callback_data='manage_cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➕ <b>Добавление роутеров</b>\n\n"
            "Выберите модель роутера или введите свою:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    else:  # deduct
        emp_id = context.user_data.get('selected_employee_id')
        routers = db.get_employee_routers(emp_id)
        
        if not routers:
            await query.edit_message_text("⚠️ У сотрудника нет роутеров для списания.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            context.user_data.clear()
            return ConversationHandler.END
        
        keyboard = []
        for router in routers:
            keyboard.append([InlineKeyboardButton(
                f"{router['router_name']} ({router['quantity']} шт.)",
                callback_data=f"deduct_router_{router['id']}"
            )])
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='manage_cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "➖ <b>Списание роутера</b>\n\n"
            "Выберите роутер для списания:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        # Остаёмся в том же состоянии для обработки выбора роутера
        return SELECT_ROUTER_ACTION
    
    return ENTER_ROUTER_NAME


async def enter_router_name(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод названия роутера"""
    # Проверяем, это callback или текстовое сообщение
    if update.callback_query:
        query = update.callback_query
        await query.answer()
        
        # Проверяем, это выбор модели или списание
        if query.data.startswith('router_model_'):
            # Выбор модели роутера при добавлении
            if query.data == 'router_model_manual':
                # Ручной ввод
                await query.edit_message_text(
                    "➕ <b>Добавление роутеров</b>\n\n"
                    "Введите название роутера:",
                    parse_mode='HTML'
                )
                return ENTER_ROUTER_NAME
            else:
                # Выбрана одна из предложенных моделей
                router_name = query.data.replace('router_model_', '')
                context.user_data['router_name'] = router_name
                
                await query.edit_message_text(
                    f"➕ <b>Добавление роутеров</b>\n\n"
                    f"Модель: {router_name}\n\n"
                    f"Введите количество роутеров:",
                    parse_mode='HTML'
                )
                return ENTER_ROUTER_QUANTITY
        
        # Это выбор роутера для списания
        router_id = int(query.data.split('_')[-1])
        emp_id = context.user_data.get('selected_employee_id')
        
        # Получаем информацию о роутере
        routers = db.get_employee_routers(emp_id)
        selected_router = next((r for r in routers if r['id'] == router_id), None)
        
        if not selected_router:
            await query.edit_message_text("❌ Роутер не найден.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            context.user_data.clear()
            return ConversationHandler.END
        
        # Сохраняем информацию о роутере и запрашиваем количество
        context.user_data['router_name'] = selected_router['router_name']
        context.user_data['router_action'] = 'deduct'
        
        await query.edit_message_text(
            f"➖ <b>Списание роутера</b>\n\n"
            f"📡 Роутер: {selected_router['router_name']}\n"
            f"📊 Доступно: {selected_router['quantity']} шт.\n\n"
            f"Введите количество для списания (целое число):",
            parse_mode='HTML'
        )
        
        return ENTER_ROUTER_QUANTITY
    
    # Это ввод названия нового роутера
    router_name = update.message.text.strip()
    context.user_data['router_name'] = router_name
    
    await update.message.reply_text(
        f"✅ Роутер: {router_name}\n\n"
        f"Введите количество (целое число):",
        parse_mode='HTML'
    )
    
    return ENTER_ROUTER_QUANTITY


async def enter_router_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Ввод количества роутеров"""
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError
        
        emp_id = context.user_data.get('selected_employee_id')
        router_name = context.user_data.get('router_name')
        action = context.user_data.get('router_action')
        
        employee = db.get_employee_by_id(emp_id)
        
        if action == 'add':
            success = db.add_router_to_employee(emp_id, router_name, quantity, created_by=update.effective_user.id)
            if success:
                new_quantity = db.get_router_quantity(emp_id, router_name)
                await update.message.reply_text(
                    f"✅ <b>Роутеры добавлены!</b>\n\n"
                    f"👤 Сотрудник: {employee['full_name']}\n"
                    f"📡 Роутер: {router_name}\n"
                    f"➕ Добавлено: {quantity} шт.\n"
                    f"📊 Всего: {new_quantity} шт.",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при добавлении роутеров.",
                    reply_markup=get_main_keyboard()
                )
        else:  # deduct
            success = db.deduct_router_from_employee(emp_id, router_name, quantity, created_by=update.effective_user.id)
            if success:
                new_quantity = db.get_router_quantity(emp_id, router_name)
                await update.message.reply_text(
                    f"✅ <b>Роутеры списаны!</b>\n\n"
                    f"👤 Сотрудник: {employee['full_name']}\n"
                    f"📡 Роутер: {router_name}\n"
                    f"➖ Списано: {quantity} шт.\n"
                    f"📊 Осталось: {new_quantity} шт.",
                    parse_mode='HTML',
                    reply_markup=get_main_keyboard()
                )
            else:
                await update.message.reply_text(
                    "❌ Ошибка при списании роутеров (недостаточно в наличии).",
                    reply_markup=get_main_keyboard()
                )
        
        context.user_data.clear()
        return ConversationHandler.END
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное целое число (например: 5)"
        )
        return ENTER_ROUTER_QUANTITY


# ==================== СПИСОК СОТРУДНИКОВ ====================

async def show_employees_list(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> None:
    """Показать список всех сотрудников с их материалами"""
    employees = db.get_all_employees()
    
    if not employees:
        await update.message.reply_text(
            "📋 <b>Список сотрудников пуст</b>\n\n"
            "Добавьте сотрудников через меню\n"
            "👥 Управление сотрудниками → ➕ Добавить сотрудника",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        return
    
    # Формируем сообщение со списком сотрудников
    message = "👤 <b>Список сотрудников</b>\n\n"
    
    for idx, emp in enumerate(employees, 1):
        emp_name = emp['full_name']
        fiber_balance = emp.get('fiber_balance', 0) or 0
        twisted_balance = emp.get('twisted_pair_balance', 0) or 0
        
        # Получаем роутеры сотрудника
        routers = db.get_employee_routers(emp['id'])
        router_count = sum(r['quantity'] for r in routers)
        
        message += f"{idx}. <b>{emp_name}</b>\n"
        message += f"   📦 Материалы:\n"
        message += f"   • ВОЛС: {fiber_balance} м\n"
        message += f"   • Витая пара: {twisted_balance} м\n"
        message += f"   📡 Роутеры: {router_count} шт.\n"
        
        # Показываем детали по роутерам
        if routers:
            message += "   Модели:\n"
            for router in routers:
                message += f"   • {router['router_name']}: {router['quantity']} шт.\n"
        
        message += "\n"
    
    message += "━━━━━━━━━━━━━━━━━━━━━━\n"
    message += f"<b>Всего сотрудников:</b> {len(employees)}"
    
    await update.message.reply_text(
        message,
        parse_mode='HTML',
        reply_markup=get_main_keyboard()
    )

