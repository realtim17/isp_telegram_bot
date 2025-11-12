# План рефакторинга ISP Telegram Bot

## Текущее состояние

### Проблемы кодовой базы

1. **handlers/connection.py** - 1162 строки
   - Смешанная ответственность
   - Дублирование кода
   - Сложность тестирования

2. **database.py** - 871 строка
   - Monolithic класс
   - Множественная ответственность
   - Сложно расширять

3. **bot.py** - множество wrapper функций
   - Передача db через параметры
   - Повторяющийся код

4. **Отсутствие модульности**
   - Нет разделения на слои
   - Нет валидации данных
   - Нет форматирования

## Выполненные улучшения

### ✅ Созданные модули

1. **utils/validators.py** - Валидация данных
   - `Validator` класс с методами валидации
   - Единообразная обработка ошибок
   - Переиспользование во всех handlers

2. **utils/formatters.py** - Форматирование текстов
   - `TextFormatter` для простого форматирования
   - `MessageBuilder` для сложных сообщений
   - Централизованное форматирование отчетов

3. **database/base_repository.py** - Базовый репозиторий
   - Общие методы для всех репозиториев
   - Упрощенная работа с БД

4. **handlers/connection/constants.py** - Константы
   - Вынесены магические числа
   - Текстовые шаблоны

5. **Структура директорий**
   - `database/repositories/` - для репозиториев
   - `handlers/connection/` - для модулей подключений

## План дальнейшего рефакторинга

### Фаза 1: Разделение handlers/connection.py

#### Приоритет: ВЫСОКИЙ
#### Время: 4-6 часов

**Цель:** Разделить 1162 строки на логические модули

**Шаги:**

1. **Создать handlers/connection/steps.py** (400-500 строк)
   - Переместить все обработчики шагов:
     - `new_connection_start()`
     - `select_connection_type()`
     - `upload_photos()`
     - `ask_address()`
     - `enter_address()`
     - `select_router()`
     - `enter_router_quantity_connection()`
     - `router_access_handler()`
     - `enter_port()`
     - `enter_fiber()`
     - `enter_twisted()`
     - `contract_signed()`

2. **Создать handlers/connection/validation.py** (200-300 строк)
   - Переместить валидацию материалов/роутеров:
     - `check_materials_and_proceed()`
     - `select_material_payer()`
     - `check_routers_and_proceed()`
     - `select_router_payer()`

3. **Создать handlers/connection/confirmation.py** (150-200 строк)
   - Переместить подтверждение:
     - `show_confirmation()`
     - `confirm_connection()`

4. **Создать handlers/connection/employees.py** (100-150 строк)
   - Переместить выбор исполнителей:
     - `select_employee_toggle()`

5. **Создать handlers/connection/cancellation.py** (50-100 строк)
   - Переместить отмену:
     - `cancel_connection()`
     - `cancel_by_menu()`
     - `cancel_by_command()`

6. **Обновить handlers/connection/conversation.py** (100 строк)
   - Импортировать из модулей
   - Создать ConversationHandler
   - Экспортировать `connection_conv`

**Результат:**
```
handlers/connection/
├── __init__.py           # 5 строк
├── conversation.py       # 100 строк
├── steps.py              # 450 строк
├── validation.py         # 250 строк
├── confirmation.py       # 180 строк
├── employees.py          # 120 строк
├── cancellation.py       # 70 строк
└── constants.py          # 30 строк
```

**Преимущества:**
- Каждый модуль < 500 строк
- Четкое разделение ответственности
- Легко найти нужный код
- Упрощено тестирование

---

### Фаза 2: Создание репозиториев

#### Приоритет: ВЫСОКИЙ
#### Время: 3-4 часа

**Цель:** Разделить database.py (871 строка) на репозитории

**Шаги:**

1. **Создать database/repositories/employee_repository.py**
   ```python
   class EmployeeRepository(BaseRepository):
       def create(full_name) -> Optional[int]
       def get_all() -> List[Dict]
       def get_by_id(id) -> Optional[Dict]
       def delete(id) -> bool
   ```

2. **Создать database/repositories/material_repository.py**
   ```python
   class MaterialRepository(BaseRepository):
       def add_material(emp_id, fiber, twisted) -> bool
       def deduct_material(emp_id, fiber, twisted) -> bool
       def get_balance(emp_id) -> Tuple[float, float]
       def log_movement(...) -> bool
       def get_movements(emp_id, start, end) -> List[Dict]
   ```

