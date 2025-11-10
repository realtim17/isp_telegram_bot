# 🛠️ Руководство разработчика

## Обзор архитектуры

Бот построен на модульной архитектуре с чёткимразделением ответственности.

### Основные компоненты

```
bot.py              # Точка входа, инициализация Application
├── config.py       # Конфигурация, константы, переменные окружения
├── database.py     # Работа с SQLite БД
├── report_generator.py  # Генерация Excel отчётов
├── handlers/       # Обработчики команд и ConversationHandlers
│   ├── commands.py      # /start, /help, /cancel
│   ├── connection.py    # Создание подключений (8 шагов)
│   ├── reports.py       # Генерация отчётов
│   └── employees.py     # Управление сотрудниками
└── utils/          # Вспомогательные функции
    ├── keyboards.py     # Telegram клавиатуры
    └── helpers.py       # Отправка отчётов, форматирование
```

## Модули системы

### 1. bot.py - Главный модуль

**Назначение:** Инициализация и запуск бота

**Ключевые функции:**
- Создание `Application`
- Регистрация всех handlers
- Настройка фильтров
- Запуск polling

**Пример:**
```python
def main():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Регистрация handlers
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(connection_conv)
    application.add_handler(report_conv)
    application.add_handler(manage_conv)
    
    application.run_polling(allowed_updates=Update.ALL_TYPES)
```

### 2. config.py - Конфигурация

**Назначение:** Централизованное хранение настроек

**Содержит:**
- Константы состояний ConversationHandler
- Токен бота и ID администраторов
- ID канала для отчётов
- Типы подключений
- Настройки логирования

**Пример:**
```python
# Состояния ConversationHandler
SELECT_CONNECTION_TYPE = 0
UPLOAD_PHOTOS = 1
ENTER_ADDRESS = 2
# ...

# Типы подключений
CONNECTION_TYPES = {
    'mkd': 'МКД',
    'chs': 'ЧС',
    'legal': 'Юр / Гос'
}
```

### 3. database.py - Работа с БД

**Назначение:** Абстракция работы с SQLite

**Основные методы:**

```python
class Database:
    # Сотрудники
    def get_all_employees() -> List[Dict]
    def add_employee(full_name: str) -> Optional[int]
    def delete_employee(employee_id: int) -> bool
    
    # Подключения
    def create_connection(...) -> Optional[int]
    def get_connection_by_id(connection_id: int) -> Optional[Dict]
    def get_connections_by_employee(...) -> List[Dict]
    
    # Фотографии
    def get_connection_photos(connection_id: int) -> List[str]
```

**Структура БД:**

```sql
-- Сотрудники
CREATE TABLE employees (
    id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Подключения
CREATE TABLE connections (
    id INTEGER PRIMARY KEY,
    connection_type TEXT NOT NULL,
    address TEXT NOT NULL,
    router_model TEXT NOT NULL,
    port TEXT NOT NULL,
    fiber_meters REAL NOT NULL,
    twisted_pair_meters REAL NOT NULL,
    created_by INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Связь подключений и сотрудников
CREATE TABLE connection_employees (
    connection_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    PRIMARY KEY (connection_id, employee_id),
    FOREIGN KEY (connection_id) REFERENCES connections(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Фотографии
CREATE TABLE connection_photos (
    id INTEGER PRIMARY KEY,
    connection_id INTEGER NOT NULL,
    photo_file_id TEXT NOT NULL,
    photo_category TEXT NOT NULL DEFAULT 'general',
    photo_order INTEGER NOT NULL,
    FOREIGN KEY (connection_id) REFERENCES connections(id)
);
```

### 4. handlers/ - Обработчики

#### handlers/commands.py

Базовые команды:
- `start_command` - приветствие и главное меню
- `help_command` - справка
- `cancel_command` - отмена операции

#### handlers/connection.py

**ConversationHandler для создания подключений (8 шагов):**

1. `SELECT_CONNECTION_TYPE` - выбор типа (МКД/ЧС/Юр)
2. `UPLOAD_PHOTOS` - загрузка фото (до 10 штук)
3. `ENTER_ADDRESS` - ввод адреса
4. `ENTER_ROUTER` - модель роутера
5. `ENTER_PORT` - номер порта
6. `ENTER_FIBER` - метраж ВОЛС
7. `ENTER_TWISTED` - метраж витой пары
8. `SELECT_EMPLOYEES` - выбор исполнителей
9. `CONFIRM` - подтверждение

**Ключевые функции:**
```python
async def new_connection_start(update, context) -> int
async def select_connection_type(update, context) -> int
async def upload_photos(update, context) -> int
async def enter_address(update, context) -> int
# ... и т.д.
```

#### handlers/reports.py

Генерация сводных отчётов:
- Выбор сотрудника
- Выбор периода (неделя/месяц/всё время)
- Генерация Excel файла

#### handlers/employees.py

Управление сотрудниками (только для админов):
- Добавление сотрудника
- Удаление сотрудника
- Просмотр списка

### 5. utils/ - Утилиты

#### utils/keyboards.py

Генерация Telegram клавиатур:
```python
def get_main_keyboard() -> ReplyKeyboardMarkup
    # Главное меню с кнопками
```

#### utils/helpers.py

Вспомогательные функции:
```python
async def send_connection_report(message, connection_id, data, photos, employee_ids, db)
    # Отправка отчёта с фотографиями
```

### 6. report_generator.py

Генерация Excel отчётов:
```python
class ReportGenerator:
    def generate_employee_report(employee_id, start_date, end_date) -> str
        # Создаёт Excel файл с отчётом
```

