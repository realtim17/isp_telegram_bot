"""
Стартовые обработчики управления сотрудниками
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    is_admin,
    MANAGE_ACTION,
    ADD_EMPLOYEE_NAME,
    DELETE_EMPLOYEE_SELECT,
    SELECT_EMPLOYEE_FOR_MATERIAL,
    SELECT_MATERIAL_ACTION,
    SELECT_EMPLOYEE_FOR_ROUTER,
    logger,
)
from utils.keyboards import get_main_keyboard


async def manage_employees_start(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с управлением сотрудниками"""
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
        [InlineKeyboardButton("➕ Добавить сотрудника", callback_data="manage_add")],
        [InlineKeyboardButton("➖ Удалить сотрудника", callback_data="manage_delete")],
        [InlineKeyboardButton("📦 Управление материалами", callback_data="manage_materials")],
        [InlineKeyboardButton("📡 Управление роутерами", callback_data="manage_routers")],
        [InlineKeyboardButton("📋 Список сотрудников", callback_data="manage_list")],
        [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = "👥 <b>Управление сотрудниками</b>\n\nВыберите действие:"

    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode="HTML")

    return MANAGE_ACTION


async def manage_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбранного действия"""
    query = update.callback_query
    await query.answer()

    data = query.data

    if data == "manage_cancel":
        await query.edit_message_text("❌ Управление сотрудниками отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END

    if data == "back_to_manage":
        return await manage_employees_start(flow, update, context)

    if data == "manage_add":
        await query.edit_message_text(
            "➕ <b>Добавление сотрудника</b>\n\nВведите ФИО сотрудника:",
            parse_mode="HTML",
        )
        return ADD_EMPLOYEE_NAME

    if data == "manage_delete":
        employees = flow.db.get_all_employees()
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников для удаления.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = [
            [InlineKeyboardButton(f"🗑 {emp['full_name']}", callback_data=f"del_emp_{emp['id']}")]
            for emp in employees
        ]
        keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="delete_cancel")])

        await query.edit_message_text(
            "➖ <b>Удаление сотрудника</b>\n\nВыберите сотрудника для удаления:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return DELETE_EMPLOYEE_SELECT

    if data == "manage_materials":
        employees = flow.db.get_all_employees()
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = []
        for emp in employees:
            fiber = emp.get("fiber_balance", 0) or 0
            twisted = emp.get("twisted_pair_balance", 0) or 0
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📦 {emp['full_name']} (ВОЛС: {fiber}м, ВП: {twisted}м)",
                        callback_data=f"mat_emp_{emp['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "📦 <b>Управление материалами</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_MATERIAL

    if data == "manage_routers":
        employees = flow.db.get_all_employees()
        if not employees:
            await query.edit_message_text("⚠️ В системе нет сотрудников.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            return ConversationHandler.END

        keyboard = []
        for emp in employees:
            routers = flow.db.get_employee_routers(emp["id"])
            router_count = sum(r["quantity"] for r in routers)
            router_text = f"{router_count} шт." if router_count > 0 else "нет"
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"📡 {emp['full_name']} ({router_text})",
                        callback_data=f"rtr_emp_{emp['id']}",
                    )
                ]
            )
        keyboard.append([InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")])

        await query.edit_message_text(
            "📡 <b>Управление роутерами</b>\n\nВыберите сотрудника:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return SELECT_EMPLOYEE_FOR_ROUTER

    if data == "manage_list":
        employees = flow.db.get_all_employees()
        if not employees:
            text = "📋 <b>Список сотрудников</b>\n\nСписок пуст."
        else:
            lines = []
            for idx, emp in enumerate(employees, 1):
                fiber = emp.get("fiber_balance", 0) or 0
                twisted = emp.get("twisted_pair_balance", 0) or 0
                lines.append(
                    f"{idx}. {emp['full_name']}\n"
                    f"   📦 ВОЛС: {fiber}м | Витая пара: {twisted}м"
                )
            text = f"📋 <b>Список сотрудников ({len(employees)}):</b>\n\n" + "\n\n".join(lines)

        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_to_manage")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")
        return MANAGE_ACTION

    logger.warning("Необработанное действие управления сотрудниками: %s", data)
    await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
    return ConversationHandler.END

