# 🏗️ Архитектура проекта

Техническая документация бота для интернет-провайдера.

## 📐 Общая структура

Проект построен по модульному принципу с разделением ответственности между компонентами.

```
┌─────────────────────────────────────────────────────────┐
│                    Telegram API                         │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────────────────┐
│                    bot.py                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Handlers   │  │Conversation  │  │  Keyboards   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└──────────┬────────────────────┬─────────────────────────┘
           │                    │
           ▼                    ▼
┌──────────────────┐  ┌──────────────────┐
│   database.py    │  │report_generator.py│
│  ┌────────────┐  │  │  ┌────────────┐  │
│  │  SQLite    │  │  │  │  openpyxl  │  │
│  └────────────┘  │  │  └────────────┘  │
└──────────────────┘  └──────────────────┘
```

## 📦 Модули

### 1. bot.py - Главный модуль

**Назначение:** Обработка взаимодействия с пользователями через Telegram API.

**Основные компоненты:**

#### ConversationHandler'ы
- `connection_conv` - создание отчета о подключении
- `report_conv` - формирование сводных отчетов
- `manage_conv` - управление сотрудниками

#### Состояния диалогов

**Создание подключения:**
```python
UPLOAD_PHOTOS      # Загрузка фотографий
ENTER_ADDRESS      # Ввод адреса
ENTER_ROUTER       # Ввод модели роутера
ENTER_PORT         # Ввод порта
ENTER_FIBER        # Ввод метража ВОЛС
ENTER_TWISTED      # Ввод метража витой пары
SELECT_EMPLOYEES   # Выбор исполнителей
CONFIRM           # Подтверждение
```

**Отчеты:**
```python
SELECT_REPORT_EMPLOYEE  # Выбор сотрудника
SELECT_REPORT_PERIOD    # Выбор периода
```

**Управление сотрудниками:**
```python
MANAGE_ACTION            # Выбор действия
ADD_EMPLOYEE_NAME        # Ввод имени сотрудника
DELETE_EMPLOYEE_SELECT   # Выбор сотрудника для удаления
```

#### Ключевые функции

```python
async def new_connection_start()      # Начало создания отчета
async def upload_photos()             # Обработка фото
async def confirm_connection()        # Сохранение в БД
async def send_connection_report()    # Отправка отчета с фото
async def report_generate()           # Генерация Excel
async def manage_employees_start()    # Управление сотрудниками
```

### 2. database.py - Работа с БД

**Назначение:** Абстракция работы с SQLite базой данных.

#### Структура БД

**Таблица: employees**
```sql
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL UNIQUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**Таблица: connections**
```sql
CREATE TABLE connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    address TEXT NOT NULL,
    router_model TEXT NOT NULL,
    port TEXT NOT NULL,
    fiber_meters REAL NOT NULL,
    twisted_pair_meters REAL NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL
)
```

**Таблица: connection_employees** (связь многие-ко-многим)
```sql
CREATE TABLE connection_employees (
    connection_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    PRIMARY KEY (connection_id, employee_id),
    FOREIGN KEY (connection_id) REFERENCES connections(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
)
```

**Таблица: connection_photos**
```sql
CREATE TABLE connection_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id INTEGER NOT NULL,
    photo_file_id TEXT NOT NULL,
    photo_order INTEGER NOT NULL,
    FOREIGN KEY (connection_id) REFERENCES connections(id)
)
```

#### Основные методы

**Сотрудники:**
```python
add_employee(full_name)              # Добавить
get_all_employees()                  # Получить всех
get_employee_by_id(id)               # Получить по ID
delete_employee(id)                  # Удалить
```

**Подключения:**
```python
create_connection(...)               # Создать
get_connection_by_id(id)             # Получить по ID
get_employee_report(emp_id, days)    # Отчет по сотруднику
```

### 3. report_generator.py - Генерация отчетов

**Назначение:** Создание Excel-отчетов с форматированием.

#### Класс ReportGenerator

```python
@staticmethod
def generate_employee_report(
    employee_name: str,
    connections: List[Dict],
    stats: Dict,
    period_name: str
) -> str
```

**Возвращает:** Путь к созданному Excel-файлу

#### Структура Excel-отчета

1. **Заголовок** - название, сотрудник, период
2. **Таблица данных:**
   - Номер по порядку
   - Список исполнителей
   - Адрес подключения
   - Модель роутера
   - Порт
   - Метраж ВОЛС
   - Метраж витой пары
   - Дата подключения
3. **Итоги:**
   - Итого общее (сумма по всем подключениям)
   - Итого для сотрудника (с учетом деления)

#### Стилизация

- Цветные заголовки (синий фон, белый текст)
- Границы ячеек
- Выравнивание текста
- Числовой формат для метража
- Зеленая заливка для итоговой строки

## 🔄 Поток данных

### Создание отчета

```
┌──────────────┐
│ Пользователь │
└──────┬───────┘
       │ /new
       ▼
