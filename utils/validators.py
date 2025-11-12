"""
Модуль валидации данных
"""
from typing import Optional, Tuple


class Validator:
    """Класс для валидации данных бота"""
    
    @staticmethod
    def validate_number(text: str, min_value: float = 0, allow_zero: bool = False) -> Tuple[bool, Optional[float], str]:
        """
        Валидация числового значения
        
        Args:
            text: Текст для валидации
            min_value: Минимальное значение
            allow_zero: Разрешить ноль
            
        Returns:
            Tuple[bool, Optional[float], str]: (валидно, значение, сообщение об ошибке)
        """
        try:
            value = float(text.replace(',', '.'))
            
            if not allow_zero and value == 0:
                return False, None, "⚠️ Значение не может быть равно нулю"
            
            if value < min_value:
                return False, None, f"⚠️ Значение не может быть меньше {min_value}"
            
            return True, value, ""
        except ValueError:
            return False, None, "⚠️ Пожалуйста, введите корректное число (например: 100 или 50.5)"
    
    @staticmethod
    def validate_integer(text: str, min_value: int = 1) -> Tuple[bool, Optional[int], str]:
        """
        Валидация целого числа
        
        Args:
            text: Текст для валидации
            min_value: Минимальное значение
            
        Returns:
            Tuple[bool, Optional[int], str]: (валидно, значение, сообщение об ошибке)
        """
        try:
            value = int(text)
            
            if value < min_value:
                return False, None, f"⚠️ Значение не может быть меньше {min_value}"
            
            return True, value, ""
        except ValueError:
            return False, None, f"⚠️ Пожалуйста, введите корректное целое число больше нуля (например: 1, 2, 3)"
    
    @staticmethod
    def validate_text(text: str, min_length: int = 1, max_length: int = 500) -> Tuple[bool, str]:
        """
        Валидация текстового поля
        
        Args:
            text: Текст для валидации
            min_length: Минимальная длина
            max_length: Максимальная длина
            
        Returns:
            Tuple[bool, str]: (валидно, сообщение об ошибке)
        """
        text = text.strip()
        
        if len(text) < min_length:
            return False, f"⚠️ Текст должен содержать минимум {min_length} символов"
        
        if len(text) > max_length:
            return False, f"⚠️ Текст не должен превышать {max_length} символов"
        
        return True, ""
    
    @staticmethod
    def is_cancel_command(text: str) -> bool:
        """Проверка, является ли текст командой отмены"""
        return text == "❌ Отмена"
    
    @staticmethod
    def is_skip_value(value: any) -> bool:
        """Проверка, является ли значение пропущенным"""
        return value == '-' or value is None or value == ''

