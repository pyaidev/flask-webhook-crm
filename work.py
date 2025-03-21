from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime, timedelta
import threading
import time
import urllib.parse
import logging

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook.log"),
        logging.StreamHandler()
    ]
)

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Разрешаем кросс-доменные запросы
logger = app.logger

# Словарь для маппинга номера хука на стадию - перемещаем объявление вверх!
HOOK_TO_STAGE = {
    1: "Все сделки",
    2: "Без статуса",
    3: "Без даты",
    4: "Без региона",
    5: "Без суммы",
    6: "Без адреса",
    7: "Все готово",
    8: "МСК",
    9: "СПб",
    10: "Регион",
    11: "Звоним без предоплаты",
    12: "Звоним без предоплаты несколько товаров",
    13: "Подтвердил заказ без предоплаты",
    14: "Отменил заказ без предоплаты",
    15: "Не взял трубку без предоплаты",
    16: "Звоним с предоплатой",
    17: "Звоним с предоплатой несколько товаров",
    18: "Подтвердил заказ с предоплатой",
    19: "Отменил заказ с предоплатой",
    20: "Не взял трубку с предоплатой",
    21: "Звоним регион",
    22: "Подтвердил заказ регион",
    23: "Отменил заказ регион",
    24: "Не взял трубку регион",
    25: "Непонятно"
}

# Мьютекс для защиты доступа к базе данных при одновременных запросах
db_lock = threading.Lock()

# Функция для получения текущей статистической даты
def get_stat_date():
    """
    Возвращает дату для статистики с учетом правила:
    - Если время с 00:00 до 21:00, возвращает текущую дату
    - Если время с 21:01 до 23:59, возвращает следующую дату
    """
    now = datetime.now()
    cutoff_time = now.replace(hour=21, minute=0, second=0, microsecond=0)
    
    # Если текущее время после 21:00, то используем следующую дату
    if now > cutoff_time:
        return (now + timedelta(days=1)).strftime('%Y-%m-%d')
    else:
        return now.strftime('%Y-%m-%d')

def ensure_all_stages_in_db():
    """Убедиться, что все стадии добавлены в базу данных."""
    stat_date = get_stat_date()
    
    with db_lock:
        conn = sqlite3.connect('webhooks.db')
        cursor = conn.cursor()
        
        # Получаем существующие стадии на дату
        cursor.execute(
            "SELECT stage FROM daily_stats WHERE date = ?",
            (stat_date,)
        )
        existing_stages = {row[0] for row in cursor.fetchall()}
        
        # Добавляем отсутствующие стадии с нулевыми значениями
        for stage_id, stage_name in HOOK_TO_STAGE.items():
            if stage_name not in existing_stages:
                cursor.execute(
                    "INSERT INTO daily_stats (date, stage, count, total_summa) VALUES (?, ?, ?, ?)",
                    (stat_date, stage_name, 0, 0)
                )
                logger.info(f"Добавлена стадия {stage_name} в статистику за {stat_date}")
        
        conn.commit()
        conn.close()

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('webhooks.db')
    cursor = conn.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS deals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hook_id INTEGER,
        name TEXT,
        summa REAL,
        stage TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        stat_date TEXT
    )
    ''')
    
    # Создаем таблицу для ежедневной статистики
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        stage TEXT,
        count INTEGER,
        total_summa REAL
    )
    ''')
    
    conn.commit()
    conn.close()

# Функция для проверки и исправления шаблонных значений
def clean_template_values(name, summa_str):
    # Список шаблонных значений для имени
    name_templates = ["{{Название}}", "{=Document:TITLE}", "{{название}}", 
                     "{=Document:NAME}", "{=Document:deal_name}"]
    
    # Список шаблонных значений для суммы
    summa_templates = ["{{Сумма}}", "{=Document:OPPORTUNITY}", "{{сумма}}", 
                       "{=Document:PRICE}", "{=Document:deal_sum}"]
    
    # Проверяем имя
    if name in name_templates or not name:
        logger.warning(f"Received template value for name: {name}")
        name = "Сделка без названия"
    
    # Проверяем сумму
    if summa_str in summa_templates or not summa_str:
        logger.warning(f"Received template value for summa: {summa_str}")
        summa_str = "0"
    
    # Декодируем URL-encoded значения
    try:
        name = urllib.parse.unquote(name)
    except:
        pass
    
    return name, summa_str

