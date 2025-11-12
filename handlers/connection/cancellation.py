"""
Обработчики отмены создания подключения
"""
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from utils.keyboards import get_main_keyboard
from handlers.connection.constants import CANCEL_TEXT, INTERRUPTED_TEXT


async def cancel_connection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена создания подключения через кнопку"""
    query = update.callback_query
    await query.answer()
    
    # Очищаем данные пользователя
    context.user_data.clear()
    
    await query.edit_message_text(
        f"{CANCEL_TEXT}\n"
        f"Выберите действие из меню:",
        parse_mode='HTML'
    )
    
    # Отправляем главное меню
    await query.message.reply_text(
        "Выберите действие:",
        reply_markup=get_main_keyboard()
    )
    
    return ConversationHandler.END


async def cancel_by_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена при переходе в другой раздел через меню"""
    context.user_data.clear()
    await update.message.reply_text(
        INTERRUPTED_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    return ConversationHandler.END


async def cancel_by_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена через команду /cancel"""
    context.user_data.clear()
    await update.message.reply_text(
        CANCEL_TEXT,
        reply_markup=get_main_keyboard(),
        parse_mode='HTML'
    )
    return ConversationHandler.END

