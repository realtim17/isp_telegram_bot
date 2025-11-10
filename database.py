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
                fiber_balance REAL DEFAULT 0,
                twisted_pair_balance REAL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Добавляем поля балансов в существующую таблицу (если их нет)
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN fiber_balance REAL DEFAULT 0")
            logger.info("Добавлено поле fiber_balance в таблицу employees")
        except sqlite3.OperationalError:
            pass
        
        try:
            cursor.execute("ALTER TABLE employees ADD COLUMN twisted_pair_balance REAL DEFAULT 0")
            logger.info("Добавлено поле twisted_pair_balance в таблицу employees")
        except sqlite3.OperationalError:
            pass
        
        # Таблица подключений
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                connection_type TEXT NOT NULL DEFAULT 'mkd',
                address TEXT NOT NULL,
                router_model TEXT NOT NULL,
                port TEXT NOT NULL,
                fiber_meters REAL NOT NULL,
                twisted_pair_meters REAL NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_by INTEGER NOT NULL
            )
        """)
        
        # Добавляем поле connection_type в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connections ADD COLUMN connection_type TEXT NOT NULL DEFAULT 'mkd'")
            logger.info("Добавлено поле connection_type в таблицу connections")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
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
                photo_category TEXT NOT NULL DEFAULT 'other',
                photo_order INTEGER NOT NULL,
                FOREIGN KEY (connection_id) REFERENCES connections(id) ON DELETE CASCADE
            )
        """)
        
        # Добавляем поле photo_category в существующую таблицу (если его нет)
        try:
            cursor.execute("ALTER TABLE connection_photos ADD COLUMN photo_category TEXT NOT NULL DEFAULT 'other'")
            logger.info("Добавлено поле photo_category в таблицу connection_photos")
        except sqlite3.OperationalError:
            # Поле уже существует
            pass
        
        # Таблица роутеров сотрудников
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS employee_routers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                employee_id INTEGER NOT NULL,
                router_name TEXT NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (employee_id) REFERENCES employees(id) ON DELETE CASCADE
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
        cursor.execute("""
            SELECT id, full_name, fiber_balance, twisted_pair_balance, created_at 
            FROM employees 
            ORDER BY full_name
        """)
        employees = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return employees
    
    def get_employee_by_id(self, employee_id: int) -> Optional[Dict]:
        """Получить сотрудника по ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, fiber_balance, twisted_pair_balance, created_at 
            FROM employees 
            WHERE id = ?
        """, (employee_id,))
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
    
    def add_material_to_employee(self, employee_id: int, fiber_meters: float = 0, 
                                 twisted_pair_meters: float = 0) -> bool:
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
            conn.commit()
            conn.close()
            if updated:
                logger.info(f"Добавлено материалов сотруднику ID {employee_id}: "
                          f"ВОЛС +{fiber_meters}м, Витая пара +{twisted_pair_meters}м")
            return updated
        except Exception as e:
            logger.error(f"Ошибка при добавлении материалов: {e}")
            return False
    
    def deduct_material_from_employee(self, employee_id: int, fiber_meters: float = 0,
                                      twisted_pair_meters: float = 0) -> bool:
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
                return False
            
            current_fiber = row[0] or 0
            current_twisted = row[1] or 0
            
            # Проверяем достаточность средств
            if current_fiber < fiber_meters:
                logger.warning(f"Недостаточно ВОЛС у сотрудника ID {employee_id}: "
                             f"есть {current_fiber}м, требуется {fiber_meters}м")
                return False
            
            if current_twisted < twisted_pair_meters:
                logger.warning(f"Недостаточно витой пары у сотрудника ID {employee_id}: "
                             f"есть {current_twisted}м, требуется {twisted_pair_meters}м")
                return False
            
            # Списываем материалы
            cursor.execute("""
                UPDATE employees 
                SET fiber_balance = fiber_balance - ?,
                    twisted_pair_balance = twisted_pair_balance - ?
                WHERE id = ?
            """, (fiber_meters, twisted_pair_meters, employee_id))
            
            updated = cursor.rowcount > 0
            conn.commit()
            conn.close()
            
            if updated:
                logger.info(f"Списано материалов у сотрудника ID {employee_id}: "
                          f"ВОЛС -{fiber_meters}м, Витая пара -{twisted_pair_meters}м")
            return updated
        except Exception as e:
            logger.error(f"Ошибка при списании материалов: {e}")
            return False
    
    def get_employee_balance(self, employee_id: int) -> Optional[Tuple[float, float]]:
        """Получить баланс материалов сотрудника (ВОЛС, Витая пара)"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT fiber_balance, twisted_pair_balance 
                FROM employees 
                WHERE id = ?
            """, (employee_id,))
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return (row[0] or 0, row[1] or 0)
            return None
        except Exception as e:
            logger.error(f"Ошибка при получении баланса: {e}")
            return None
    
    # ==================== РОУТЕРЫ СОТРУДНИКОВ ====================
    
    def add_router_to_employee(self, employee_id: int, router_name: str, quantity: int) -> bool:
        """Добавить роутеры сотруднику"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже такой роутер у сотрудника
            cursor.execute("""
                SELECT id, quantity FROM employee_routers 
                WHERE employee_id = ? AND router_name = ?
            """, (employee_id, router_name))
            existing = cursor.fetchone()
            
            if existing:
                # Обновляем количество
                new_quantity = existing[1] + quantity
                cursor.execute("""
                    UPDATE employee_routers 
                    SET quantity = ? 
                    WHERE id = ?
                """, (new_quantity, existing[0]))
                logger.info(f"Обновлено количество роутеров '{router_name}' у сотрудника ID {employee_id}: +{quantity} (всего: {new_quantity})")
            else:
                # Добавляем новую запись
                cursor.execute("""
                    INSERT INTO employee_routers (employee_id, router_name, quantity)
                    VALUES (?, ?, ?)
                """, (employee_id, router_name, quantity))
                logger.info(f"Добавлены роутеры '{router_name}' сотруднику ID {employee_id}: {quantity} шт.")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении роутеров: {e}")
            return False
    
    def deduct_router_from_employee(self, employee_id: int, router_name: str, quantity: int = 1) -> bool:
        """Списать роутер у сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Проверяем текущее количество
            cursor.execute("""
                SELECT id, quantity FROM employee_routers 
                WHERE employee_id = ? AND router_name = ?
            """, (employee_id, router_name))
            existing = cursor.fetchone()
            
            if not existing:
                logger.warning(f"Роутер '{router_name}' не найден у сотрудника ID {employee_id}")
                conn.close()
                return False
            
            current_quantity = existing[1]
            if current_quantity < quantity:
                logger.warning(f"Недостаточно роутеров '{router_name}' у сотрудника ID {employee_id}: есть {current_quantity}, требуется {quantity}")
                conn.close()
                return False
            
            new_quantity = current_quantity - quantity
            
            if new_quantity == 0:
                # Удаляем запись, если количество стало 0
                cursor.execute("DELETE FROM employee_routers WHERE id = ?", (existing[0],))
                logger.info(f"Списаны все роутеры '{router_name}' у сотрудника ID {employee_id}")
            else:
                # Обновляем количество
                cursor.execute("""
                    UPDATE employee_routers 
                    SET quantity = ? 
                    WHERE id = ?
                """, (new_quantity, existing[0]))
                logger.info(f"Списан роутер '{router_name}' у сотрудника ID {employee_id}: -{quantity} (осталось: {new_quantity})")
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            logger.error(f"Ошибка при списании роутера: {e}")
            return False
    
    def get_employee_routers(self, employee_id: int) -> List[Dict]:
        """Получить список роутеров сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id, router_name, quantity, created_at
                FROM employee_routers 
                WHERE employee_id = ?
                ORDER BY router_name
            """, (employee_id,))
            
            routers = []
            for row in cursor.fetchall():
                routers.append({
                    'id': row[0],
                    'router_name': row[1],
                    'quantity': row[2],
                    'created_at': row[3]
                })
            
            conn.close()
            return routers
        except Exception as e:
            logger.error(f"Ошибка при получении роутеров сотрудника: {e}")
            return []
    
    def get_router_quantity(self, employee_id: int, router_name: str) -> int:
        """Получить количество конкретного роутера у сотрудника"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT quantity FROM employee_routers 
                WHERE employee_id = ? AND router_name = ?
            """, (employee_id, router_name))
            row = cursor.fetchone()
            conn.close()
            
            return row[0] if row else 0
        except Exception as e:
            logger.error(f"Ошибка при получении количества роутеров: {e}")
            return 0
    
    def get_all_router_names(self) -> List[str]:
        """Получить список всех уникальных названий роутеров"""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT router_name 
                FROM employee_routers 
                ORDER BY router_name
            """)
            
            names = [row[0] for row in cursor.fetchall()]
            conn.close()
            return names
        except Exception as e:
            logger.error(f"Ошибка при получении списка роутеров: {e}")
            return []
    
    # ==================== ПОДКЛЮЧЕНИЯ ====================
    
    def create_connection(
        self,
        connection_type: str,
        address: str,
        router_model: str,
        port: str,
        fiber_meters: float,
        twisted_pair_meters: float,
        employee_ids: List[int],
        photo_file_ids: List[str],
        created_by: int,
        material_payer_id: Optional[int] = None
    ) -> Optional[int]:
        """Создать новое подключение и списать материалы с указанного сотрудника
        
        Args:
            material_payer_id: ID сотрудника, с которого списывать материалы.
                              Если None, материалы списываются поровну со всех.
        """
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Создаем запись подключения
            cursor.execute("""
                INSERT INTO connections 
                (connection_type, address, router_model, port, fiber_meters, twisted_pair_meters, created_by)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (connection_type, address, router_model, port, fiber_meters, twisted_pair_meters, created_by))
            
            connection_id = cursor.lastrowid
            
            # Связываем всех сотрудников с подключением
            for emp_id in employee_ids:
                cursor.execute("""
                    INSERT INTO connection_employees (connection_id, employee_id)
                    VALUES (?, ?)
                """, (connection_id, emp_id))
            
            # Списываем материалы
            if material_payer_id:
                # Списываем весь материал с одного сотрудника
                cursor.execute("""
                    SELECT fiber_balance, twisted_pair_balance 
                    FROM employees 
                    WHERE id = ?
                """, (material_payer_id,))
                row = cursor.fetchone()
                
                if not row:
                    logger.error(f"Сотрудник ID {material_payer_id} не найден")
                    conn.close()
                    return None
                
                current_fiber = row[0] or 0
                current_twisted = row[1] or 0
                
                # Проверяем достаточность материалов
                if current_fiber < fiber_meters:
                    logger.warning(f"Недостаточно ВОЛС у сотрудника ID {material_payer_id}: "
                                 f"есть {current_fiber}м, требуется {fiber_meters}м")
                    conn.close()
                    return None
                
                if current_twisted < twisted_pair_meters:
                    logger.warning(f"Недостаточно витой пары у сотрудника ID {material_payer_id}: "
                                 f"есть {current_twisted}м, требуется {twisted_pair_meters}м")
                    conn.close()
                    return None
                
                # Списываем весь материал с одного сотрудника
                cursor.execute("""
                    UPDATE employees 
                    SET fiber_balance = fiber_balance - ?,
                        twisted_pair_balance = twisted_pair_balance - ?
                    WHERE id = ?
                """, (fiber_meters, twisted_pair_meters, material_payer_id))
                
                logger.info(f"Списано у сотрудника ID {material_payer_id}: "
                          f"ВОЛС -{fiber_meters}м, Витая пара -{twisted_pair_meters}м (полная сумма)")
            else:
                # Старая логика: делим поровну между всеми
                emp_count = len(employee_ids)
                fiber_per_emp = fiber_meters / emp_count if emp_count > 0 else 0
                twisted_per_emp = twisted_pair_meters / emp_count if emp_count > 0 else 0
                
                for emp_id in employee_ids:
                    cursor.execute("""
                        UPDATE employees 
                        SET fiber_balance = fiber_balance - ?,
                            twisted_pair_balance = twisted_pair_balance - ?
                        WHERE id = ?
                    """, (fiber_per_emp, twisted_per_emp, emp_id))
                    
                    logger.info(f"Списано у сотрудника ID {emp_id}: "
                              f"ВОЛС -{fiber_per_emp}м, Витая пара -{twisted_per_emp}м")
            
            # Сохраняем фотографии
            for idx, photo_id in enumerate(photo_file_ids):
                cursor.execute("""
                    INSERT INTO connection_photos (connection_id, photo_file_id, photo_category, photo_order)
                    VALUES (?, ?, ?, ?)
                """, (connection_id, photo_id, 'general', idx))
            
            conn.commit()
            conn.close()
            logger.info(f"Создано подключение ID: {connection_id}, материалы списаны")
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
    
    def get_all_connections_count(self) -> int:
        """Получить общее количество подключений"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM connections")
        count = cursor.fetchone()['count']
        conn.close()
        return count
