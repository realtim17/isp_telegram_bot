"""
Добавление и удаление сотрудников
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import get_main_keyboard
from config import ADD_EMPLOYEE_NAME


async def add_employee_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавляет нового сотрудника"""
    full_name = update.message.text.strip()

    if len(full_name) < 3:
        await update.message.reply_text(
            "⚠️ ФИО должно содержать минимум 3 символа. Попробуйте еще раз:"
        )
        return ADD_EMPLOYEE_NAME

    employee_id = flow.db.add_employee(full_name)

    if employee_id:
        await update.message.reply_text(
            f"✅ Сотрудник <b>{full_name}</b> успешно добавлен!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
    else:
        await update.message.reply_text(
            f"⚠️ Сотрудник <b>{full_name}</b> уже существует в системе!",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )

    return ConversationHandler.END


async def delete_employee_confirm(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждает удаление сотрудника"""
    query = update.callback_query
    await query.answer()

    if query.data == "delete_cancel":
        await query.edit_message_text("❌ Удаление отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    emp_id = int(query.data.split("_")[2])
    employee = flow.db.get_employee_by_id(emp_id)

    if flow.db.delete_employee(emp_id):
        await query.edit_message_text(
            f"✅ Сотрудник <b>{employee['full_name']}</b> удален!",
            parse_mode="HTML",
        )
    else:
        await query.edit_message_text("❌ Ошибка при удалении сотрудника.")

    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END
