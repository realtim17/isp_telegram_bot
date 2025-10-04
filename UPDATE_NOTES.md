# 🔄 Инструкция по обновлению до версии 1.1.0

## 📋 Что нового

В версии 1.1.0 добавлена функция **автоматической отправки отчетов с фотографиями** пользователю сразу после создания отчета.

### Новые возможности:

✅ После создания отчета пользователь получает красиво отформатированное сообщение  
✅ Фотографии отправляются как альбом (медиа-группа)  
✅ Первое фото содержит полное описание отчета  
✅ Поддержка отчетов без фотографий  

## 🚀 Как обновить

### Вариант 1: Автоматический перезапуск (рекомендуется)

Если бот запущен через systemd или docker:

```bash
cd /path/to/isp_telegram_bot

# Обновить код
git pull origin main

# Перезапустить бота
sudo systemctl restart isp_bot

# Или для Docker
docker-compose restart
```

### Вариант 2: Ручное обновление

```bash
# 1. Остановить бота
pkill -f "python.*bot.py"

# 2. Перейти в директорию проекта
cd /path/to/isp_telegram_bot

# 3. Сделать резервную копию (на всякий случай)
cp bot.py bot.py.backup
cp database.py database.py.backup

# 4. Обновить код
git pull origin main

# 5. Убедиться, что зависимости установлены
source venv/bin/activate  # или активируйте ваше виртуальное окружение
pip install -r requirements.txt

# 6. Запустить бота
python bot.py &
```

### Вариант 3: Ручное применение изменений

Если вы не используете git, внесите изменения вручную:

#### 1. Обновить импорты в `bot.py`

В начале файла найдите строку:
```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
```

Замените на:
```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton, InputMediaPhoto
```

#### 2. Добавить функцию `send_connection_report`

Добавьте эту функцию в `bot.py` (после функции `show_confirmation`):

```python
async def send_connection_report(message, connection_id: int, data: Dict, photos: List[str], employee_ids: List[int]) -> None:
    """Отправить красиво отформатированный отчет о подключении с фотографиями"""
    try:
        # Получаем имена сотрудников
        employees = db.get_all_employees()
        employee_names = [emp['full_name'] for emp in employees if emp['id'] in employee_ids]
        
        # Рассчитываем долю на каждого
        emp_count = len(employee_ids)
        fiber_per_emp = round(data['fiber_meters'] / emp_count, 2)
        twisted_per_emp = round(data['twisted_pair_meters'] / emp_count, 2)
        
        # Формируем текст отчета
        report_text = f"""
📋 <b>ОТЧЕТ О ПОДКЛЮЧЕНИИ #{connection_id}</b>

📍 <b>Адрес:</b> {data['address']}
🌐 <b>Модель роутера:</b> {data['router_model']}
🔌 <b>Порт:</b> {data['port']}

📏 <b>Проложенный кабель:</b>
  • ВОЛС: {data['fiber_meters']} м
  • Витая пара: {data['twisted_pair_meters']} м

👥 <b>Исполнители ({emp_count}):</b>
{chr(10).join(['  • ' + name for name in employee_names])}

💡 <b>Расчет на каждого исполнителя:</b>
  • ВОЛС: {fiber_per_emp} м
  • Витая пара: {twisted_per_emp} м

📅 <b>Дата подключения:</b> {datetime.now().strftime('%d.%m.%Y %H:%M')}
"""
        
        if photos:
            # Создаем медиа-группу
            media_group = []
            for idx, photo_id in enumerate(photos):
                if idx == 0:
                    # К первому фото прикрепляем описание
                    media_group.append(InputMediaPhoto(media=photo_id, caption=report_text, parse_mode='HTML'))
                else:
                    media_group.append(InputMediaPhoto(media=photo_id))
            
            # Отправляем альбом
            await message.reply_media_group(media=media_group)
            logger.info(f"Отправлен отчет #{connection_id} с {len(photos)} фото")
        else:
            # Если фото нет, просто отправляем текст
            await message.reply_text(report_text, parse_mode='HTML')
            logger.info(f"Отправлен отчет #{connection_id} без фото")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке отчета о подключении: {e}")
        await message.reply_text(
            "⚠️ Отчет создан, но возникла ошибка при отправке фотографий.",
            parse_mode='HTML'
        )
```

#### 3. Обновить функцию `confirm_connection`

Найдите строки в функции `confirm_connection`:
```python
if connection_id:
    await query.edit_message_text(
        f"✅ <b>Отчет успешно создан!</b>\n\n"
        f"ID подключения: #{connection_id}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode='HTML'
    )
    
    await query.message.reply_text(
        "Выберите следующее действие:",
        reply_markup=get_main_keyboard()
    )
```

Замените на:
```python
if connection_id:
    await query.edit_message_text(
        f"✅ <b>Отчет успешно создан!</b>\n\n"
        f"ID подключения: #{connection_id}\n"
        f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
        parse_mode='HTML'
    )
    
    # Отправляем отчет с фотографиями
    await send_connection_report(query.message, connection_id, data, photos, selected_employees)
    
    await query.message.reply_text(
        "Выберите следующее действие:",
        reply_markup=get_main_keyboard()
    )
```

## ✅ Проверка обновления

После перезапуска бота:

1. Создайте тестовый отчет с фотографиями
2. После подтверждения вы должны получить:
   - Сообщение об успешном создании
   - Альбом с фотографиями и описанием отчета
3. Если фото не загружали - получите только текстовый отчет

## 🔍 Проверка логов

```bash
tail -f bot.log
```

Вы должны увидеть строки типа:
```
INFO - Отправлен отчет #42 с 3 фото
```

## ⚠️ Возможные проблемы

### Ошибка: ModuleNotFoundError: No module named 'telegram'

**Решение:**
```bash
source venv/bin/activate
pip install python-telegram-bot==21.0
```

### Ошибка: name 'InputMediaPhoto' is not defined

**Решение:** Не забыли обновить импорты в начале файла `bot.py`

### Фотографии не отправляются

**Возможные причины:**
1. Проблемы с Telegram API (временные)
2. Недостаточно прав у бота
3. Неверные file_id фотографий

**Решение:** Проверьте логи для деталей ошибки

## 🔄 Откат к предыдущей версии

Если что-то пошло не так:

```bash
# Остановить бота
pkill -f "python.*bot.py"

# Восстановить резервную копию
cp bot.py.backup bot.py
cp database.py.backup database.py

# Запустить снова
python bot.py &
```

## 📞 Поддержка

При возникновении проблем:
1. Проверьте логи: `tail -f bot.log`
2. Убедитесь, что все зависимости установлены
3. Проверьте, что бот работает и отвечает на команды

## 📊 Статистика обновления

- ✅ Обратная совместимость: Да
- ✅ Требуется миграция БД: Нет
- ✅ Требуются новые зависимости: Нет
- ✅ Требуется изменение .env: Нет

**Обновление безопасно и не требует изменения базы данных или конфигурации.**

---

**Обновление до версии 1.1.0 завершено!** 🎉

Теперь ваш бот автоматически отправляет красиво отформатированные отчеты с фотографиями пользователям.
