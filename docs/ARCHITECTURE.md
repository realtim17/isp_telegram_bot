# Архитектура проекта ISP Telegram Bot

## Обзор

Telegram-бот для автоматизации отчетности по подключению новых абонентов интернет-провайдера.

## Архитектурный паттерн

Проект использует **многослойную архитектуру** с разделением ответственности:

```
┌─────────────────────────────────────────┐
│           Telegram Bot API              │
│         (python-telegram-bot)           │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│          Presentation Layer             │
│         (handlers/, bot.py)             │
│  - Обработка команд и callback          │
│  - Управление состоянием диалогов       │
│  - Валидация ввода пользователя         │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│          Business Logic Layer           │
│         (services/, utils/)             │
│  - Форматирование данных                │
│  - Валидация бизнес-правил              │
│  - Генерация отчетов                    │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│          Data Access Layer              │
│    (database/, repositories/)           │
│  - Работа с SQLite                      │
│  - CRUD операции                        │
│  - Логирование изменений                │
└──────────────┬──────────────────────────┘
               │
┌──────────────▼──────────────────────────┐
│            Database                     │
│           (isp_bot.db)                  │
│  - SQLite база данных                   │
└─────────────────────────────────────────┘
```

## Структура директорий

```
isp_telegram_bot/
│
├── bot.py                      # Точка входа приложения
├── config.py                   # Конфигурация и константы
├── requirements.txt            # Зависимости Python
│
├── database/                   # Слой доступа к данным
│   ├── __init__.py
│   ├── db_manager.py          # Основной класс Database
│   ├── base_repository.py     # Базовый репозиторий
│   └── repositories/          # Репозитории по сущностям
│       ├── employee_repository.py
│       ├── connection_repository.py
│       ├── material_repository.py
│       └── router_repository.py
│
├── handlers/                   # Обработчики команд и событий
│   ├── __init__.py
│   ├── commands.py            # Базовые команды (/start, /help)
│   ├── connection/            # Модуль подключений
│   │   ├── __init__.py
│   │   ├── conversation.py    # ConversationHandler
│   │   ├── steps.py           # Шаги создания подключения
│   │   ├── validation.py      # Проверка материалов/роутеров
│   │   ├── confirmation.py    # Подтверждение данных
│   │   └── constants.py       # Константы модуля
│   ├── employees.py           # Управление сотрудниками
│   └── reports.py             # Генерация отчетов
│
├── utils/                      # Вспомогательные модули
│   ├── __init__.py
│   ├── validators.py          # Валидация данных
│   ├── formatters.py          # Форматирование текстов
│   ├── keyboards.py           # Клавиатуры Telegram
│   └── helpers.py             # Вспомогательные функции
│
├── report_generator.py         # Генерация Excel отчетов
│
└── docs/                       # Документация
    ├── ARCHITECTURE.md         # Архитектура (этот файл)
    ├── MODULE_GUIDE.md         # Руководство по модулям
    ├── REFACTORING_PLAN.md     # План рефакторинга
    └── development/            # Документация разработки
```

## Основные компоненты

### 1. Bot Layer (bot.py)

**Ответственность:**
- Инициализация приложения
- Регистрация обработчиков
- Управление жизненным циклом бота

**Ключевые элементы:**
- `Application` - главный объект бота
- `ConversationHandler` - управление диалогами
- Регистрация handlers для команд и событий

### 2. Handlers Layer (handlers/)

**Ответственность:**
- Обработка команд пользователя
- Управление состоянием диалогов
- Валидация ввода

**Модули:**

#### handlers/commands.py
- Базовые команды: `/start`, `/help`, `/cancel`
- Вспомогательные функции

#### handlers/connection/
Модуль создания подключений (рефакторинг из 1163 строк):
- `conversation.py` - ConversationHandler
- `steps.py` - Обработчики шагов (адрес, роутер, порт и т.д.)
- `validation.py` - Проверка материалов и роутеров
- `confirmation.py` - Подтверждение и сохранение
- `constants.py` - Константы и текстовые шаблоны

#### handlers/employees.py
Управление сотрудниками:
- Добавление/удаление сотрудников
- Управление материалами (ВОЛС, витая пара)
- Управление роутерами

#### handlers/reports.py
Генерация отчетов:
- Выбор сотрудника
- Выбор периода
- Генерация Excel файла

### 3. Database Layer (database/)

**Ответственность:**
- Работа с SQLite
- CRUD операции
- Логирование изменений

**Структура:**

#### database/db_manager.py
Основной класс `Database` - фасад для репозиториев

#### database/repositories/
Репозитории по сущностям (паттерн Repository):
- `EmployeeRepository` - сотрудники
- `ConnectionRepository` - подключения
- `MaterialRepository` - материалы
- `RouterRepository` - роутеры

**Преимущества:**
- Разделение ответственности
- Упрощение тестирования
- Повторное использование кода
- Легкость рефакторинга

### 4. Utils Layer (utils/)

**Ответственность:**
- Вспомогательные функции
- Валидация данных
- Форматирование текстов

**Модули:**