3. **Создать database/repositories/router_repository.py**
   ```python
   class RouterRepository(BaseRepository):
       def add_router(emp_id, name, quantity) -> bool
       def deduct_router(emp_id, name, quantity) -> bool
       def get_routers(emp_id) -> List[Dict]
       def get_quantity(emp_id, name) -> int
       def get_all_names() -> List[str]
   ```

4. **Создать database/repositories/connection_repository.py**
   ```python
   class ConnectionRepository(BaseRepository):
       def create(...) -> Optional[int]
       def get_by_id(id) -> Optional[Dict]
       def get_by_employee(emp_id, days) -> List[Dict]
   ```

5. **Переименовать database.py → database/db_manager.py**
   - Использовать композицию репозиториев
   - Оставить публичный API неизменным
   - Делегировать вызовы репозиториям

**Результат:**
```python
class Database:
    def __init__(self):
        self.employees = EmployeeRepository()
        self.materials = MaterialRepository()
        self.routers = RouterRepository()
        self.connections = ConnectionRepository()
    
    def add_employee(self, name):
        return self.employees.create(name)
    
    # ... делегирование остальных методов
```

**Преимущества:**
- Разделение ответственности
- Легкость тестирования (mock репозиториев)
- Возможность замены БД
- Чистота кода

---

### Фаза 3: Dependency Injection

#### Приоритет: СРЕДНИЙ
#### Время: 2-3 часа

**Цель:** Устранить множество wrapper функций в bot.py

**Текущий подход:**
```python
# bot.py - 214 строк, много wrapper'ов

async def report_start_wrapper(update, context):
    return await report_start(update, context, db)

async def manage_action_wrapper(update, context):
    return await manage_action(update, context, db)

# ... еще 10+ wrapper'ов
```

**Новый подход:**

**Вариант 1: Глобальный экземпляр**
```python
# database/__init__.py
from database.db_manager import Database

db_instance = Database()  # Singleton

# handlers/employees.py
from database import db_instance

async def manage_action(update, context):
    employees = db_instance.get_all_employees()
    # ...
```

**Вариант 2: Context.bot_data**
```python
# bot.py
application.bot_data['db'] = Database()

# handlers/employees.py
async def manage_action(update, context):
    db = context.bot_data['db']
    employees = db.get_all_employees()
    # ...
```

**Рекомендация:** Вариант 1 (проще и понятнее)

**Результат:**
- bot.py сокращается до 100 строк
- Удаление всех wrapper'ов
- Упрощение кода

---

### Фаза 4: Оптимизация handlers/employees.py

#### Приоритет: СРЕДНИЙ
#### Время: 2-3 часа

**Цель:** Сократить 753 строки

**Проблемы:**
- Дублирование логики добавления/списания
- Повторяющиеся паттерны валидации
- Длинные функции

**Решения:**

1. **Создать handlers/employees/materials.py**
   - Вынести управление материалами

2. **Создать handlers/employees/routers.py**
   - Вынести управление роутерами

3. **Создать handlers/employees/crud.py**
   - Вынести CRUD сотрудников

4. **Использовать utils/validators.py**
   - Заменить ручную валидацию

**Результат:**
```
handlers/employees/
├── __init__.py
├── conversation.py
├── crud.py
├── materials.py
└── routers.py
```

---

### Фаза 5: Устранение дублирования

#### Приоритет: НИЗКИЙ
#### Время: 1-2 часа

**Паттерны дублирования:**

1. **Обработка отмены**
   ```python
   # Повторяется в каждом handler'е
   if text == "❌ Отмена":
       context.user_data.clear()
       await update.message.reply_text(...)
       return ConversationHandler.END
   ```
   
   **Решение:**
   ```python
   # utils/handlers_common.py
   async def handle_cancel(update, context):
       context.user_data.clear()
       await update.message.reply_text(
           CANCEL_TEXT,
           reply_markup=get_main_keyboard()
       )
       return ConversationHandler.END
   
   # В handlers
   if Validator.is_cancel_command(text):
       return await handle_cancel(update, context)
   ```

