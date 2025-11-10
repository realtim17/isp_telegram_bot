"""
Конфигурация бота и константы
"""
import os
import logging
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Константы состояний для ConversationHandler
# Создание подключения
SELECT_CONNECTION_TYPE = 0
UPLOAD_PHOTOS = 1
ENTER_ADDRESS = 2
SELECT_ROUTER = 3
ENTER_PORT = 4
ENTER_FIBER = 5
ENTER_TWISTED = 6
SELECT_EMPLOYEES = 7
SELECT_MATERIAL_PAYER = 8
SELECT_ROUTER_PAYER = 9
CONFIRM = 10

# Управление сотрудниками
MANAGE_ACTION = 11
ADD_EMPLOYEE_NAME = 12
DELETE_EMPLOYEE_SELECT = 13
SELECT_EMPLOYEE_FOR_MATERIAL = 14
SELECT_MATERIAL_ACTION = 15
ENTER_FIBER_AMOUNT = 16
ENTER_TWISTED_AMOUNT = 17
SELECT_EMPLOYEE_FOR_ROUTER = 18
SELECT_ROUTER_ACTION = 19
ENTER_ROUTER_NAME = 20
ENTER_ROUTER_QUANTITY = 21

# Отчеты
SELECT_REPORT_EMPLOYEE = 22
SELECT_REPORT_PERIOD = 23

# Типы подключений
CONNECTION_TYPES = {
    'mkd': 'МКД',
    'chs': 'ЧС',
    'legal': 'Юр / Гос'
}


# Токен бота
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Загрузка ID администраторов
ADMIN_IDS = [int(id.strip()) for id in os.getenv('ADMIN_USER_IDS', '').split(',') if id.strip()]

# ID канала для отправки отчетов (опционально)
REPORTS_CHANNEL_ID = os.getenv('REPORTS_CHANNEL_ID', '').strip()
if REPORTS_CHANNEL_ID:
    try:
        REPORTS_CHANNEL_ID = int(REPORTS_CHANNEL_ID)
        logger.info(f"Канал для отчетов настроен: {REPORTS_CHANNEL_ID}")
    except ValueError:
        REPORTS_CHANNEL_ID = None
        logger.warning("REPORTS_CHANNEL_ID имеет неверный формат")
else:
    REPORTS_CHANNEL_ID = None


def is_admin(user_id: int) -> bool:
    """Проверка, является ли пользователь администратором"""
    return user_id in ADMIN_IDS