# Общая функция обработки веб-хука (для обоих методов GET и POST)
def process_webhook(hook_id, name, summa_str):
    if hook_id < 1 or hook_id > 25:
        return jsonify({"status": "error", "message": "Invalid hook ID"}), 400
    
    # Очищаем от шаблонных значений
    name, summa_str = clean_template_values(name, summa_str)
    
    # Логируем обработанные данные
    logger.info(f"Processing webhook {hook_id} - Name: {name}, Summa: {summa_str}")
    
    # Преобразование суммы в число
    try:
        summa_str = str(summa_str).replace(' ', '').replace(',', '.')
        summa = float(summa_str)
    except ValueError:
        logger.error(f"Could not convert summa to float: {summa_str}")
        summa = 0
    
    stage = HOOK_TO_STAGE.get(hook_id, "Неизвестно")
    
    # Получаем дату для статистики с учетом времени
    stat_date = get_stat_date()
    
    # Используем блокировку для предотвращения конфликтов при одновременных запросах
    with db_lock:
        conn = sqlite3.connect('webhooks.db')
        cursor = conn.cursor()
        
        # Сохраняем информацию о сделке с датой статистики
        cursor.execute(
            "INSERT INTO deals (hook_id, name, summa, stage, stat_date) VALUES (?, ?, ?, ?, ?)",
            (hook_id, name, summa, stage, stat_date)
        )
        deal_id = cursor.lastrowid
        logger.info(f"Inserted deal with ID: {deal_id}, stat_date: {stat_date}")
        
        # Проверяем, есть ли уже запись для этой стадии на эту дату
        cursor.execute(
            "SELECT id, count, total_summa FROM daily_stats WHERE date = ? AND stage = ?",
            (stat_date, stage)
        )
        result = cursor.fetchone()
        
        if result:
            # Обновляем существующую запись
            stat_id, count, total_summa = result
            cursor.execute(
                "UPDATE daily_stats SET count = ?, total_summa = ? WHERE id = ?",
                (count + 1, total_summa + summa, stat_id)
            )
            logger.info(f"Updated daily stats ID: {stat_id}, new count: {count + 1}, new total: {total_summa + summa}")
        else:
            # Создаем новую запись
            cursor.execute(
                "INSERT INTO daily_stats (date, stage, count, total_summa) VALUES (?, ?, ?, ?)",
                (stat_date, stage, 1, summa)
            )
            stat_id = cursor.lastrowid
            logger.info(f"Inserted new daily stats with ID: {stat_id}")
        
        conn.commit()
        conn.close()
    
    return jsonify({
        "status": "success", 
        "message": f"Webhook {hook_id} processed",
        "data": {
            "name": name,
            "summa": summa,
            "stage": stage,
            "stat_date": stat_date
        }
    })

# Обработчик для GET запросов с параметрами в URL
@app.route('/hook<int:hook_id>/', methods=['GET'])
def handle_webhook_get(hook_id):
    logger.info(f"GET request received for hook {hook_id}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Args: {request.args}")
    
    name = request.args.get('name', '')
    summa_str = request.args.get('summa', '0')
    return process_webhook(hook_id, name, summa_str)

