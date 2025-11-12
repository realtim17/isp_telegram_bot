"""
Репозиторий для работы с материалами сотрудников
"""
from typing import List, Dict, Optional
from datetime import datetime
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class MaterialRepository(BaseRepository):
    """Репозиторий для управления материалами (ВОЛС и витая пара)"""
    
    def add_material(
        self, 
        employee_id: int, 
        fiber_meters: float = 0, 
        twisted_pair_meters: float = 0,
        created_by: Optional[int] = None
    ) -> bool:
        """Добавить материалы на баланс сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance + ?,
                    twisted_pair_balance = twisted_pair_balance + ?
                WHERE id = ?
            """, (fiber_meters, twisted_pair_meters, employee_id))
            
            updated = cursor.rowcount > 0
            
            if updated:
                # Получаем новый баланс
                cursor.execute("""
                    SELECT fiber_balance, twisted_pair_balance 
                    FROM employees WHERE id = ?
                """, (employee_id,))
                row = cursor.fetchone()
                new_fiber = row[0] if row else 0
                new_twisted = row[1] if row else 0
                
                conn.commit()
                conn.close()
                
                # Логируем операции
                if fiber_meters > 0:
                    self.log_movement(employee_id, 'add', 'fiber', 'ВОЛС', 
                                    fiber_meters, new_fiber, None, created_by)
                if twisted_pair_meters > 0:
                    self.log_movement(employee_id, 'add', 'twisted_pair', 'Витая пара',
                                    twisted_pair_meters, new_twisted, None, created_by)
                
                logger.info(f"Добавлено материалов сотруднику ID {employee_id}: "
                          f"ВОЛС +{fiber_meters}м, Витая пара +{twisted_pair_meters}м")
            else:
                conn.close()
            
            return updated
        except Exception as e:
            logger.error(f"Ошибка при добавлении материалов: {e}")
            return False
    
    def deduct_material(
        self,
        employee_id: int,
        fiber_meters: float = 0,
        twisted_pair_meters: float = 0,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> bool:
        """Списать материалы с баланса сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Проверяем текущий баланс
            cursor.execute("""
                SELECT fiber_balance, twisted_pair_balance 
                FROM employees 
                WHERE id = ?
            """, (employee_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"Сотрудник ID {employee_id} не найден")
                conn.close()
                return False
            
            current_fiber = row[0] or 0
            current_twisted = row[1] or 0
            
            # Проверяем достаточность средств
            if current_fiber < fiber_meters:
                logger.warning(f"Недостаточно ВОЛС у сотрудника ID {employee_id}")
                conn.close()
                return False
            
            if current_twisted < twisted_pair_meters:
                logger.warning(f"Недостаточно витой пары у сотрудника ID {employee_id}")
                conn.close()
                return False
            
            # Списываем материалы
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance - ?,
                    twisted_pair_balance = twisted_pair_balance - ?
                WHERE id = ?
            """, (fiber_meters, twisted_pair_meters, employee_id))
            
            updated = cursor.rowcount > 0
            
            if updated:
                new_fiber = current_fiber - fiber_meters
                new_twisted = current_twisted - twisted_pair_meters
                
                conn.commit()
                conn.close()
                
                # Логируем операции
                if fiber_meters > 0:
                    self.log_movement(employee_id, 'deduct', 'fiber', 'ВОЛС',
                                    fiber_meters, new_fiber, connection_id, created_by)
                if twisted_pair_meters > 0:
                    self.log_movement(employee_id, 'deduct', 'twisted_pair', 'Витая пара',
                                    twisted_pair_meters, new_twisted, connection_id, created_by)
                
                logger.info(f"Списано материалов у сотрудника ID {employee_id}: "
                          f"ВОЛС -{fiber_meters}м, Витая пара -{twisted_pair_meters}м")
            else:
                conn.close()
            
            return updated
        except Exception as e:
            logger.error(f"Ошибка при списании материалов: {e}")
            return False
    
    def log_movement(
        self,
        employee_id: int,
        operation_type: str,
        item_type: str,
        item_name: str,
        quantity: float,
        balance_after: float,
        connection_id: Optional[int] = None,
        created_by: Optional[int] = None
    ) -> bool:
        """Записать движение материала в лог"""
        try:
            self.execute_query("""
                INSERT INTO material_movement_log 
                (employee_id, operation_type, item_type, item_name, quantity, 
                 balance_after, connection_id, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (employee_id, operation_type, item_type, item_name, quantity,
                  balance_after, connection_id, created_by))
            
            logger.info(f"Logged movement: {operation_type} {quantity} {item_type} for employee {employee_id}")
            return True
        except Exception as e:
            logger.error(f"Ошибка при логировании движения: {e}")
            return False
    
    def get_movements(
        self,
        employee_id: int,
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Получить все движения материалов сотрудника за период"""
        try:
            return self.execute_query("""
                SELECT 
                    operation_type,
                    item_type,
                    item_name,
                    quantity,
                    balance_after,
                    connection_id,
                    created_at
                FROM material_movement_log
                WHERE employee_id = ? 
                  AND created_at >= ? 
                  AND created_at <= ?
                ORDER BY created_at
            """, (employee_id, start_date, end_date), fetch_all=True) or []
        except Exception as e:
            logger.error(f"Ошибка при получении движений: {e}")
            return []

