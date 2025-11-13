"""
Обработчики управления роутерами сотрудников
"""
from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, ConversationHandler

from config import (
    SELECT_EMPLOYEE_FOR_ROUTER,
    SELECT_ROUTER_ACTION,
    ENTER_ROUTER_NAME,
    ENTER_ROUTER_QUANTITY,
)
from utils.keyboards import get_main_keyboard


async def select_employee_for_router(
    flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE
) -> int:
    """Выбор сотрудника для операций с роутерами"""
    query = update.callback_query
    await query.answer()

    if query.data == "back_to_manage":
        from .start import manage_employees_start

        return await manage_employees_start(flow, update, context)

    emp_id = int(query.data.split("_")[-1])
    context.user_data["selected_employee_id"] = emp_id

    employee = flow.db.get_employee_by_id(emp_id)
    routers = flow.db.get_employee_routers(emp_id)

    router_text = ""
    if routers:
        for router in routers:
            router_text += f"  • {router['router_name']}: {router['quantity']} шт.\n"
    else:
        router_text = "  Роутеров нет\n"

    keyboard = [
        [InlineKeyboardButton("➕ Добавить роутеры", callback_data="rtr_action_add")],
        [InlineKeyboardButton("➖ Списать роутер", callback_data="rtr_action_deduct")],
        [InlineKeyboardButton("◀️ Назад", callback_data="rtr_back_to_list")],
    ]

    await query.edit_message_text(
        "📡 <b>Роутеры сотрудника</b>\n\n"
        f"👤 {employee['full_name']}\n\n"
        f"📊 Текущие роутеры:\n{router_text}\n"
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_ROUTER_ACTION


async def select_router_action(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора действия с роутером"""
    query = update.callback_query
    await query.answer()

    if query.data == "rtr_back_to_list":
        employees = flow.db.get_all_employees()
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

    action = query.data.split("_")[-1]
    context.user_data["router_action"] = action

    if action == "add":
        keyboard = [
            [InlineKeyboardButton("📡 SNR AX 2", callback_data="router_model_SNR AX 2")],
            [InlineKeyboardButton("📡 TP-Link AX 12", callback_data="router_model_TP-Link AX 12")],
            [InlineKeyboardButton("📡 Keenetic Speedster", callback_data="router_model_Keenetic Speedster")],
            [InlineKeyboardButton("✏️ Ввести вручную", callback_data="router_model_manual")],
            [InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")],
        ]
        await query.edit_message_text(
            "➕ <b>Добавление роутеров</b>\n\nВыберите модель роутера или введите свою:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return ENTER_ROUTER_NAME

    emp_id = context.user_data.get("selected_employee_id")
    routers = flow.db.get_employee_routers(emp_id)
    if not routers:
        await query.edit_message_text("⚠️ У сотрудника нет роутеров для списания.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    keyboard = [
        [
            InlineKeyboardButton(
                f"{router['router_name']} ({router['quantity']} шт.)",
                callback_data=f"deduct_router_{router['id']}",
            )
        ]
        for router in routers
    ]
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data="manage_cancel")])

    await query.edit_message_text(
        "➖ <b>Списание роутера</b>\n\nВыберите роутер для списания:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )
    return SELECT_ROUTER_ACTION


async def enter_router_name(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Получение модели роутера или списание"""
    if update.callback_query:
        query = update.callback_query
        await query.answer()

        if query.data.startswith("router_model_"):
            if query.data == "router_model_manual":
                await query.edit_message_text(
                    "➕ <b>Добавление роутеров</b>\n\nВведите название роутера:",
                    parse_mode="HTML",
                )
                return ENTER_ROUTER_NAME

            router_name = query.data.replace("router_model_", "")
            context.user_data["router_name"] = router_name
            await query.edit_message_text(
                f"➕ <b>Добавление роутеров</b>\n\nМодель: {router_name}\n\nВведите количество роутеров:",
                parse_mode="HTML",
            )
            return ENTER_ROUTER_QUANTITY

        router_id = int(query.data.split("_")[-1])
        emp_id = context.user_data.get("selected_employee_id")
        routers = flow.db.get_employee_routers(emp_id)
        selected_router = next((r for r in routers if r["id"] == router_id), None)

        if not selected_router:
            await query.edit_message_text("❌ Роутер не найден.")
            await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
            context.user_data.clear()
            return ConversationHandler.END

        success = flow.db.deduct_router_from_employee(emp_id, selected_router["router_name"], 1)
        employee = flow.db.get_employee_by_id(emp_id)

        if success:
            new_quantity = flow.db.get_router_quantity(emp_id, selected_router["router_name"])
            await query.edit_message_text(
                "✅ <b>Роутер списан!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n"
                f"📡 Роутер: {selected_router['router_name']}\n"
                "➖ Списано: 1 шт.\n"
                f"📊 Осталось: {new_quantity} шт.",
                parse_mode="HTML",
            )
        else:
            await query.edit_message_text("❌ Ошибка при списании роутера.", parse_mode="HTML")

        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END

    router_name = update.message.text.strip()
    context.user_data["router_name"] = router_name

    await update.message.reply_text(
        f"✅ Роутер: {router_name}\n\nВведите количество (целое число):",
        parse_mode="HTML",
    )
    return ENTER_ROUTER_QUANTITY


async def enter_router_quantity(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Добавление количества роутеров"""
    try:
        quantity = int(update.message.text.strip())
        if quantity <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "⚠️ Пожалуйста, введите корректное целое число (например: 5)"
        )
        return ENTER_ROUTER_QUANTITY

    emp_id = context.user_data.get("selected_employee_id")
    router_name = context.user_data.get("router_name")
    action = context.user_data.get("router_action")

    employee = flow.db.get_employee_by_id(emp_id)

    if action == "add":
        success = flow.db.add_router_to_employee(emp_id, router_name, quantity)
        if success:
            new_quantity = flow.db.get_router_quantity(emp_id, router_name)
            await update.message.reply_text(
                "✅ <b>Роутеры добавлены!</b>\n\n"
                f"👤 Сотрудник: {employee['full_name']}\n"
                f"📡 Роутер: {router_name}\n"
                f"➕ Добавлено: {quantity} шт.\n"
                f"📊 Всего: {new_quantity} шт.",
                parse_mode="HTML",
                reply_markup=get_main_keyboard(),
            )
        else:
            await update.message.reply_text(
                "❌ Ошибка при добавлении роутеров.", reply_markup=get_main_keyboard()
            )

    context.user_data.clear()
    return ConversationHandler.END

