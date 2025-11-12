"""
Репозиторий для работы с сотрудниками
"""
import sqlite3
from typing import List, Dict, Optional, Tuple
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class EmployeeRepository(BaseRepository):
    """Репозиторий для управления сотрудниками"""
    
    def create(self, full_name: str) -> Optional[int]:
        """Добавить нового сотрудника"""
        try:
            return self.execute_query(
                "INSERT INTO employees (full_name) VALUES (?)",
                (full_name,)
            )
        except sqlite3.IntegrityError:
            logger.warning(f"Сотрудник {full_name} уже существует")
            return None
    
    def get_all(self) -> List[Dict]:
        """Получить список всех сотрудников"""
        return self.execute_query("""
            SELECT id, full_name, fiber_balance, twisted_pair_balance, created_at 
            FROM employees 
            ORDER BY full_name
        """, fetch_all=True) or []
    
    def get_by_id(self, employee_id: int) -> Optional[Dict]:
        """Получить сотрудника по ID"""
        return self.execute_query("""
            SELECT id, full_name, fiber_balance, twisted_pair_balance, created_at 
            FROM employees 
            WHERE id = ?
        """, (employee_id,), fetch_one=True)
    
    def delete(self, employee_id: int) -> bool:
        """Удалить сотрудника и все связанные данные"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Сначала удаляем роутеры сотрудника (если CASCADE не настроен)
            cursor.execute("DELETE FROM employee_routers WHERE employee_id = ?", (employee_id,))
            deleted_routers = cursor.rowcount
            
            # Обнуляем балансы материалов (или можно оставить для истории)
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = 0, twisted_pair_balance = 0 
                WHERE id = ?
            """, (employee_id,))
            
            # Удаляем сотрудника
            cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            deleted_emp = cursor.rowcount > 0
            
            conn.commit()
            conn.close()
            
            if deleted_emp:
                logger.info(f"Удален сотрудник ID: {employee_id} и {deleted_routers} записей роутеров")
                return True
            return False
        except Exception as e:
            logger.error(f"Ошибка при удалении сотрудника: {e}")
            return False
    
    def get_balance(self, employee_id: int) -> Optional[Tuple]:
        """Получить баланс материалов сотрудника (ВОЛС, Витая пара)"""
        try:
            result = self.execute_query("""
                SELECT fiber_balance, twisted_pair_balance 
                FROM employees 
                WHERE id = ?
            """, (employee_id,), fetch_one=True)
            
            if result:
                return (result.get('fiber_balance', 0) or 0, 
                       result.get('twisted_pair_balance', 0) or 0)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            return None

