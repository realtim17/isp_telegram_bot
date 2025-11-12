"""
Обработчики выбора исполнителей для подключения
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from config import SELECT_EMPLOYEES, logger
from database import Database


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
        from handlers.connection.validation import check_materials_and_proceed
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

