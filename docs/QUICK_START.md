# 🚀 Быстрый старт после рефакторинга

## Что нового?

### ✅ Созданные модули

1. **utils/validators.py** - Валидация данных
2. **utils/formatters.py** - Форматирование текстов
3. **database/base_repository.py** - Базовый репозиторий
4. **handlers/connection/** - Модульная структура

### ✅ Документация

1. **docs/ARCHITECTURE.md** - Архитектура проекта
2. **docs/MODULE_GUIDE.md** - Руководство по модулям
3. **docs/REFACTORING_PLAN.md** - План рефакторинга
4. **docs/README.md** - Навигация

---

## Как использовать новые модули

### Валидация данных

```python
from utils.validators import Validator

# Валидация числа
valid, value, error = Validator.validate_number(text, min_value=0)
if not valid:
    await update.message.reply_text(error)
    return SAME_STATE

# Валидация целого числа
valid, value, error = Validator.validate_integer(text, min_value=1)
if not valid:
    await update.message.reply_text(error)
    return SAME_STATE

# Проверка команды отмены
if Validator.is_cancel_command(text):
    return await cancel_handler(update, context)

# Проверка пропущенного значения
if Validator.is_skip_value(router_model):
    router_display = "-"
```

### Форматирование текстов

```python
from utils.formatters import TextFormatter, MessageBuilder

# Форматирование роутера
router_info = TextFormatter.format_router_info("TP-Link", quantity=2)
# Результат: "TP-Link (2 шт.)"

# Форматирование порта
port_display = TextFormatter.format_port(port)
# Результат: "8" или "-" если пропущено

# Форматирование статуса
status = TextFormatter.format_contract_status(signed=True)
# Результат: "✅ Подписан"

# Построение сложного сообщения
message = MessageBuilder.build_confirmation_message(
    connection_type='mkd',
    address='г. Москва, ул. Ленина, 1',
    router_model='TP-Link',
    router_quantity=1,
    port='8',
    fiber=100.0,
    twisted=50.0,
    contract_signed=True,
    employees=['Иванов И.И.', 'Петров П.П.'],
    payer_info='\n💰 Материалы: Иванов И.И.'
)
await update.message.reply_text(message)
```

### Работа с репозиториями

```python
from database.base_repository import BaseRepository

class MyRepository(BaseRepository):
    def get_all(self):
        return self.execute_query(
            "SELECT * FROM my_table",
            fetch_all=True
        )
    
    def get_by_id(self, id):
        return self.execute_query(
            "SELECT * FROM my_table WHERE id = ?",
            params=(id,),
            fetch_one=True
        )
    
    def create(self, data):
        return self.execute_query(
            "INSERT INTO my_table (field) VALUES (?)",
            params=(data,)
        )
```

---

## Следующие шаги

### 1. Применить в существующем коде

Замените ручную валидацию на `Validator`:

**Было:**
```python
try:
    fiber_meters = float(text.replace(',', '.'))
    if fiber_meters < 0:
        raise ValueError
    # ...
except ValueError:
    await update.message.reply_text(
        "⚠️ Пожалуйста, введите корректное число"
    )
    return ENTER_FIBER
```

**Стало:**
```python
from utils.validators import Validator

valid, fiber_meters, error = Validator.validate_number(text, min_value=0)
if not valid:
    await update.message.reply_text(error)
    return ENTER_FIBER
```

### 2. Следуйте плану рефакторинга

См. `docs/REFACTORING_PLAN.md` для детального плана из 6 фаз.

### 3. Изучите документацию

- `docs/ARCHITECTURE.md` - понимание структуры
- `docs/MODULE_GUIDE.md` - работа с модулями
- `docs/README.md` - навигация

---

## Важно знать

### Обратная совместимость
Все существующие функции работают без изменений. Новые модули - это дополнение, а не замена.

### Постепенное внедрение
Можно применять новые модули постепенно, функция за функцией.

### Тестирование
После каждого изменения тестируйте бота на реальных сценариях.

---

## Помощь

**Вопросы?** См. `docs/README.md` для навигации по документации

**Проблемы?** Проверьте `docs/MODULE_GUIDE.md` для примеров использования

**Рефакторинг?** Следуйте `docs/REFACTORING_PLAN.md`

---

*Удачи в разработке!* 🚀

