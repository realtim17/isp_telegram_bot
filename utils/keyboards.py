"""
Модуль для создания клавиатур
"""
from telegram import ReplyKeyboardMarkup, KeyboardButton


def get_main_keyboard() -> ReplyKeyboardMarkup:
    """Создать главную клавиатуру"""
    keyboard = [
        [KeyboardButton("📝 Новое подключение")],
        [KeyboardButton("📊 Сводный отчет")],
        [KeyboardButton("👥 Управление сотрудниками")],
        [KeyboardButton("ℹ️ Помощь")]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

