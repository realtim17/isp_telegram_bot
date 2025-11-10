"""
Обработчики для формирования отчетов
"""
import os
import logging

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler

from config import SELECT_REPORT_EMPLOYEE, SELECT_REPORT_PERIOD
from utils.keyboards import get_main_keyboard
from report_generator import ReportGenerator

logger = logging.getLogger(__name__)


async def report_start(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Начало формирования отчета"""
    employees = db.get_all_employees()
    
    if not employees:
        text = "⚠️ В системе нет ни одного сотрудника!"
        if update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.message.reply_text(text, reply_markup=get_main_keyboard())
        else:
            await update.message.reply_text(text, reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    keyboard = []
    for emp in employees:
        keyboard.append([InlineKeyboardButton(emp['full_name'], callback_data=f"rep_emp_{emp['id']}")])
    
    keyboard.append([InlineKeyboardButton("❌ Отмена", callback_data='report_cancel')])
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    text = "📊 <b>Сводный отчет</b>\n\nВыберите сотрудника:"
    
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text, reply_markup=reply_markup, parse_mode='HTML')
    else:
        await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='HTML')
    
    return SELECT_REPORT_EMPLOYEE


async def report_select_period(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Выбор периода для отчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'report_cancel':
        await query.edit_message_text("❌ Формирование отчета отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        return ConversationHandler.END
    
    # Сохраняем выбранного сотрудника
    emp_id = int(query.data.split('_')[2])
    context.user_data['report_employee_id'] = emp_id
    
    employee = db.get_employee_by_id(emp_id)
    
    keyboard = [
        [InlineKeyboardButton("📅 Последняя неделя", callback_data='period_7')],
        [InlineKeyboardButton("📅 Последний месяц", callback_data='period_30')],
        [InlineKeyboardButton("📅 Все время", callback_data='period_all')],
        [InlineKeyboardButton("❌ Отмена", callback_data='period_cancel')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(
        f"Выбран сотрудник: <b>{employee['full_name']}</b>\n\n"
        f"Выберите период для отчета:",
        reply_markup=reply_markup,
        parse_mode='HTML'
    )
    
    return SELECT_REPORT_PERIOD


async def report_generate(update: Update, context: ContextTypes.DEFAULT_TYPE, db) -> int:
    """Генерация и отправка отчета"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'period_cancel':
        await query.edit_message_text("❌ Формирование отчета отменено.")
        await query.message.reply_text("Выберите действие:", reply_markup=get_main_keyboard())
        context.user_data.clear()
        return ConversationHandler.END
    
    # Определяем период
    period_map = {
        'period_7': (7, 'Последняя неделя'),
        'period_30': (30, 'Последний месяц'),
        'period_all': (None, 'Все время')
    }
    
    days, period_name = period_map[query.data]
    emp_id = context.user_data['report_employee_id']
    employee = db.get_employee_by_id(emp_id)
    
    await query.edit_message_text("⏳ Формирую отчет, подождите...")
    
    # Получаем данные из БД
    connections, stats = db.get_employee_report(emp_id, days)
    
    if not connections:
        await query.message.reply_text(
            f"ℹ️ У сотрудника <b>{employee['full_name']}</b> нет подключений за выбранный период.",
            parse_mode='HTML',
            reply_markup=get_main_keyboard()
        )
        context.user_data.clear()
        return ConversationHandler.END
    
    # Генерируем Excel-отчет
    try:
        filename = ReportGenerator.generate_employee_report(
            employee_name=employee['full_name'],
            connections=connections,
            stats=stats,
            period_name=period_name
        )
        
        # Отправляем файл
        with open(filename, 'rb') as file:
            await query.message.reply_document(
                document=file,
                filename=filename,
                caption=f"📊 Отчет по сотруднику: <b>{employee['full_name']}</b>\n"
                        f"Период: {period_name}\n"
                        f"Подключений: {stats['total_connections']}\n"
                        f"ВОЛС: {stats['total_fiber_meters']} м\n"
                        f"Витая пара: {stats['total_twisted_pair_meters']} м",
                parse_mode='HTML'
            )
        
        # Удаляем временный файл
        os.remove(filename)
        
        await query.message.reply_text(
            "✅ Отчет сформирован!",
            reply_markup=get_main_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при генерации отчета: {e}")
        await query.message.reply_text(
            "❌ Ошибка при формировании отчета. Попробуйте позже.",
            reply_markup=get_main_keyboard()
        )
    
    context.user_data.clear()
    return ConversationHandler.END

