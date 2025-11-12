"""
Репозиторий для работы с подключениями
"""
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import logging

from database.base_repository import BaseRepository

logger = logging.getLogger(__name__)


class ConnectionRepository(BaseRepository):
    """Репозиторий для управления подключениями"""
    
    def create(
        self,
        connection_type: str,
        address: str,
        router_model: str,
        port: str,
        fiber_meters: float,
        twisted_pair_meters: float,
        created_by: int,
        router_quantity: int = 1,
        contract_signed: bool = False,
        router_access: bool = False,
        telegram_bot_connected: bool = False
    ) -> Optional[int]:
        """Создать новое подключение"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Создаем запись подключения
            cursor.execute("""
                INSERT INTO connections 
                (connection_type, address, router_model, port, fiber_meters, 
                 twisted_pair_meters, created_by, router_quantity, contract_signed, 
                 router_access, telegram_bot_connected)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                connection_type, address, router_model, port, fiber_meters,
                twisted_pair_meters, created_by, router_quantity,
                1 if contract_signed else 0,
                1 if router_access else 0,
                1 if telegram_bot_connected else 0
            ))
            
            connection_id = cursor.lastrowid
            conn.commit()
            conn.close()
            
            logger.info(f"Создано подключение ID: {connection_id}")
            return connection_id
        except Exception as e:
            logger.error(f"Ошибка при создании подключения: {e}")
            return None
    
    def link_employees(self, connection_id: int, employee_ids: List[int]) -> bool:
        """Связать сотрудников с подключением"""
        try:
            params_list = [(connection_id, emp_id) for emp_id in employee_ids]
            return self.execute_many("""
                INSERT INTO connection_employees (connection_id, employee_id)
                VALUES (?, ?)
            """, params_list)
        except Exception as e:
            logger.error(f"Ошибка при связывании сотрудников: {e}")
            return False
    
    def save_photos(self, connection_id: int, photo_file_ids: List[str]) -> bool:
        """Сохранить фотографии подключения"""
        try:
            params_list = [
                (connection_id, photo_id, 'general', idx)
                for idx, photo_id in enumerate(photo_file_ids)
            ]
            return self.execute_many("""
                INSERT INTO connection_photos (connection_id, photo_file_id, photo_category, photo_order)
                VALUES (?, ?, ?, ?)
            """, params_list)
        except Exception as e:
            logger.error(f"Ошибка при сохранении фотографий: {e}")
            return False
    
    def get_by_id(self, connection_id: int) -> Optional[Dict]:
        """Получить подключение по ID"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Получаем основную информацию
            cursor.execute("""
                SELECT id, connection_type, address, router_model, port, fiber_meters, 
                       twisted_pair_meters, created_at, created_by, router_quantity, 
                       contract_signed, router_access, telegram_bot_connected
                FROM connections
                WHERE id = ?
            """, (connection_id,))
            
            row = cursor.fetchone()
            if not row:
                conn.close()
                return None
            
            connection = dict(row)
            
            # Получаем сотрудников
            cursor.execute("""
                SELECT e.id, e.full_name
                FROM employees e
                JOIN connection_employees ce ON e.id = ce.employee_id
                WHERE ce.connection_id = ?
                ORDER BY e.full_name
            """, (connection_id,))
            connection['employees'] = [dict(row) for row in cursor.fetchall()]
            
            # Получаем фотографии
            cursor.execute("""
                SELECT photo_file_id
                FROM connection_photos
                WHERE connection_id = ?
                ORDER BY photo_order
            """, (connection_id,))
            connection['photos'] = [row['photo_file_id'] for row in cursor.fetchall()]
            
            conn.close()
            return connection
        except Exception as e:
            logger.error(f"Ошибка при получении подключения: {e}")
            return None
    
    def get_employee_report(
        self,
        employee_id: int,
        days: Optional[int] = None
    ) -> tuple[List[Dict], Dict]:
        """Получить отчет по сотруднику за период"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Формируем условие по дате
            date_condition = ""
            params = [employee_id]
            if days is not None:
                date_limit = datetime.now() - timedelta(days=days)
                date_condition = "AND c.created_at >= ?"
                params.append(date_limit.strftime("%Y-%m-%d %H:%M:%S"))
            
            # Получаем подключения с участием сотрудника
            query = f"""
                SELECT 
                    c.id,
                    c.connection_type,
                    c.address,
                    c.router_model,
                    c.port,
                    c.fiber_meters,
                    c.twisted_pair_meters,
                    c.created_at,
                    COUNT(DISTINCT ce.employee_id) as employee_count
                FROM connections c
                JOIN connection_employees ce ON c.id = ce.connection_id
                WHERE ce.connection_id IN (
                    SELECT connection_id 
                    FROM connection_employees 
                    WHERE employee_id = ?
                )
                {date_condition}
                GROUP BY c.id
                ORDER BY c.created_at DESC
            """
            
            cursor.execute(query, params)
            connections = []
            
            total_fiber = 0.0
            total_twisted = 0.0
            
            for row in cursor.fetchall():
                conn_dict = dict(row)
                emp_count = conn_dict['employee_count']
                
                # Рассчитываем долю для сотрудника
                conn_dict['employee_fiber_meters'] = round(conn_dict['fiber_meters'] / emp_count, 2)
                conn_dict['employee_twisted_pair_meters'] = round(conn_dict['twisted_pair_meters'] / emp_count, 2)
                
                # Получаем список всех исполнителей для этого подключения
                cursor.execute("""
                    SELECT e.full_name
                    FROM employees e
                    JOIN connection_employees ce ON e.id = ce.employee_id
                    WHERE ce.connection_id = ?
                    ORDER BY e.full_name
                """, (conn_dict['id'],))
                conn_dict['all_employees'] = [row['full_name'] for row in cursor.fetchall()]
                
                connections.append(conn_dict)
                total_fiber += conn_dict['employee_fiber_meters']
                total_twisted += conn_dict['employee_twisted_pair_meters']
            
            conn.close()
            
            stats = {
                'total_connections': len(connections),
                'total_fiber_meters': round(total_fiber, 2),
                'total_twisted_pair_meters': round(total_twisted, 2)
            }
            
            return connections, stats
        except Exception as e:
            logger.error(f"Ошибка при получении отчета: {e}")
            return [], {}
    
    def get_all_count(self) -> int:
        """Получить общее количество подключений"""
        try:
            result = self.execute_query(
                "SELECT COUNT(*) as count FROM connections",
                fetch_one=True
            )
            return result['count'] if result else 0
        except Exception as e:
            logger.error(f"Ошибка при подсчете подключений: {e}")
            return 0

