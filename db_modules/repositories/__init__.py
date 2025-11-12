"""
Репозитории для работы с БД
Разделение логики доступа к данным по сущностям
"""
from database.repositories.employee_repository import EmployeeRepository
from database.repositories.connection_repository import ConnectionRepository
from database.repositories.material_repository import MaterialRepository
from database.repositories.router_repository import RouterRepository

__all__ = [
    'EmployeeRepository',
    'ConnectionRepository',
    'MaterialRepository',
    'RouterRepository'
]

