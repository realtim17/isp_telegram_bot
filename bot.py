"""
Telegram-бот для интернет-провайдера
Автоматизация отчетности по подключению новых абонентов
"""
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

# Импорт конфигурации
from config import (
    TELEGRAM_BOT_TOKEN,
    MANAGE_ACTION, ADD_EMPLOYEE_NAME, DELETE_EMPLOYEE_SELECT,
    SELECT_EMPLOYEE_FOR_MATERIAL, SELECT_MATERIAL_ACTION,
    ENTER_FIBER_AMOUNT, ENTER_TWISTED_AMOUNT,
    SELECT_EMPLOYEE_FOR_ROUTER, SELECT_ROUTER_ACTION,
    ENTER_ROUTER_NAME, ENTER_ROUTER_QUANTITY,
    SELECT_REPORT_EMPLOYEE, SELECT_REPORT_PERIOD,
    logger
)

# Импорт базы данных
from database import Database

# Импорт обработчиков команд
from handlers.commands import (
    start_command,
    help_command,
    cancel_command,
    cancel_and_start_new
)

# Импорт клавиатуры
from utils.keyboards import get_main_keyboard

# Импорт ConversationHandler для подключений
from handlers.connection import connection_conv

# Импорт обработчиков отчетов
from handlers.reports import (
    report_start,
    report_select_period,
    report_generate
)

# Импорт обработчиков сотрудников
from handlers.employees import (
    manage_employees_start,
    manage_action,
    add_employee_name,
    delete_employee_confirm,
    select_employee_for_material,
    select_material_action,
    enter_fiber_amount,
    enter_twisted_amount,
    select_employee_for_router,
    select_router_action,
    enter_router_name,
    enter_router_quantity
)

# Инициализация БД
db = Database()


def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN не найден в .env файле!")
        return
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Фильтр для ввода данных (исключает кнопки главного меню)
    text_input_filter = (
        filters.TEXT & 
        ~filters.COMMAND & 
        ~filters.Regex('^(📝 Новое подключение|📊 Сводный отчет|👥 Управление сотрудниками|ℹ️ Помощь)$')
    )
    
    # Фильтр для кнопок главного меню
    menu_buttons_filter = filters.Regex('^(📝 Новое подключение|📊 Сводный отчет|👥 Управление сотрудниками|ℹ️ Помощь)$')
    
    # Обертки для передачи db в обработчики отчетов и сотрудников
    async def report_start_wrapper(update, context):
        return await report_start(update, context, db)
    
    async def report_select_period_wrapper(update, context):
        return await report_select_period(update, context, db)
    
    async def report_generate_wrapper(update, context):
        return await report_generate(update, context, db)
    
    async def manage_action_wrapper(update, context):
        return await manage_action(update, context, db)
    
    async def add_employee_name_wrapper(update, context):
        return await add_employee_name(update, context, db)
    
    async def delete_employee_confirm_wrapper(update, context):
        return await delete_employee_confirm(update, context, db)
    
    async def select_employee_for_material_wrapper(update, context):
        return await select_employee_for_material(update, context, db)
    
    async def select_material_action_wrapper(update, context):
        return await select_material_action(update, context, db)
    
    async def enter_fiber_amount_wrapper(update, context):
        return await enter_fiber_amount(update, context, db)
    
    async def enter_twisted_amount_wrapper(update, context):
        return await enter_twisted_amount(update, context, db)
    
    async def select_employee_for_router_wrapper(update, context):
        return await select_employee_for_router(update, context, db)
    
    async def select_router_action_wrapper(update, context):
        return await select_router_action(update, context, db)
    
    async def enter_router_name_wrapper(update, context):
        return await enter_router_name(update, context, db)
    
    async def enter_router_quantity_wrapper(update, context):
        return await enter_router_quantity(update, context, db)
    
    # Обработчик отчетов
    report_conv = ConversationHandler(
        entry_points=[
            CommandHandler('report', report_start_wrapper),
            MessageHandler(filters.Regex('^📊 Сводный отчет$'), report_start_wrapper)
        ],
        states={
            SELECT_REPORT_EMPLOYEE: [CallbackQueryHandler(report_select_period_wrapper, pattern='^(rep_emp_|report_cancel)')],
            SELECT_REPORT_PERIOD: [CallbackQueryHandler(report_generate_wrapper, pattern='^(period_|period_cancel)')]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command),
            MessageHandler(menu_buttons_filter, cancel_and_start_new)
        ]
    )
    
    # Обработчик управления сотрудниками
    manage_conv = ConversationHandler(
        entry_points=[
            CommandHandler('manage_employees', manage_employees_start),
            MessageHandler(filters.Regex('^👥 Управление сотрудниками$'), manage_employees_start)
        ],
        states={
            MANAGE_ACTION: [CallbackQueryHandler(manage_action_wrapper, pattern='^(manage_|back_to_manage)')],
            ADD_EMPLOYEE_NAME: [MessageHandler(text_input_filter, add_employee_name_wrapper)],
            DELETE_EMPLOYEE_SELECT: [CallbackQueryHandler(delete_employee_confirm_wrapper, pattern='^(del_emp_|delete_cancel)')],
            SELECT_EMPLOYEE_FOR_MATERIAL: [CallbackQueryHandler(select_employee_for_material_wrapper, pattern='^(mat_emp_|back_to_manage)')],
            SELECT_MATERIAL_ACTION: [CallbackQueryHandler(select_material_action_wrapper, pattern='^(mat_action_|mat_back_to_list)')],
            ENTER_FIBER_AMOUNT: [MessageHandler(text_input_filter, enter_fiber_amount_wrapper)],
            ENTER_TWISTED_AMOUNT: [MessageHandler(text_input_filter, enter_twisted_amount_wrapper)],
            SELECT_EMPLOYEE_FOR_ROUTER: [CallbackQueryHandler(select_employee_for_router_wrapper, pattern='^(rtr_emp_|back_to_manage)')],
            SELECT_ROUTER_ACTION: [
                CallbackQueryHandler(select_router_action_wrapper, pattern='^(rtr_action_|rtr_back_to_list)'),
                CallbackQueryHandler(enter_router_name_wrapper, pattern='^deduct_router_')
            ],
            ENTER_ROUTER_NAME: [MessageHandler(text_input_filter, enter_router_name_wrapper)],
            ENTER_ROUTER_QUANTITY: [MessageHandler(text_input_filter, enter_router_quantity_wrapper)]
        },
        fallbacks=[
            CommandHandler('cancel', cancel_command),
            MessageHandler(menu_buttons_filter, cancel_and_start_new)
        ]
    )
    
    # Добавляем обработчики
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(connection_conv)
    application.add_handler(report_conv)
    application.add_handler(manage_conv)
    application.add_handler(MessageHandler(filters.Regex('^ℹ️ Помощь$'), help_command))
    
    # Fallback для неизвестных команд
    async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text(
            "Неизвестная команда. Используйте кнопки меню или /help для справки.",
            reply_markup=get_main_keyboard()
        )
    
    application.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & ~menu_buttons_filter,
        unknown_command
    ))
    
    # Запускаем бота
    logger.info("🚀 Бот запущен!")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
