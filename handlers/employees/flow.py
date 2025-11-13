"""
Класс-координатор управления сотрудниками
"""
from __future__ import annotations

from telegram.ext import CallbackQueryHandler, CommandHandler, ConversationHandler, MessageHandler, filters

from config import (
    MANAGE_ACTION,
    ADD_EMPLOYEE_NAME,
    DELETE_EMPLOYEE_SELECT,
    SELECT_EMPLOYEE_FOR_MATERIAL,
    SELECT_MATERIAL_ACTION,
    ENTER_FIBER_AMOUNT,
    ENTER_TWISTED_AMOUNT,
    SELECT_EMPLOYEE_FOR_ROUTER,
    SELECT_ROUTER_ACTION,
    ENTER_ROUTER_NAME,
    ENTER_ROUTER_QUANTITY,
)
from database import Database

from . import listing, materials, mutations, routers, start


class EmployeeFlow:
    """Инкапсулирует логику управления сотрудниками"""

    def __init__(self, db: Database) -> None:
        self.db = db

    # --- Основные действия ---
    async def manage_employees_start(self, update, context):
        return await start.manage_employees_start(self, update, context)

    async def manage_action(self, update, context):
        return await start.manage_action(self, update, context)

    async def add_employee_name(self, update, context):
        return await mutations.add_employee_name(self, update, context)

    async def delete_employee_confirm(self, update, context):
        return await mutations.delete_employee_confirm(self, update, context)

    # --- Материалы ---
    async def select_employee_for_material(self, update, context):
        return await materials.select_employee_for_material(self, update, context)

    async def select_material_action(self, update, context):
        return await materials.select_material_action(self, update, context)

    async def enter_fiber_amount(self, update, context):
        return await materials.enter_fiber_amount(self, update, context)

    async def enter_twisted_amount(self, update, context):
        return await materials.enter_twisted_amount(self, update, context)

    # --- Роутеры ---
    async def select_employee_for_router(self, update, context):
        return await routers.select_employee_for_router(self, update, context)

    async def select_router_action(self, update, context):
        return await routers.select_router_action(self, update, context)

    async def enter_router_name(self, update, context):
        return await routers.enter_router_name(self, update, context)

    async def enter_router_quantity(self, update, context):
        return await routers.enter_router_quantity(self, update, context)

    # --- Общий список ---
    async def show_employees_list(self, update, context):
        return await listing.show_employees_list(self, update, context)

    # --- Построение ConversationHandler ---
    def build_conversation(self, text_input_filter, fallbacks) -> ConversationHandler:
        return ConversationHandler(
            entry_points=[
                CommandHandler('manage_employees', self.manage_employees_start),
                MessageHandler(filters.Regex("^👥 Управление сотрудниками$"), self.manage_employees_start),
            ],
            states={
                MANAGE_ACTION: [
                    CallbackQueryHandler(self.manage_action, pattern="^(manage_|back_to_manage)")
                ],
                ADD_EMPLOYEE_NAME: [
                    MessageHandler(text_input_filter, self.add_employee_name)
                ],
                DELETE_EMPLOYEE_SELECT: [
                    CallbackQueryHandler(self.delete_employee_confirm, pattern="^(del_emp_|delete_cancel)")
                ],
                SELECT_EMPLOYEE_FOR_MATERIAL: [
                    CallbackQueryHandler(
                        self.select_employee_for_material, pattern="^(mat_emp_|back_to_manage)"
                    )
                ],
                SELECT_MATERIAL_ACTION: [
                    CallbackQueryHandler(
                        self.select_material_action, pattern="^(mat_action_|mat_back_to_list)"
                    )
                ],
                ENTER_FIBER_AMOUNT: [
                    MessageHandler(text_input_filter, self.enter_fiber_amount)
                ],
                ENTER_TWISTED_AMOUNT: [
                    MessageHandler(text_input_filter, self.enter_twisted_amount)
                ],
                SELECT_EMPLOYEE_FOR_ROUTER: [
                    CallbackQueryHandler(
                        self.select_employee_for_router, pattern="^(rtr_emp_|back_to_manage)"
                    )
                ],
                SELECT_ROUTER_ACTION: [
                    CallbackQueryHandler(
                        self.select_router_action, pattern="^(rtr_action_|rtr_back_to_list)"
                    ),
                    CallbackQueryHandler(
                        self.enter_router_name, pattern="^(deduct_router_|router_model_)"
                    ),
                ],
                ENTER_ROUTER_NAME: [
                    CallbackQueryHandler(self.enter_router_name, pattern="^router_model_"),
                    MessageHandler(text_input_filter, self.enter_router_name),
                ],
                ENTER_ROUTER_QUANTITY: [
                    MessageHandler(text_input_filter, self.enter_router_quantity)
                ],
            },
            fallbacks=fallbacks,
        )
