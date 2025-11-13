"""
Вспомогательные обработчики отображения списков
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from utils.keyboards import get_main_keyboard


async def show_employees_list(flow: "EmployeeFlow", update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Выводит список сотрудников с материалами и роутерами"""
    employees = flow.db.get_all_employees()

    if not employees:
        await update.message.reply_text(
            "📋 <b>Список сотрудников пуст</b>\n\n"
            "Добавьте сотрудников через меню\n"
            "👥 Управление сотрудниками → ➕ Добавить сотрудника",
            parse_mode="HTML",
            reply_markup=get_main_keyboard(),
        )
        return

    message_lines = ["👤 <b>Список сотрудников</b>\n"]

    for idx, emp in enumerate(employees, 1):
        fiber_balance = emp.get("fiber_balance", 0) or 0
        twisted_balance = emp.get("twisted_pair_balance", 0) or 0
        routers = flow.db.get_employee_routers(emp["id"])
        router_count = sum(r["quantity"] for r in routers)

        message_lines.append(f"{idx}. <b>{emp['full_name']}</b>")
        message_lines.append("   📦 Материалы:")
        message_lines.append(f"   • ВОЛС: {fiber_balance} м")
        message_lines.append(f"   • Витая пара: {twisted_balance} м")
        message_lines.append(f"   📡 Роутеры: {router_count} шт.")

        if routers:
            message_lines.append("   Модели:")
            for router in routers:
                message_lines.append(
                    f"   • {router['router_name']}: {router['quantity']} шт."
                )
        message_lines.append("")

    message_lines.append("━━━━━━━━━━━━━━━━━━━━━━")
    message_lines.append(f"<b>Всего сотрудников:</b> {len(employees)}")

    await update.message.reply_text(
        "\n".join(message_lines),
        parse_mode="HTML",
        reply_markup=get_main_keyboard(),
    )

