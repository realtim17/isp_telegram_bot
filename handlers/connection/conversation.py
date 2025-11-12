"""
ConversationHandler для создания подключений
Интегрирует все модули обработки подключений
"""
from telegram.ext import ConversationHandler, MessageHandler, CallbackQueryHandler, filters

from config import (
    SELECT_CONNECTION_TYPE, UPLOAD_PHOTOS, ENTER_ADDRESS, SELECT_ROUTER,
    ENTER_ROUTER_QUANTITY_CONNECTION, ROUTER_ACCESS, ENTER_PORT, ENTER_FIBER,
    ENTER_TWISTED, CONTRACT_SIGNED, SELECT_EMPLOYEES, SELECT_MATERIAL_PAYER,
    SELECT_ROUTER_PAYER, CONFIRM
)

# Импорт обработчиков шагов
from handlers.connection.steps import (
    new_connection_start,
    select_connection_type,
    upload_photos,
    ask_address,
    enter_address,
    select_router,
    enter_router_quantity_connection,
    router_access_handler,
    enter_port,
    enter_fiber,
    enter_twisted,
    contract_signed
)

# Импорт обработчиков выбора исполнителей
from handlers.connection.employees import (
    select_employee_toggle
)

# Импорт обработчиков валидации
from handlers.connection.validation import (
    select_material_payer,
    select_router_payer
)

# Импорт обработчиков подтверждения
from handlers.connection.confirmation import (
    confirm_connection
)

# Импорт обработчиков отмены
from handlers.connection.cancellation import (
    cancel_connection,
    cancel_by_menu,
    cancel_by_command
)

# Создаем ConversationHandler для подключений
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
            CallbackQueryHandler(select_router, pattern='^(select_router_|router_skip)'),
            CallbackQueryHandler(cancel_connection, pattern='^cancel_connection$')
        ],
        ENTER_ROUTER_QUANTITY_CONNECTION: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_router_quantity_connection)
        ],
        ROUTER_ACCESS: [
            CallbackQueryHandler(router_access_handler, pattern='^(router_access_confirmed|router_access_skipped|cancel_connection)$')
        ],
        ENTER_PORT: [
            CallbackQueryHandler(enter_port, pattern='^(port_skip|cancel_connection)$'),
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_port)
        ],
        ENTER_FIBER: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_fiber)
        ],
        ENTER_TWISTED: [
            MessageHandler(filters.TEXT & ~filters.COMMAND, enter_twisted)
        ],
        CONTRACT_SIGNED: [
            CallbackQueryHandler(contract_signed, pattern='^(contract_confirmed|cancel_connection)$')
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

