"""
Тесты для модуля database.py
"""
import unittest
import os
from database import Database


class TestDatabase(unittest.TestCase):
    """Тесты для класса Database"""
    
    def setUp(self):
        """Подготовка к тестам - создание тестовой БД"""
        self.test_db_path = "test_isp_bot.db"
        self.db = Database(self.test_db_path)
    
    def tearDown(self):
        """Очистка после тестов - удаление тестовой БД"""
        if os.path.exists(self.test_db_path):
            os.remove(self.test_db_path)
    
    # ==================== ТЕСТЫ СОТРУДНИКОВ ====================
    
    def test_add_employee(self):
        """Тест добавления сотрудника"""
        emp_id = self.db.add_employee("Иванов Иван Иванович")
        self.assertIsNotNone(emp_id)
        self.assertIsInstance(emp_id, int)
    
    def test_add_duplicate_employee(self):
        """Тест добавления дубликата сотрудника"""
        name = "Петров Петр Петрович"
        emp_id1 = self.db.add_employee(name)
        emp_id2 = self.db.add_employee(name)
        
        self.assertIsNotNone(emp_id1)
        self.assertIsNone(emp_id2)
    
    def test_get_all_employees(self):
        """Тест получения всех сотрудников"""
        # Добавляем сотрудников
        self.db.add_employee("Сотрудник 1")
        self.db.add_employee("Сотрудник 2")
        self.db.add_employee("Сотрудник 3")
        
        employees = self.db.get_all_employees()
        self.assertEqual(len(employees), 3)
        self.assertTrue(all(isinstance(emp, dict) for emp in employees))
    
    def test_get_employee_by_id(self):
        """Тест получения сотрудника по ID"""
        emp_id = self.db.add_employee("Тестовый Сотрудник")
        employee = self.db.get_employee_by_id(emp_id)
        
        self.assertIsNotNone(employee)
        self.assertEqual(employee['full_name'], "Тестовый Сотрудник")
        self.assertEqual(employee['id'], emp_id)
    
    def test_get_nonexistent_employee(self):
        """Тест получения несуществующего сотрудника"""
        employee = self.db.get_employee_by_id(99999)
        self.assertIsNone(employee)
    
    def test_delete_employee(self):
        """Тест удаления сотрудника"""
        emp_id = self.db.add_employee("Удаляемый Сотрудник")
        result = self.db.delete_employee(emp_id)
        
        self.assertTrue(result)
        
        # Проверяем, что сотрудник действительно удален
        employee = self.db.get_employee_by_id(emp_id)
        self.assertIsNone(employee)
    
    def test_delete_nonexistent_employee(self):
        """Тест удаления несуществующего сотрудника"""
        result = self.db.delete_employee(99999)
        self.assertFalse(result)
    
    # ==================== ТЕСТЫ ПОДКЛЮЧЕНИЙ ====================
    
    def test_create_connection(self):
        """Тест создания подключения"""
        # Добавляем сотрудников
        emp1 = self.db.add_employee("Монтажник 1")
        emp2 = self.db.add_employee("Монтажник 2")
        
        # Создаем подключение
        conn_id = self.db.create_connection(
            address="ул. Тестовая, д. 1",
            router_model="Test Router",
            port="8",
            fiber_meters=100.0,
            twisted_pair_meters=20.0,
            employee_ids=[emp1, emp2],
            photo_file_ids=["photo1", "photo2"],
            created_by=123456789
        )
        
        self.assertIsNotNone(conn_id)
        self.assertIsInstance(conn_id, int)
    
    def test_get_connection_by_id(self):
        """Тест получения подключения по ID"""
        # Подготовка данных
        emp1 = self.db.add_employee("Монтажник А")
        emp2 = self.db.add_employee("Монтажник Б")
        
        conn_id = self.db.create_connection(
            address="ул. Ленина, д. 10",
            router_model="Keenetic",
            port="5",
            fiber_meters=150.0,
            twisted_pair_meters=25.0,
            employee_ids=[emp1, emp2],
            photo_file_ids=["photo1", "photo2", "photo3"],
            created_by=123456789
        )
        
        # Получаем подключение
        connection = self.db.get_connection_by_id(conn_id)
        
        self.assertIsNotNone(connection)
        self.assertEqual(connection['address'], "ул. Ленина, д. 10")
        self.assertEqual(connection['router_model'], "Keenetic")
        self.assertEqual(connection['fiber_meters'], 150.0)
        self.assertEqual(len(connection['employees']), 2)
        self.assertEqual(len(connection['photos']), 3)
    
    # ==================== ТЕСТЫ ОТЧЕТОВ ====================
    
    def test_get_employee_report_empty(self):
        """Тест получения отчета для сотрудника без подключений"""
        emp_id = self.db.add_employee("Новый Сотрудник")
        connections, stats = self.db.get_employee_report(emp_id)
        
        self.assertEqual(len(connections), 0)
        self.assertEqual(stats['total_connections'], 0)
        self.assertEqual(stats['total_fiber_meters'], 0)
        self.assertEqual(stats['total_twisted_pair_meters'], 0)
    
    def test_get_employee_report_single(self):
        """Тест отчета с одним подключением (один исполнитель)"""
        emp_id = self.db.add_employee("Единственный Исполнитель")
        
        conn_id = self.db.create_connection(
            address="ул. Мира, д. 5",
            router_model="TP-Link",
            port="3",
            fiber_meters=100.0,
            twisted_pair_meters=15.0,
            employee_ids=[emp_id],
            photo_file_ids=[],
            created_by=123456789
        )
        
        connections, stats = self.db.get_employee_report(emp_id)
        
        self.assertEqual(len(connections), 1)
        self.assertEqual(stats['total_connections'], 1)
        self.assertEqual(stats['total_fiber_meters'], 100.0)
        self.assertEqual(stats['total_twisted_pair_meters'], 15.0)
    
    def test_get_employee_report_shared(self):
        """Тест отчета с разделенным подключением (два исполнителя)"""
        emp1 = self.db.add_employee("Исполнитель 1")
        emp2 = self.db.add_employee("Исполнитель 2")
        
        # Создаем подключение с двумя исполнителями
        self.db.create_connection(
            address="ул. Пушкина, д. 3",
            router_model="Mikrotik",
            port="12",
            fiber_meters=200.0,
            twisted_pair_meters=30.0,
            employee_ids=[emp1, emp2],
            photo_file_ids=[],
            created_by=123456789
        )
        
        # Проверяем отчет для первого исполнителя
        connections, stats = self.db.get_employee_report(emp1)
        
        self.assertEqual(len(connections), 1)
        self.assertEqual(stats['total_fiber_meters'], 100.0)  # 200 / 2
        self.assertEqual(stats['total_twisted_pair_meters'], 15.0)  # 30 / 2
    
    def test_get_employee_report_multiple(self):
        """Тест отчета с несколькими подключениями"""
        emp1 = self.db.add_employee("Многозадачный 1")
        emp2 = self.db.add_employee("Многозадачный 2")
        
        # Первое подключение (один исполнитель)
        self.db.create_connection(
            address="Адрес 1",
            router_model="Router 1",
            port="1",
            fiber_meters=100.0,
            twisted_pair_meters=10.0,
            employee_ids=[emp1],
            photo_file_ids=[],
            created_by=123456789
        )
        
        # Второе подключение (два исполнителя)
        self.db.create_connection(
            address="Адрес 2",
            router_model="Router 2",
            port="2",
            fiber_meters=200.0,
            twisted_pair_meters=20.0,
            employee_ids=[emp1, emp2],
            photo_file_ids=[],
            created_by=123456789
        )
        
        # Проверяем отчет
        connections, stats = self.db.get_employee_report(emp1)
        
        self.assertEqual(len(connections), 2)
        self.assertEqual(stats['total_fiber_meters'], 200.0)  # 100 + 100 (200/2)
        self.assertEqual(stats['total_twisted_pair_meters'], 20.0)  # 10 + 10 (20/2)
    
    def test_get_connections_count(self):
        """Тест подсчета общего количества подключений"""
        emp_id = self.db.add_employee("Тестовый")
        
        # Изначально 0
        count = self.db.get_all_connections_count()
        self.assertEqual(count, 0)
        
        # Добавляем 3 подключения
        for i in range(3):
            self.db.create_connection(
                address=f"Адрес {i}",
                router_model="Router",
                port=str(i),
                fiber_meters=100.0,
                twisted_pair_meters=10.0,
                employee_ids=[emp_id],
                photo_file_ids=[],
                created_by=123456789
            )
        
        count = self.db.get_all_connections_count()
        self.assertEqual(count, 3)


if __name__ == '__main__':
    print("🧪 Запуск тестов базы данных...\n")
    unittest.main(verbosity=2)
