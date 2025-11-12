"""
Базовый репозиторий с общими методами для работы с БД
"""
import sqlite3
from typing import Optional, List, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)


class BaseRepository:
    """Базовый класс для всех репозиториев"""
    
    def __init__(self, db_path: str = "isp_bot.db"):
        """Инициализация репозитория"""
        self.db_path = db_path
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить подключение к БД с row_factory"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def execute_query(
        self, 
        query: str, 
        params: Tuple = (), 
        fetch_one: bool = False, 
        fetch_all: bool = False,
        commit: bool = True
    ) -> Any:
        """
        Выполнить SQL запрос
        
        Args:
            query: SQL запрос
            params: Параметры запроса
            fetch_one: Вернуть одну запись
            fetch_all: Вернуть все записи
            commit: Выполнить commit
            
        Returns:
            Результат запроса, ID последней вставки, или None
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            
            if fetch_one:
                result = cursor.fetchone()
                return dict(result) if result else None
            elif fetch_all:
                result = cursor.fetchall()
                return [dict(row) for row in result]
            else:
                last_id = cursor.lastrowid
                if commit:
                    conn.commit()
                return last_id
        except Exception as e:
            logger.error(f"Ошибка выполнения запроса: {e}")
            if conn:
                conn.rollback()
            return None
        finally:
            if conn:
                conn.close()
    
    def execute_many(self, query: str, params_list: List[Tuple]) -> bool:
        """
        Выполнить множественные вставки
        
        Args:
            query: SQL запрос
            params_list: Список параметров
            
        Returns:
            Успех операции
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.executemany(query, params_list)
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка множественного запроса: {e}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                conn.close()