2. **Создание клавиатур с отменой**
   ```python
   # Повторяется часто
   keyboard = [[KeyboardButton("❌ Отмена")]]
   reply_markup = ReplyKeyboardMarkup(keyboard, ...)
   ```
   
   **Решение:**
   ```python
   # utils/keyboards.py
   def get_cancel_keyboard() -> ReplyKeyboardMarkup:
       keyboard = [[KeyboardButton("❌ Отмена")]]
       return ReplyKeyboardMarkup(
           keyboard, 
           resize_keyboard=True, 
           one_time_keyboard=False
       )
   ```

3. **Валидация чисел**
   ```python
   # Повторяется в разных местах
   try:
       value = float(text.replace(',', '.'))
       if value < 0:
           raise ValueError
       # ...
   except ValueError:
       await update.message.reply_text("...")
       return SAME_STATE
   ```
   
   **Решение:** Использовать `Validator.validate_number()`

---

### Фаза 6: Тестирование

#### Приоритет: СРЕДНИЙ
#### Время: 4-5 часов

**Создать тесты для:**

1. **utils/validators.py**
   ```python
   def test_validate_number_positive():
       valid, value, _ = Validator.validate_number("100")
       assert valid == True
       assert value == 100
   
   def test_validate_number_negative():
       valid, _, error = Validator.validate_number("-10")
       assert valid == False
   ```

2. **database/repositories/**
   - Использовать :memory: БД для тестов
   - Проверить CRUD операции
   - Проверить транзакции

3. **handlers/** (интеграционные тесты)
   - Использовать pytest-telegram
   - Тестировать потоки диалогов

**Структура:**
```
tests/
├── test_validators.py
├── test_formatters.py
├── test_repositories.py
├── test_handlers_connection.py
├── test_handlers_employees.py
└── fixtures/
    └── database.py
```

---

## Метрики успеха

### До рефакторинга
| Файл | Строки | Проблемы |
|------|--------|----------|
| handlers/connection.py | 1162 | Monolithic |
| database.py | 871 | Monolithic |
| handlers/employees.py | 753 | Длинный |
| bot.py | 214 | Wrapper'ы |

### После рефакторинга (цель)
| Модуль | Строки | Улучшения |
|--------|--------|-----------|
| handlers/connection/* | 6 файлов × ~200 строк | Модульность |
| database/* | 5 файлов × ~150 строк | Repository Pattern |
| handlers/employees/* | 4 файла × ~200 строк | Разделение |
| bot.py | ~100 строк | Без wrapper'ов |

### Качественные метрики
- ✅ Разделение ответственности
- ✅ Тестируемость (>80% coverage)
- ✅ Переиспользование кода
- ✅ Понятная структура
- ✅ Легкость расширения

---

## Приоритеты реализации

### Немедленно (Critical)
1. ✅ Создать utils/validators.py
2. ✅ Создать utils/formatters.py
3. ✅ Создать структуру directories

### Скоро (High)
4. Разделить handlers/connection.py
5. Создать репозитории для database.py
6. Использовать validators в существующих handlers

### Потом (Medium)
7. Dependency Injection
8. Оптимизировать handlers/employees.py
9. Устранить дублирование

### Когда будет время (Low)
10. Написать тесты
11. Добавить type hints
12. CI/CD pipeline

---

## Рекомендации

### При реализации

1. **Постепенность**
   - Рефакторить по одному модулю
   - Тестировать после каждого изменения
   - Не ломать существующий функционал

2. **Тестирование**
   - Запускать бота после каждого изменения
   - Проверять критические потоки
   - Писать unit тесты

3. **Документация**
   - Обновлять MODULE_GUIDE.md
   - Добавлять docstrings
   - Комментировать сложный код

4. **Git**
   - Делать коммиты после каждой фазы
   - Писать осмысленные commit messages
   - Создавать ветки для больших изменений

### Безопасность

- ⚠️ Создавать backup БД перед рефакторингом
- ⚠️ Тестировать на тестовой БД
- ⚠️ Не удалять старый код сразу (комментировать)

---

## Заключение

Этот план рефакторинга направлен на:
- 📦 **Модульность** - разделение на логические компоненты
- 🧪 **Тестируемость** - упрощение написания тестов
- 📚 **Читаемость** - понятная структура кода
- 🔧 **Поддерживаемость** - легкость внесения изменений
- 🚀 **Масштабируемость** - возможность роста

Следование этому плану позволит создать качественную кодовую базу, которая будет легко поддерживаться и расширяться в будущем.

