"""
Модуль базы данных
Обеспечивает доступ к данным через репозитории
"""
# Временный импорт из старого файла database.py
# TODO: После полного рефакторинга переименовать database.py в database/db_manager.py
import sys
import os

# Импортируем Database из корневого database.py
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from database import Database as _Database

Database = _Database

__all__ = ['Database']

