"""
Модуль для работы с базой данных SQLite
"""
import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class Database:
    """Класс для работы с базой данных"""
    
    def __init__(self, db_path: str = "isp_bot.db"):
        """Инициализация подключения к БД"""
        self.db_path = db_path
        self.create_tables()
    
    def get_connection(self) -> sqlite3.Connection:
        """Получить подключение к БД"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def create_tables(self):
        """Создать таблицы БД"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Таблица сотрудников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employees (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL UNIQUE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Таблица подключений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                address TEXT NOT NULL,
                router_model TEXT NOT NULL,
                port TEXT NOT NULL,
                fiber_meters REAL NOT NULL,
                twisted_pair_meters REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL
            )
        """)
        
        # Таблица связи подключений и сотрудников (многие ко многим)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_employees (
                connection_id INTEGER NOT NULL,
                employee_id INTEGER NOT NULL,
                PRIMARY KEY (connection_id, employee_id),
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
            )
        """)
        
        # Таблица фотографий подключений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connection_photos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_id INTEGER NOT NULL,
                photo_file_id TEXT NOT NULL,
                photo_order INTEGER NOT NULL,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Таблицы БД созданы успешно")
    
    # ==================== СОТРУДНИКИ ====================
    
    def add_employee(self, full_name: str) -> Optional[int]:
        """Добавить нового сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("INSERT INTO employees (full_name) VALUES (?)", (full_name,))
            employee_id = cursor.lastrowid
            conn.commit()
            conn.close()
            logger.info(f"Добавлен сотрудник: {full_name} (ID: {employee_id})")
            return employee_id
        except sqlite3.IntegrityError:
            logger.warning(f"Сотрудник {full_name} уже существует")
            return None
    
    def get_all_employees(self) -> List[Dict]:
        """Получить список всех сотрудников"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, created_at FROM employees ORDER BY full_name")
        employees = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return employees
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Получить сотрудника по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT id, full_name, created_at FROM employees WHERE id = ?", (employee_id,))
        row = cursor.fetchone()
        conn.close()
        return dict(row) if row else None
    
    def delete_employee(self, employee_id: int) -> bool:
        """Удалить сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
            deleted = cursor.rowcount > 0
            conn.commit()
            conn.close()
            if deleted:
                logger.info(f"Удален сотрудник ID: {employee_id}")
            return deleted
        except Exception as e:
            logger.error(f"Ошибка при удалении сотрудника: {e}")
            return False
    
    # ==================== ПОДКЛЮЧЕНИЯ ====================
    
    def create_connection(
        self,
        address: str,
        router_model: str,
        port: str,
        fiber_meters: float,
        twisted_pair_meters: float,
        employee_ids: List[int],
        photo_file_ids: List[str],
        created_by: int
    ) -> Optional[int]:
        """Создать новое подключение"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Создаем запись подключения
            cursor.execute("""
                INSERT INTO connections 
                (address, router_model, port, fiber_meters, twisted_pair_meters, created_by)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (address, router_model, port, fiber_meters, twisted_pair_meters, created_by))
            
            connection_id = cursor.lastrowid
            
            # Связываем сотрудников
            for emp_id in employee_ids:
                cursor.execute("""
                    INSERT INTO connection_employees (connection_id, employee_id)
                    VALUES (?, ?)
                """, (connection_id, emp_id))
            
            # Сохраняем фотографии
            for idx, photo_id in enumerate(photo_file_ids):
                cursor.execute("""
                    INSERT INTO connection_photos (connection_id, photo_file_id, photo_order)
                    VALUES (?, ?, ?)
                """, (connection_id, photo_id, idx))
            
            conn.commit()
            conn.close()
            logger.info(f"Создано подключение ID: {connection_id}")
            return connection_id
        except Exception as e:
            logger.error(f"Ошибка при создании подключения: {e}")
            return None
    
    def get_connection_by_id(self, connection_id: int) -> Optional[Dict]:
        """Получить подключение по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем основную информацию
        cursor.execute("""
            SELECT id, address, router_model, port, fiber_meters, 
                   twisted_pair_meters, created_at, created_by
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
    
    # ==================== ОТЧЕТЫ ====================
    
    def get_employee_report(
        self,
        employee_id: int,
        days: Optional[int] = None
    ) -> Tuple[List[Dict], Dict]:
        """
        Получить отчет по сотруднику за период
        
        Args:
            employee_id: ID сотрудника
            days: Количество дней (None = все время)
        
        Returns:
            Tuple: (список подключений, итоговая статистика)
        """
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
    
    def get_all_connections_count(self) -> int:
        """Получить общее количество подключений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM connections")
        count = cursor.fetchone()['count']
        conn.close()
        return count