┌─────────────────┐
│ upload_photos() │
└──────┬──────────┘
       │ photos[]
       ▼
┌──────────────────┐
│ enter_address()  │
│ enter_router()   │
│ enter_port()     │
│ enter_fiber()    │
│ enter_twisted()  │
└──────┬───────────┘
       │ connection_data{}
       ▼
┌──────────────────────┐
│ select_employees()   │
└──────┬───────────────┘
       │ selected_employees[]
       ▼
┌──────────────────────┐
│ confirm_connection() │
└──────┬───────────────┘
       │
       ▼
┌──────────────────────┐
│ db.create_connection │
└──────┬───────────────┘
       │ connection_id
       ▼
┌────────────────────────┐
│ send_connection_report │
├────────────────────────┤
│ 1. Отправка пользов.   │
│ 2. Отправка в канал    │
└────────────────────────┘
```

### Формирование сводного отчета

```
┌──────────────┐
│ Пользователь │
└──────┬───────┘
       │ /report
       ▼
┌─────────────────────┐
│ Выбор сотрудника    │
└──────┬──────────────┘
       │ employee_id
       ▼
┌─────────────────────┐
│ Выбор периода       │
└──────┬──────────────┘
       │ days
       ▼
┌─────────────────────────┐
│ db.get_employee_report  │
└──────┬──────────────────┘
       │ connections[], stats{}
       ▼
┌───────────────────────────────┐
│ ReportGenerator.generate...() │
└──────┬────────────────────────┘
       │ filename.xlsx
       ▼
┌──────────────────┐
│ Отправка файла   │
└──────────────────┘
```

## 🔐 Безопасность

### Аутентификация администраторов

```python
ADMIN_IDS = [int(id) for id in os.getenv('ADMIN_USER_IDS').split(',')]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS
```

Проверка выполняется в начале функций управления сотрудниками.

### Защита данных

- **Токен бота** хранится в `.env` (не коммитится в git)
- **База данных** локальная, без внешнего доступа
- **Фотографии** хранятся на серверах Telegram (file_id)

## 📱 Интерфейс пользователя

### Главная клавиатура

```python
[📝 Новое подключение]
[📊 Сводный отчет]
[👥 Управление сотрудниками]
[ℹ️ Помощь]
```

### Inline-клавиатуры

- Выбор сотрудников (чекбоксы)
- Подтверждение действий
- Выбор периода отчета
- Управление сотрудниками

## 🔄 Обработка ошибок

### Уровни логирования

```python
logger.info()     # Успешные операции
logger.warning()  # Предупреждения
logger.error()    # Ошибки
```

### Обработка исключений

- `try-except` блоки во всех критичных функциях
- Информативные сообщения пользователю
- Логирование всех ошибок

## 🚀 Производительность

### Оптимизация БД

- Индексы на внешних ключах
- `row_factory = sqlite3.Row` для удобного доступа
- Закрытие соединений после операций

### Асинхронность

- Все обработчики - `async def`
- Использование `await` для IO операций
- `Application.run_polling()` для получения обновлений

## 📊 Масштабируемость

### Текущие ограничения

- SQLite (однопользовательский режим)
- Локальное хранение данных
- Одна инстанция бота

### Возможные улучшения

1. **PostgreSQL** вместо SQLite для многопользовательского режима
2. **Redis** для кеширования
3. **Webhook** вместо polling для больших нагрузок
4. **Celery** для фоновых задач (генерация больших отчетов)

## 🧪 Тестирование

### Покрытие тестами

- ✅ database.py - юнит-тесты
- ⏳ bot.py - интеграционные тесты (TODO)
- ⏳ report_generator.py - тесты генерации (TODO)

### Запуск тестов

```bash
python test_database.py
```

## 📦 Зависимости

```
python-telegram-bot==21.0  # Telegram Bot API
python-dotenv==1.0.0       # Переменные окружения
openpyxl==3.1.2            # Excel генерация
Pillow==10.2.0             # Обработка изображений
```

## 🔧 Конфигурация

### Переменные окружения (.env)

```env
TELEGRAM_BOT_TOKEN=       # Обязательно
ADMIN_USER_IDS=           # Обязательно
REPORTS_CHANNEL_ID=       # Опционально
```

### Константы в коде

```python
MAX_PHOTOS = 10           # Максимум фото на отчет
DB_PATH = "isp_bot.db"    # Путь к БД
```

## 📈 Мониторинг

### Логи

- Консольный вывод
- Файл `bot.log`
- Формат: timestamp, уровень, сообщение

### Метрики для отслеживания

- Количество созданных отчетов
- Количество пользователей
- Ошибки и исключения
- Время генерации отчетов

---

**Документ актуален для версии 1.2.0**
