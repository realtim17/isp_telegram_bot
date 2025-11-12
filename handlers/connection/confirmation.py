"""
Подтверждение данных и сохранение подключения
"""
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import CONFIRM, CONNECTION_TYPES, logger
from utils.keyboards import get_main_keyboard
from utils.helpers import send_connection_report
from database import Database


async def show_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Показать подтверждение перед сохранением"""
    query = update.callback_query
    
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    
    # Получаем имена выбранных сотрудников
    employees = db.get_all_employees()
    employee_names = [emp['full_name'] for emp in employees if emp['id'] in selected_employees]
    
    # Получаем читаемое название типа подключения
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    # Рассчитываем долю на каждого
    emp_count = len(selected_employees)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
    
    # Получаем информацию о плательщиках
    material_payer_id = context.user_data.get('material_payer_id')
    router_payer_id = context.user_data.get('router_payer_id')
    
    payer_info = ""
    if material_payer_id:
        payer = db.get_employee_by_id(material_payer_id)
        if payer:
            payer_info += f"\n\n💰 <b>Материалы списываются с:</b> {payer['full_name']}"
    
    if router_payer_id:
        router_payer = db.get_employee_by_id(router_payer_id)
        if router_payer:
            router_quantity = data.get('router_quantity', 1)
            quantity_text = f" ({router_quantity} шт.)" if router_quantity > 1 else ""
            payer_info += f"\n📡 <b>Роутер списывается с:</b> {router_payer['full_name']}{quantity_text}"
    
    # Формируем отображение роутера
    router_model = data.get('router_model', '-')
    router_quantity = data.get('router_quantity', 1)
    
    if router_model == '-' or not router_model:
        router_display = "-"
    else:
        router_display = router_model
        if router_quantity > 1:
            router_display += f" ({router_quantity} шт.)"
    
    # Формируем отображение порта
    port = data.get('port', '-')
    port_display = port if port and port != '' else '-'
    
    # Получаем информацию о договоре
    contract_signed = data.get('contract_signed', False)
    contract_status = "✅ Подписан" if contract_signed else "❌ Не подписан"
    
    confirmation_text = f"""
📋 <b>Подтверждение данных</b>

🏢 <b>Тип:</b> {type_name}
📍 <b>Адрес:</b> {data['address']}
🌐 <b>Роутер:</b> {router_display}
🔌 <b>Порт:</b> {port_display}

📏 <b>Метраж:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

📄 <b>Договор:</b> {contract_status}

👥 <b>Исполнители ({emp_count}):</b>
{chr(10).join([f"  • {name}" for name in employee_names])}

<b>Метраж на каждого (для зарплаты):</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м{payer_info}

📸 <b>Фото:</b> {len(photos)} шт.

Всё верно? Подтвердите создание отчета.
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Подтвердить", callback_data='confirm_yes')],
        [InlineKeyboardButton("❌ Отменить", callback_data='confirm_no')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        confirmation_text,
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return CONFIRM


async def confirm_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Подтверждение и сохранение подключения"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'confirm_no':
        context.user_data.clear()
        await query.edit_message_text(
            "❌ Создание отчета отменено.",
            reply_markup=None
        )
        await query.message.reply_text(
            "Выберите действие:",
            reply_markup=get_main_keyboard()
        )
        return ConversationHandler.END
    
    # Сохраняем в БД
    db = Database()
    data = context.user_data['connection_data']
    photos = context.user_data.get('photos', [])
    selected_employees = context.user_data.get('selected_employees', [])
    material_payer_id = context.user_data.get('material_payer_id')
    router_payer_id = context.user_data.get('router_payer_id')
    user_id = update.effective_user.id
    
    router_quantity = data.get('router_quantity', 1)
    contract_signed = data.get('contract_signed', False)
    router_access = data.get('router_access', False)
    
    connection_id = db.create_connection(
        connection_type=data.get('connection_type', 'mkd'),
        address=data['address'],
        router_model=data['router_model'],
        port=data['port'],
        fiber_meters=data['fiber_meters'],
        twisted_pair_meters=data['twisted_pair_meters'],
        employee_ids=selected_employees,
        photo_file_ids=photos,
        created_by=user_id,
        material_payer_id=material_payer_id,
        router_quantity=router_quantity,
        contract_signed=contract_signed,
        router_access=router_access
    )
    
    if connection_id:
        # Списываем роутер, если указан плательщик и роутер не пропущен
        router_model = data.get('router_model', '-')
        if router_payer_id and router_model != '-' and router_model:
            success = db.deduct_router_from_employee(
                router_payer_id, 
                router_model, 
                router_quantity,
                connection_id=connection_id,
                created_by=user_id
            )
            if success:
                logger.info(f"Роутер '{router_model}' x{router_quantity} списан с сотрудника ID {router_payer_id}")
            else:
                logger.warning(f"Не удалось списать роутер '{router_model}' x{router_quantity} с сотрудника ID {router_payer_id}")
        
        # Отправляем подтверждение
        await query.edit_message_text(
            f"✅ <b>Отчет успешно создан!</b>\n\n"
            f"ID подключения: #{connection_id}\n"
            f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            parse_mode='HTML'
        )
        
        # Отправляем отчет с фотографиями
        await send_connection_report(query.message, connection_id, data, photos, selected_employees, db)
        
        await query.message.reply_text(
            "Выберите следующее действие:",
            reply_markup=get_main_keyboard()
        )
    else:
        await query.edit_message_text(
            "❌ Ошибка при создании отчета. Попробуйте позже.",
            parse_mode='HTML'
        )
    
    context.user_data.clear()
    return ConversationHandler.END

