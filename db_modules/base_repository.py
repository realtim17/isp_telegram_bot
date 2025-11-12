"""
Базовый репозиторий с общими методами
"""
import sqlite3
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """Базовый класс для всех репозиториев"""
    
    def __init__(self, db_path: str = "isp_bot.db"):
        """Инициализация репозитория"""
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(self, query: str, params: tuple = (), fetch_one: bool = False, fetch_all: bool = False):
        """
        Выполнить SQL запрос
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch_one: Вернуть одну запись
            fetch_all: Вернуть все записи
            
        Returns:
            Результат запроса или ID последней вставленной записи
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                conn.close()
                return dict(result) if result else None
            elif fetch_all:
                result = cursor.fetchall()
                conn.close()
                return [dict(row) for row in result]
            else:
                last_id = cursor.lastrowid
                conn.commit()
                conn.close()
                return last_id
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            return None

