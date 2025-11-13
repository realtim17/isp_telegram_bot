"""
Вспомогательные функции
"""
from typing import Dict, List
from datetime import datetime
import logging

from telegram import InputMediaPhoto

from config import REPORTS_CHANNEL_ID, CONNECTION_TYPES

logger = logging.getLogger(__name__)


def _create_media_group(photos: List[str], caption: str) -> List[InputMediaPhoto]:
    """Создать медиа-группу из фотографий с подписью"""
    media_group = []
    for idx, photo_id in enumerate(photos):
        if idx == 0:
            media_group.append(InputMediaPhoto(media=photo_id, caption=caption, parse_mode='HTML'))
        else:
            media_group.append(InputMediaPhoto(media=photo_id))
    return media_group


def _format_report_text(connection_id: int, data: Dict, employee_names: List[str]) -> str:
    """Форматировать текст отчёта"""
    conn_type = data.get('connection_type', 'mkd')
    type_name = CONNECTION_TYPES.get(conn_type, conn_type)
    
    emp_count = len(employee_names)
    fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
    twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
    
    # Получаем информацию о роутерах (если есть)
    router_model = data.get('router_model', '-')
    router_quantity = data.get('router_quantity', 1)
    
    # Если роутер пропущен или "-", отображаем "-"
    if router_model == '-' or not router_model:
        router_info = "-"
    else:
        router_info = router_model
    if router_quantity > 1:
        router_info += f" ({router_quantity} шт.)"
    
    # Получаем информацию о порте
    port = data.get('port', '-')
    port_display = port if port and port != '' else '-'
    
    # Получаем информацию о договоре
    contract_signed = data.get('contract_signed', False)
    contract_status = "✅ Подписан" if contract_signed else "❌ Не подписан"
    
    # Получаем информацию о доступе на роутер
    router_access = data.get('router_access', False)
    router_access_status = "✅ Получен" if router_access else "⏭️ Пропущено"
    
    # Получаем информацию о Телеграмм Боте
    telegram_bot_connected = data.get('telegram_bot_connected', False)
    telegram_bot_status = "✅ Подключен" if telegram_bot_connected else "-"
    
    return f"""
<b>📋 ОТЧЕТ О ПОДКЛЮЧЕНИИ #{connection_id}</b>

<b>📍 Адрес:</b> {data['address']}
<b> Тип подключения:</b> {type_name}
<b> Модель роутера:</b> {router_info}
<b> Доступ на роутер:</b> {router_access_status}
<b> Договор:</b> {contract_status}
<b> Телеграмм Бот:</b> {telegram_bot_status}
<b> Порт:</b> {port_display}

<b>📏 Проложенный кабель:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

<b>👥 Исполнители ({emp_count}):</b>
{chr(10).join(['  • ' + name for name in employee_names])}

<b>💡 Расчет на каждого исполнителя:</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м

<b>📅 Дата подключения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""


async def send_connection_report(message, connection_id: int, data: Dict, photos: List[str], 
                                 employee_ids: List[int], db) -> None:
    """Отправить красиво отформатированный отчет о подключении с фотографиями"""
    try:
        # Получаем имена сотрудников
        employees = db.get_all_employees()
        employee_names = [emp['full_name'] for emp in employees if emp['id'] in employee_ids]
        
        # Формируем текст отчета
        report_text = _format_report_text(connection_id, data, employee_names)
        
        # Отправляем отчет пользователю
        if photos:
            media_group = _create_media_group(photos, report_text)
            await message.reply_media_group(media=media_group)
            logger.info(f"Отправлен отчет #{connection_id} пользователю с {len(photos)} фото")
        else:
            await message.reply_text(report_text, parse_mode='HTML')
            logger.info(f"Отправлен отчет #{connection_id} пользователю без фото")
        
        # Отправляем отчет в канал, если он настроен
        if REPORTS_CHANNEL_ID:
            try:
                bot = message.get_bot()
                if photos:
                    media_group = _create_media_group(photos, report_text)
                    await bot.send_media_group(chat_id=REPORTS_CHANNEL_ID, media=media_group)
                    logger.info(f"Отчет #{connection_id} отправлен в канал с {len(photos)} фото")
                else:
                    await bot.send_message(chat_id=REPORTS_CHANNEL_ID, text=report_text, parse_mode='HTML')
                    logger.info(f"Отчет #{connection_id} отправлен в канал без фото")
            except Exception as channel_error:
                logger.error(f"Ошибка при отправке отчета в канал: {channel_error}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета о подключении: {e}")
        await message.reply_text(
            "⚠️ Отчет создан, но возникла ошибка при отправке фотографий.",
            parse_mode='HTML'
        )

