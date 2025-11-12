"""
Модуль для форматирования текстов
"""
from typing import Dict, List
from datetime import datetime
from config import CONNECTION_TYPES


class TextFormatter:
    """Класс для форматирования текстовых сообщений"""
    
    @staticmethod
    def format_connection_type(conn_type: str) -> str:
        """Форматирование типа подключения"""
        return CONNECTION_TYPES.get(conn_type, conn_type)
    
    @staticmethod
    def format_router_info(router_model: str, quantity: int = 1) -> str:
        """
        Форматирование информации о роутере
        
        Args:
            router_model: Модель роутера
            quantity: Количество
            
        Returns:
            Отформатированная строка
        """
        if router_model == '-' or not router_model:
            return "-"
        
        if quantity > 1:
            return f"{router_model} ({quantity} шт.)"
        
        return router_model
    
    @staticmethod
    def format_port(port: str) -> str:
        """Форматирование порта"""
        return port if port and port != '' and port != '-' else '-'
    
    @staticmethod
    def format_boolean_status(value: bool, true_text: str = "✅ Да", false_text: str = "❌ Нет") -> str:
        """Форматирование булева значения"""
        return true_text if value else false_text
    
    @staticmethod
    def format_contract_status(signed: bool) -> str:
        """Форматирование статуса договора"""
        return "✅ Подписан" if signed else "❌ Не подписан"
    
    @staticmethod
    def format_router_access_status(has_access: bool) -> str:
        """Форматирование статуса доступа на роутер"""
        return "✅ Получен" if has_access else "⏭️ Пропущено"
    
    @staticmethod
    def format_date(dt: datetime = None) -> str:
        """Форматирование даты"""
        if dt is None:
            dt = datetime.now()
        return dt.strftime('%d.%m.%Y %H:%M')
    
    @staticmethod
    def format_employee_list(names: List[str], prefix: str = "  • ") -> str:
        """Форматирование списка сотрудников"""
        return '\n'.join([f"{prefix}{name}" for name in names])
    
    @staticmethod
    def format_cable_info(fiber: float, twisted: float) -> str:
        """Форматирование информации о кабеле"""
        return f"""📏 <b>Проложенный кабель:</b>
  • ВОЛС: {fiber} м
  • Витая пара: {twisted} м"""
    
    @staticmethod
    def format_employee_share(fiber_total: float, twisted_total: float, emp_count: int) -> str:
        """Форматирование доли на каждого сотрудника"""
        fiber_per_emp = round(fiber_total / emp_count, 2)
        twisted_per_emp = round(twisted_total / emp_count, 2)
        
        return f"""💡 <b>Расчет на каждого исполнителя:</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м"""


class MessageBuilder:
    """Класс для построения сложных сообщений"""
    
    @staticmethod
    def build_step_header(step: int, total: int, title: str) -> str:
        """Построение заголовка шага"""
        return f"<b>Шаг {step}/{total}: {title}</b>"
    
    @staticmethod
    def build_confirmation_message(
        connection_type: str,
        address: str,
        router_model: str,
        router_quantity: int,
        port: str,
        fiber: float,
        twisted: float,
        contract_signed: bool,
        employees: List[str],
        payer_info: str = ""
    ) -> str:
        """Построение сообщения подтверждения"""
        type_name = TextFormatter.format_connection_type(connection_type)
        router_display = TextFormatter.format_router_info(router_model, router_quantity)
        port_display = TextFormatter.format_port(port)
        contract_status = TextFormatter.format_contract_status(contract_signed)
        emp_count = len(employees)
        
        fiber_per_emp = round(fiber / emp_count, 2)
        twisted_per_emp = round(twisted / emp_count, 2)
        
        return f"""📋 <b>Подтверждение данных</b>

🏢 <b>Тип:</b> {type_name}
📍 <b>Адрес:</b> {address}
🌐 <b>Роутер:</b> {router_display}
🔌 <b>Порт:</b> {port_display}

📏 <b>Метраж:</b>
  • ВОЛС: {fiber} м
  • Витая пара: {twisted} м

📄 <b>Договор:</b> {contract_status}

👥 <b>Исполнители ({emp_count}):</b>
{TextFormatter.format_employee_list(employees)}

<b>Метраж на каждого (для зарплаты):</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м{payer_info}

📸 <b>Фото:</b> загружено

Всё верно? Подтвердите создание отчета."""