#### utils/validators.py
Класс `Validator` с методами:
- `validate_number()` - валидация чисел
- `validate_integer()` - валидация целых чисел
- `validate_text()` - валидация текста
- `is_cancel_command()` - проверка команды отмены
- `is_skip_value()` - проверка пропущенного значения

#### utils/formatters.py
Классы `TextFormatter` и `MessageBuilder`:
- Форматирование типов подключения
- Форматирование информации о роутере
- Форматирование статусов
- Построение сложных сообщений

#### utils/keyboards.py
Фабрики клавиатур Telegram

#### utils/helpers.py
Вспомогательные функции:
- Отправка отчетов
- Работа с фото

### 5. Business Logic (report_generator.py)

**Ответственность:**
- Генерация Excel отчетов
- Форматирование данных для отчетов

## База данных

### Схема БД (SQLite)

```sql
-- Сотрудники
CREATE TABLE employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL UNIQUE,
    fiber_balance REAL DEFAULT 0,
    twisted_pair_balance REAL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Подключения
CREATE TABLE connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_type TEXT NOT NULL DEFAULT 'mkd',
    address TEXT NOT NULL,
    router_model TEXT NOT NULL,
    port TEXT NOT NULL,
    fiber_meters REAL NOT NULL,
    twisted_pair_meters REAL NOT NULL,
    router_quantity INTEGER DEFAULT 1,
    contract_signed INTEGER DEFAULT 0,
    router_access INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER NOT NULL
);

-- Связь подключений и сотрудников (M:N)
CREATE TABLE connection_employees (
    connection_id INTEGER NOT NULL,
    employee_id INTEGER NOT NULL,
    PRIMARY KEY (connection_id, employee_id),
    FOREIGN KEY (connection_id) REFERENCES connections(id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Фотографии подключений
CREATE TABLE connection_photos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    connection_id INTEGER NOT NULL,
    photo_file_id TEXT NOT NULL,
    photo_category TEXT NOT NULL DEFAULT 'other',
    photo_order INTEGER NOT NULL,
    FOREIGN KEY (connection_id) REFERENCES connections(id)
);

-- Роутеры сотрудников
CREATE TABLE employee_routers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    router_name TEXT NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

-- Лог движения материалов
CREATE TABLE material_movement_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    operation_type TEXT NOT NULL,  -- 'add' или 'deduct'
    item_type TEXT NOT NULL,        -- 'fiber', 'twisted_pair', 'router'
    item_name TEXT,
    quantity REAL NOT NULL,
    balance_after REAL,
    connection_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by INTEGER,
    FOREIGN KEY (employee_id) REFERENCES employees(id),
    FOREIGN KEY (connection_id) REFERENCES connections(id)
);
```

## Потоки данных

### Создание нового подключения

```
1. Пользователь → Handlers → Валидация
2. Handlers → Database → Проверка материалов/роутеров
3. Handlers → User → Подтверждение
4. Handlers → Database → Сохранение подключения
5. Database → Логирование изменений
6. Handlers → ReportGenerator → Excel отчет
7. Handlers → User → Отчет с фотографиями
```

### Управление материалами

```
1. Пользователь → Handlers → Выбор сотрудника
2. Handlers → Database → Получение текущих балансов
3. Handlers → User → Отображение балансов
4. User → Handlers → Ввод количества
5. Handlers → Validators → Валидация
6. Handlers → Database → Обновление балансов
7. Database → Логирование операции
```

## Безопасность

### Аутентификация
- Проверка `ADMIN_USER_IDS` из .env
- Функция `is_admin()` в config.py

### Данные
- Локальное хранение SQLite
- Логирование всех операций
- Отслеживание `created_by` для аудита

## Масштабируемость

### Текущие ограничения
- SQLite (однопользовательский режим)
- Синхронная обработка
- Локальное хранение файлов

### Пути развития
1. **БД**: Переход на PostgreSQL для многопользовательского режима
2. **Хранилище**: S3/MinIO для файлов
3. **Очереди**: Celery для асинхронных задач
4. **API**: REST API для интеграции с другими системами
5. **Мониторинг**: Prometheus + Grafana

## Зависимости

### Основные
- `python-telegram-bot` - Telegram Bot API
- `openpyxl` - Генерация Excel
- `python-dotenv` - Конфигурация

### Разработка
- `pytest` - Тестирование
- `black` - Форматирование кода
- `flake8` - Линтинг

## Производительность

### Оптимизации
- Индексы БД на часто используемых полях
- Кэширование списка сотрудников
- Batch операции для фотографий
- Минимизация SQL запросов

### Метрики
- Среднее время создания подключения: ~2-3 минуты
- Размер БД: ~1-5 MB на 1000 подключений
- Concurrent users: 1-10 (SQLite limitation)

## Deployment

### Требования
- Python 3.9+
- SQLite 3
- 100MB диск
- 256MB RAM

### Конфигурация
См. `docs/setup/SETUP_GUIDE.md`

### Мониторинг
- Логи: `bot.log`
- Systemd service: `isp_bot.service`
- Restart script: `RESTART_BOT.sh`