# Обработчик для POST запросов с JSON-телом или URL-параметрами
@app.route('/hook<int:hook_id>/', methods=['POST'])
def handle_webhook_post(hook_id):
    # Проверяем формат данных
    content_type = request.headers.get('Content-Type', '')
    
    # Логирование для отладки
    logger.info(f"POST request received for hook {hook_id}")
    logger.info(f"Content-Type: {content_type}")
    logger.info(f"URL: {request.url}")
    logger.info(f"Args: {request.args}")
    
    try:
        # Получаем аргументы из URL
        name = request.args.get('name', '')
        summa_str = request.args.get('summa', '0')
        
        # Если в URL нет параметров, проверяем тело запроса
        if not name:
            if 'application/json' in content_type:
                # Если данные пришли в формате JSON
                data = request.json
                logger.info(f"JSON data: {data}")
                name = data.get('name', '')
                summa_str = data.get('summa', '0')
            elif 'application/x-www-form-urlencoded' in content_type:
                # Если данные пришли в формате form-data
                logger.info(f"Form data: {request.form}")
                name = request.form.get('name', '')
                summa_str = request.form.get('summa', '0')
            else:
                # Пробуем получить данные из тела запроса напрямую
                try:
                    request_data = request.data.decode('utf-8')
                    logger.info(f"Raw request data: {request_data}")
                    data = json.loads(request_data)
                    name = data.get('name', '')
                    summa_str = data.get('summa', '0')
                except Exception as e:
                    logger.error(f"Failed to parse JSON from request body: {str(e)}")
        
        logger.info(f"Extracted name: {name}, summa: {summa_str}")
        return process_webhook(hook_id, name, summa_str)
    
    except Exception as e:
        logger.error(f"Error processing POST webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Обработчик для запросов вида /hook1/name=XXX&summa=YYY (без вопросительного знака)
@app.route('/hook<int:hook_id>/<path:params>', methods=['GET', 'POST'])
def handle_webhook_with_params_in_path(hook_id, params):
    logger.info(f"Request with params in path received for hook {hook_id}")
    logger.info(f"Params: {params}")
    
    # Преобразуем параметры из пути в словарь
    params_dict = {}
    try:
        # Разбиваем параметры по символу &
        param_pairs = params.split('&')
        for pair in param_pairs:
            # Каждую пару разбиваем по символу =
            if '=' in pair:
                key, value = pair.split('=', 1)
                params_dict[key] = value
    except Exception as e:
        logger.error(f"Error parsing params: {e}")
    
    # Получаем параметры
    name = params_dict.get('name', '')
    summa_str = params_dict.get('summa', '0')
    
    logger.info(f"Extracted from path: name={name}, summa={summa_str}")
    
    # Обрабатываем данные
    return process_webhook(hook_id, name, summa_str)

# Маршрут для отображения главной страницы
@app.route('/')
def index():
    return render_template('index.html')

# API для получения статистики по всем стадиям
# Replace the API endpoint for getting stats with this fixed version

@app.route('/api/stats', methods=['GET'])
def get_stats():
    try:
        # Get date parameter from request
        date = request.args.get('date')
        
        logger.info(f"Stats requested for date: {date}")
        
        if not date:
            # If date not provided, use current date
            date = datetime.now().strftime('%Y-%m-%d')
            logger.info(f"No date provided, using current date: {date}")
        
        conn = sqlite3.connect('webhooks.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get statistics for the selected date
        cursor.execute(
            "SELECT stage, count, total_summa FROM daily_stats WHERE date = ? ORDER BY stage",
            (date,)
        )
        stats = [dict(row) for row in cursor.fetchall()]
        
        logger.info(f"Found {len(stats)} stats records for date {date}")
        
        # Check if we have entries for all stages, if not - add them with zero values
        existing_stages = {stat['stage'] for stat in stats}
        
        # Add missing stages with zero values
        for stage_id, stage_name in HOOK_TO_STAGE.items():
            if stage_name not in existing_stages:
                stats.append({'stage': stage_name, 'count': 0, 'total_summa': 0})
        
        conn.close()
        
        # Set explicit headers to prevent caching
        response = jsonify(stats)
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
        
        return response
        
    except Exception as e:
        logger.error(f"Error in get_stats: {str(e)}")
        return jsonify({"error": str(e)}), 500

# API для получения сделок по стадии
@app.route('/api/deals/<stage>', methods=['GET'])
def get_deals_by_stage(stage):
    date = request.args.get('date')
    
    if not date:
        # Если дата не указана, используем текущую дату
        date = datetime.now().strftime('%Y-%m-%d')
    
    conn = sqlite3.connect('webhooks.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем сделки по стадии и дате
    # Учитываем как поле stat_date, так и timestamp для обратной совместимости
    cursor.execute(
        """
        SELECT id, name, summa, timestamp 
        FROM deals 
        WHERE stage = ? AND (stat_date = ? OR date(timestamp) = ?)
        ORDER BY timestamp DESC
        """,
        (stage, date, date)
    )
    deals = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify(deals)

# API для получения доступных дат, для которых есть статистика
@app.route('/api/dates', methods=['GET'])
def get_available_dates():
    conn = sqlite3.connect('webhooks.db')
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT date FROM daily_stats ORDER BY date DESC")
    dates = [row[0] for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify(dates)

# Маршрут для проверки работоспособности
@app.route('/health')
def health_check():
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()})

def schedule_daily_stats_initialization():
    while True:
        now = datetime.now()
        next_run = datetime(now.year, now.month, now.day) + timedelta(days=1, minutes=1)
        sleep_time = (next_run - now).total_seconds()
        time.sleep(sleep_time)
        ensure_all_stages_in_db()
        logger.info("Выполнена ежедневная инициализация статистики")

if __name__ == '__main__':
    # Инициализируем базу данных
    init_db()
    # Добавляем все стадии в БД
    ensure_all_stages_in_db()
    
    # Запускаем поток для ежедневной инициализации статистики
    stats_thread = threading.Thread(target=schedule_daily_stats_initialization, daemon=True)
    stats_thread.start()
    
    # Запускаем сервер
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)