## Добавление нового функционала

### Пример: Добавление нового типа подключения

1. **Обновить config.py:**
```python
CONNECTION_TYPES = {
    'mkd': 'МКД',
    'chs': 'ЧС',
    'legal': 'Юр / Гос',
    'new_type': 'Новый тип'  # ← добавить
}
```

2. **Обновить handlers/connection.py:**
```python
keyboard = [
    [InlineKeyboardButton("1️⃣ МКД", callback_data='conn_type_mkd')],
    [InlineKeyboardButton("2️⃣ ЧС", callback_data='conn_type_chs')],
    [InlineKeyboardButton("3️⃣ Юр / Гос", callback_data='conn_type_legal')],
    [InlineKeyboardButton("4️⃣ Новый тип", callback_data='conn_type_new_type')]  # ← добавить
]
```

3. **Протестировать:**
```bash
python bot.py
# Создать тестовое подключение с новым типом
```

### Пример: Добавление нового поля в отчёт

1. **Обновить БД (database.py):**
```python
cursor.execute("""
    ALTER TABLE connections 
    ADD COLUMN new_field TEXT
""")
```

2. **Обновить create_connection:**
```python
def create_connection(self, ..., new_field: str):
    cursor.execute("""
        INSERT INTO connections (..., new_field)
        VALUES (..., ?)
    """, (..., new_field))
```

3. **Добавить шаг в ConversationHandler:**
```python
# В config.py
ENTER_NEW_FIELD = 9  # новое состояние

# В handlers/connection.py
async def enter_new_field(update, context):
    new_field = update.message.text.strip()
    context.user_data['connection_data']['new_field'] = new_field
    # переход к следующему шагу
```

4. **Обновить отчёт (utils/helpers.py):**
```python
report_text = f"""
...
🆕 <b>Новое поле:</b> {data['new_field']}
...
"""
```

## Лучшие практики

### 1. Обработка ошибок

```python
try:
    connection_id = db.create_connection(...)
    if connection_id:
        await send_success_message()
    else:
        await send_error_message()
except Exception as e:
    logger.error(f"Ошибка: {e}")
    await send_error_message()
```

### 2. Логирование

```python
import logging
logger = logging.getLogger(__name__)

logger.info("Создано подключение #123")
logger.warning("Сотрудник не найден")
logger.error(f"Ошибка БД: {e}")
```

### 3. Валидация данных

```python
try:
    fiber_meters = float(update.message.text.strip().replace(',', '.'))
    if fiber_meters < 0:
        raise ValueError
except ValueError:
    await update.message.reply_text("⚠️ Введите корректное число")
    return ENTER_FIBER
```

### 4. ConversationHandler

- Всегда возвращайте следующее состояние
- Используйте `context.user_data` для хранения данных
- Очищайте `context.user_data.clear()` в конце
- Добавляйте fallbacks для отмены

### 5. Тестирование

```python
# Перед коммитом:
1. Проверить линтер: read_lints
2. Запустить бота: python bot.py
3. Протестировать новый функционал
4. Проверить логи на ошибки
5. Проверить что старый функционал работает
```

## Отладка

### Просмотр логов

```bash
# Все логи
cat bot.log

# Последние 50 строк
tail -50 bot.log

# Только ошибки
grep -i error bot.log

# В реальном времени
tail -f bot.log
```

### Проверка БД

```bash
sqlite3 isp_bot.db

# Посмотреть таблицы
.tables

# Посмотреть сотрудников
SELECT * FROM employees;

# Посмотреть подключения
SELECT * FROM connections ORDER BY created_at DESC LIMIT 10;
```

### Дебаг ConversationHandler

Добавьте логирование в каждый handler:

```python
async def enter_address(update, context):
    logger.info(f"enter_address: user_data={context.user_data}")
    # ... остальной код
```

## Полезные ссылки

- [python-telegram-bot документация](https://docs.python-telegram-bot.org/)
- [Telegram Bot API](https://core.telegram.org/bots/api)
- [SQLite документация](https://www.sqlite.org/docs.html)
- [openpyxl документация](https://openpyxl.readthedocs.io/)

## Структура ConversationHandler

```python
ConversationHandler(
    entry_points=[
        # Точки входа - как начать разговор
        MessageHandler(filters.Regex('^📝 Новое подключение$'), start_handler)
    ],
    states={
        # Состояния и их обработчики
        STATE_1: [MessageHandler(filters.TEXT, handler_1)],
        STATE_2: [CallbackQueryHandler(handler_2, pattern='^data_')],
    },
    fallbacks=[
        # Выходы из разговора
        CommandHandler('cancel', cancel_handler)
    ]
)
```

## Типичные ошибки и решения

### 1. ConversationHandler не работает

**Проблема:** Handler не реагирует на сообщения

**Решение:**
- Проверьте, что возвращаете правильное состояние
- Проверьте фильтры в states
- Убедитесь, что handler зарегистрирован в bot.py

### 2. База данных заблокирована

**Проблема:** `database is locked`

**Решение:**
```python
# Всегда закрывайте соединения
conn = self.get_connection()
try:
    # работа с БД
finally:
    conn.close()
```

### 3. Фото не отправляются

**Проблема:** Ошибка при отправке media_group

**Решение:**
- Проверьте, что file_id валидны
- Максимум 10 фото в группе
- Используйте InputMediaPhoto

---

Для получения дополнительной информации см.:
- [Примеры кода](EXAMPLES.md)
- [Диаграмма модулей](MODULE_DIAGRAM.txt)
- [Процесс подключения](NEW_CONNECTION_FLOW.txt)


