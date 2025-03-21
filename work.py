from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import sqlite3
import json
from datetime import datetime
import threading
import time

app = Flask(__name__, static_folder='static', template_folder='templates')
CORS(app)  # Разрешаем кросс-доменные запросы

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
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
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

init_db()

# Словарь для маппинга номера хука на стадию
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

# Обработчики для каждого веб-хука (POST-запросы)
@app.route('/hook<int:hook_id>/', methods=['POST'])
def handle_webhook_post(hook_id):
    if hook_id < 1 or hook_id > 25:
        return jsonify({"status": "error", "message": "Invalid hook ID"}), 400
    
    # Получаем данные из POST-запроса
    try:
        # Проверяем формат данных
        content_type = request.headers.get('Content-Type', '')
        
        if 'application/json' in content_type:
            # Если данные пришли в формате JSON
            data = request.json
            name = data.get('name', '')
            summa_str = data.get('summa', '0')
        elif 'application/x-www-form-urlencoded' in content_type:
            # Если данные пришли в формате form-data
            name = request.form.get('name', '')
            summa_str = request.form.get('summa', '0')
        else:
            # Пробуем получить данные из тела запроса напрямую
            try:
                data = json.loads(request.data)
                name = data.get('name', '')
                summa_str = data.get('summa', '0')
            except:
                # Если не удалось распарсить JSON, используем аргументы запроса
                name = request.args.get('name', '')
                summa_str = request.args.get('summa', '0')
        
        # Преобразование суммы в число
        try:
            summa = float(str(summa_str).replace(' ', '').replace(',', '.'))
        except ValueError:
            summa = 0
        
        stage = HOOK_TO_STAGE.get(hook_id, "Неизвестно")
        
        # Используем блокировку для предотвращения конфликтов при одновременных запросах
        with db_lock:
            conn = sqlite3.connect('webhooks.db')
            cursor = conn.cursor()
            
            # Сохраняем информацию о сделке
            cursor.execute(
                "INSERT INTO deals (hook_id, name, summa, stage) VALUES (?, ?, ?, ?)",
                (hook_id, name, summa, stage)
            )
            
            # Обновляем ежедневную статистику
            today = datetime.now().strftime('%Y-%m-%d')
            
            # Проверяем, есть ли уже запись для этой стадии на сегодня
            cursor.execute(
                "SELECT id, count, total_summa FROM daily_stats WHERE date = ? AND stage = ?",
                (today, stage)
            )
            result = cursor.fetchone()
            
            if result:
                # Обновляем существующую запись
                stat_id, count, total_summa = result
                cursor.execute(
                    "UPDATE daily_stats SET count = ?, total_summa = ? WHERE id = ?",
                    (count + 1, total_summa + summa, stat_id)
                )
            else:
                # Создаем новую запись
                cursor.execute(
                    "INSERT INTO daily_stats (date, stage, count, total_summa) VALUES (?, ?, ?, ?)",
                    (today, stage, 1, summa)
                )
            
            conn.commit()
            conn.close()
        
        return jsonify({
            "status": "success", 
            "message": f"Webhook {hook_id} processed",
            "data": {
                "name": name,
                "summa": summa,
                "stage": stage
            }
        })
        
    except Exception as e:
        return jsonify({
            "status": "error", 
            "message": f"Error processing webhook: {str(e)}"
        }), 500

# Для обратной совместимости также поддерживаем GET-запросы
@app.route('/hook<int:hook_id>/', methods=['GET'])
def handle_webhook_get(hook_id):
    if hook_id < 1 or hook_id > 25:
        return jsonify({"status": "error", "message": "Invalid hook ID"}), 400
    
    name = request.args.get('name', '')
    summa_str = request.args.get('summa', '0')
    
    # Преобразование суммы в число
    try:
        summa = float(summa_str.replace(' ', '').replace(',', '.'))
    except ValueError:
        summa = 0
    
    stage = HOOK_TO_STAGE.get(hook_id, "Неизвестно")
    
    # Используем блокировку для предотвращения конфликтов при одновременных запросах
    with db_lock:
        conn = sqlite3.connect('webhooks.db')
        cursor = conn.cursor()
        
        # Сохраняем информацию о сделке
        cursor.execute(
            "INSERT INTO deals (hook_id, name, summa, stage) VALUES (?, ?, ?, ?)",
            (hook_id, name, summa, stage)
        )
        
        # Обновляем ежедневную статистику
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Проверяем, есть ли уже запись для этой стадии на сегодня
        cursor.execute(
            "SELECT id, count, total_summa FROM daily_stats WHERE date = ? AND stage = ?",
            (today, stage)
        )
        result = cursor.fetchone()
        
        if result:
            # Обновляем существующую запись
            stat_id, count, total_summa = result
            cursor.execute(
                "UPDATE daily_stats SET count = ?, total_summa = ? WHERE id = ?",
                (count + 1, total_summa + summa, stat_id)
            )
        else:
            # Создаем новую запись
            cursor.execute(
                "INSERT INTO daily_stats (date, stage, count, total_summa) VALUES (?, ?, ?, ?)",
                (today, stage, 1, summa)
            )
        
        conn.commit()
        conn.close()
    
    return jsonify({"status": "success", "message": f"Webhook {hook_id} processed"})

# Маршрут для отображения главной страницы
@app.route('/')
def index():
    return render_template('index.html')


# API для получения статистики по всем стадиям
@app.route('/api/stats', methods=['GET'])
def get_stats():
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = sqlite3.connect('webhooks.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем статистику за выбранную дату
    cursor.execute(
        "SELECT stage, count, total_summa FROM daily_stats WHERE date = ? ORDER BY stage",
        (date,)
    )
    stats = [dict(row) for row in cursor.fetchall()]
    
    conn.close()
    
    return jsonify(stats)

# API для получения сделок по стадии
@app.route('/api/deals/<stage>', methods=['GET'])
def get_deals_by_stage(stage):
    date = request.args.get('date', datetime.now().strftime('%Y-%m-%d'))
    
    conn = sqlite3.connect('webhooks.db')
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Получаем сделки по стадии и дате
    cursor.execute(
        """
        SELECT id, name, summa, timestamp 
        FROM deals 
        WHERE stage = ? AND date(timestamp) = ?
        ORDER BY timestamp DESC
        """,
        (stage, date)
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


@app.route('/robots.txt')
def robots():
    return app.send_static_file('robots.txt')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001, threaded=True)