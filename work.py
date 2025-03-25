import os
from flask import Flask, request, render_template, jsonify, redirect, url_for
from datetime import datetime, time, timedelta
import sqlite3
import threading
import logging
from queue import Queue
import time as time_module
import traceback
import pytz

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("webhook_processor.log"),
        logging.StreamHandler()  # Also output to console
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Database initialization
DB_PATH = "webhooks.db"

# Queue for processing webhooks asynchronously
webhook_queue = Queue()

# Moscow timezone
moscow_tz = pytz.timezone('Europe/Moscow')


def init_db():
    """Initialize the database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Table for storing webhook data
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS webhooks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        hook_type TEXT NOT NULL,
        name TEXT,
        summa TEXT,
        received_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        received_at_moscow TEXT,
        processing_date TEXT,
        raw_data TEXT
    )
    ''')

    # Add received_at_moscow column if it doesn't exist
    try:
        cursor.execute("SELECT received_at_moscow FROM webhooks LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE webhooks ADD COLUMN received_at_moscow TEXT")
        logger.info("Added received_at_moscow column to webhooks table")

    # Table for storing daily statistics with sum columns
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS daily_stats (
        date TEXT PRIMARY KEY,
        hook1_count INTEGER DEFAULT 0,
        hook2_count INTEGER DEFAULT 0,
        hook3_count INTEGER DEFAULT 0,
        hook4_count INTEGER DEFAULT 0,
        hook5_count INTEGER DEFAULT 0,
        hook6_count INTEGER DEFAULT 0,
        hook7_count INTEGER DEFAULT 0,
        hook8_count INTEGER DEFAULT 0,
        hook9_count INTEGER DEFAULT 0,
        hook10_count INTEGER DEFAULT 0,
        hook11_count INTEGER DEFAULT 0,
        hook12_count INTEGER DEFAULT 0,
        hook13_count INTEGER DEFAULT 0,
        hook14_count INTEGER DEFAULT 0,
        hook15_count INTEGER DEFAULT 0,
        hook16_count INTEGER DEFAULT 0,
        hook17_count INTEGER DEFAULT 0,
        hook18_count INTEGER DEFAULT 0,
        hook19_count INTEGER DEFAULT 0,
        hook20_count INTEGER DEFAULT 0,
        hook21_count INTEGER DEFAULT 0,
        hook22_count INTEGER DEFAULT 0,
        hook23_count INTEGER DEFAULT 0,
        hook24_count INTEGER DEFAULT 0,
        hook25_count INTEGER DEFAULT 0,
        total_count INTEGER DEFAULT 0,
        hook1_sum INTEGER DEFAULT 0,
        hook2_sum INTEGER DEFAULT 0,
        hook3_sum INTEGER DEFAULT 0,
        hook4_sum INTEGER DEFAULT 0,
        hook5_sum INTEGER DEFAULT 0,
        hook6_sum INTEGER DEFAULT 0,
        hook7_sum INTEGER DEFAULT 0,
        hook8_sum INTEGER DEFAULT 0,
        hook9_sum INTEGER DEFAULT 0,
        hook10_sum INTEGER DEFAULT 0,
        hook11_sum INTEGER DEFAULT 0,
        hook12_sum INTEGER DEFAULT 0,
        hook13_sum INTEGER DEFAULT 0,
        hook14_sum INTEGER DEFAULT 0,
        hook15_sum INTEGER DEFAULT 0,
        hook16_sum INTEGER DEFAULT 0,
        hook17_sum INTEGER DEFAULT 0,
        hook18_sum INTEGER DEFAULT 0,
        hook19_sum INTEGER DEFAULT 0,
        hook20_sum INTEGER DEFAULT 0,
        hook21_sum INTEGER DEFAULT 0,
        hook22_sum INTEGER DEFAULT 0,
        hook23_sum INTEGER DEFAULT 0,
        hook24_sum INTEGER DEFAULT 0,
        hook25_sum INTEGER DEFAULT 0,
        total_sum INTEGER DEFAULT 0
    )
    ''')

    # Make sure all columns exist
    for i in range(1, 26):
        # Check and add count columns if they don't exist
        count_col = f"hook{i}_count"
        try:
            cursor.execute(f"SELECT {count_col} FROM daily_stats LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f"ALTER TABLE daily_stats ADD COLUMN {count_col} INTEGER DEFAULT 0")
            logger.info(f"Added {count_col} column to daily_stats table")

        # Check and add sum columns if they don't exist
        sum_col = f"hook{i}_sum"
        try:
            cursor.execute(f"SELECT {sum_col} FROM daily_stats LIMIT 1")
        except sqlite3.OperationalError:
            cursor.execute(f"ALTER TABLE daily_stats ADD COLUMN {sum_col} INTEGER DEFAULT 0")
            logger.info(f"Added {sum_col} column to daily_stats table")

    # Add total columns if they don't exist
    try:
        cursor.execute("SELECT total_count FROM daily_stats LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE daily_stats ADD COLUMN total_count INTEGER DEFAULT 0")
        logger.info("Added total_count column to daily_stats table")

    try:
        cursor.execute("SELECT total_sum FROM daily_stats LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE daily_stats ADD COLUMN total_sum INTEGER DEFAULT 0")
        logger.info("Added total_sum column to daily_stats table")

    conn.commit()
    conn.close()
    logger.info("Database initialized successfully")


def get_moscow_now():
    """Get current datetime in Moscow timezone"""
    return datetime.now(moscow_tz)


def get_processing_date():
    """
    Determine the processing date based on current Moscow time
    If time is after 21:00, use tomorrow's date
    If time is before or equal to 21:00, use today's date
    """
    now = get_moscow_now()
    cutoff_time = time(21, 0)  # 21:00

    if now.time() > cutoff_time:
        # If current time is past 21:00, use tomorrow's date
        processing_date = (now + timedelta(days=1)).strftime('%d.%m.%Y')
        logger.info(
            f"Moscow time is {now.strftime('%H:%M:%S')}, which is after 21:00. Using tomorrow's date: {processing_date}")
    else:
        # Otherwise use today's date
        processing_date = now.strftime('%d.%m.%Y')
        logger.info(
            f"Moscow time is {now.strftime('%H:%M:%S')}, which is before 21:00. Using today's date: {processing_date}")

    return processing_date


def save_webhook(hook_type, name, summa, raw_data):
    """Save webhook data to database"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)  # Increase timeout to avoid database locks
        cursor = conn.cursor()

        processing_date = get_processing_date()

        # Get current time in Moscow timezone
        now = get_moscow_now()
        moscow_time_str = now.strftime('%Y-%m-%d %H:%M:%S')

        # Convert summa to integer if possible
        try:
            summa_int = int(summa)
        except (ValueError, TypeError):
            summa_int = 0

        # Log detailed information
        logger.info(
            f"Saving webhook: type={hook_type}, name={name}, summa={summa}, date={processing_date}, moscow_time={moscow_time_str}")

        # Insert webhook data with Moscow time
        cursor.execute(
            "INSERT INTO webhooks (hook_type, name, summa, received_at_moscow, processing_date, raw_data) VALUES (?, ?, ?, ?, ?, ?)",
            (hook_type, name, summa, moscow_time_str, processing_date, raw_data)
        )

        # Get the hook number from the hook_type string (e.g., "hook1_count" -> 1)
        hook_num = int(hook_type.replace("hook", "").replace("_count", ""))
        sum_column = f"hook{hook_num}_sum"

        # Ensure the date exists in daily_stats
        cursor.execute(
            "INSERT OR IGNORE INTO daily_stats (date) VALUES (?)",
            (processing_date,)
        )

        # Update daily statistics (count and sum)
        update_query = f"""
            UPDATE daily_stats 
            SET {hook_type} = COALESCE({hook_type}, 0) + 1, 
                total_count = COALESCE(total_count, 0) + 1, 
                {sum_column} = COALESCE({sum_column}, 0) + ?, 
                total_sum = COALESCE(total_sum, 0) + ? 
            WHERE date = ?
        """
        cursor.execute(update_query, (summa_int, summa_int, processing_date))

        conn.commit()

        # Verify the update worked by querying the updated record
        cursor.execute(f"SELECT {hook_type}, total_count, {sum_column}, total_sum FROM daily_stats WHERE date = ?",
                       (processing_date,))
        updated_stats = cursor.fetchone()
        if updated_stats:
            logger.info(
                f"Updated stats for {processing_date}: {hook_type}={updated_stats[0]}, total_count={updated_stats[1]}, "
                f"{sum_column}={updated_stats[2]}, total_sum={updated_stats[3]}")
        else:
            logger.error(f"No stats found for date {processing_date} after update")

        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error saving webhook: {str(e)}")
        # Print more detailed error information
        logger.error(traceback.format_exc())
        if 'conn' in locals() and conn:
            conn.close()
        return False


def webhook_processor():
    """Background thread function to process webhooks from the queue"""
    logger.info("Webhook processor thread started")
    while True:
        try:
            logger.info(f"Queue size: {webhook_queue.qsize()}")  # Add this line
            webhook_data = webhook_queue.get(timeout=5)  # 5 second timeout
            if webhook_data is None:  # Poison pill to stop the thread
                break

            hook_type = webhook_data.get('hook_type')
            name = webhook_data.get('name')
            summa = webhook_data.get('summa')
            raw_data = webhook_data.get('raw_data')

            logger.info(f"Processing webhook from queue: {hook_type}, {name}, {summa}")

            # Test database connection before saving
            try:
                conn = sqlite3.connect(DB_PATH, timeout=20)
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                conn.close()
                logger.info("Database connection test successful")
            except Exception as db_e:
                logger.error(f"Database connection test failed: {str(db_e)}")
                logger.error(traceback.format_exc())

            success = save_webhook(hook_type, name, summa, raw_data)

            if success:
                logger.info(f"Successfully processed webhook: {hook_type}")
            else:
                logger.error(f"Failed to process webhook: {hook_type}")

            webhook_queue.task_done()

            # Small delay to prevent database locks
            time_module.sleep(0.1)

        except Exception as e:
            # If timeout or other error, just continue
            if "Empty" not in str(e):  # Don't log queue.Empty exceptions
                logger.error(f"Webhook processor exception: {str(e)}")
                logger.error(traceback.format_exc())
            continue


def get_stats_for_date(date):
    """Get statistics for a specific date"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)  # Increase timeout to avoid database locks
        conn.row_factory = sqlite3.Row  # Use row factory for easier dictionary conversion
        cursor = conn.cursor()

        # First ensure the date exists in the table
        cursor.execute("INSERT OR IGNORE INTO daily_stats (date) VALUES (?)", (date,))
        conn.commit()

        # Then get the stats
        cursor.execute("SELECT * FROM daily_stats WHERE date = ?", (date,))
        stats = cursor.fetchone()

        if not stats:
            logger.error(f"No stats found for date {date}")
            return {}

        # Convert to dictionary
        stats_dict = dict(stats)

        # Ensure all keys have values (not None)
        for key in stats_dict:
            if stats_dict[key] is None:
                stats_dict[key] = 0

        conn.close()
        return stats_dict
    except Exception as e:
        logger.error(f"Error getting stats for date {date}: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals() and conn:
            conn.close()
        return {}


def calculate_kpis(stats_dict):
    """Calculate KPIs based on daily statistics"""
    # Ensure all hook counts exist to avoid None values
    for i in range(1, 26):
        key = f"hook{i}_count"
        sum_key = f"hook{i}_sum"
        if key not in stats_dict or stats_dict[key] is None:
            stats_dict[key] = 0
        if sum_key not in stats_dict or stats_dict[sum_key] is None:
            stats_dict[sum_key] = 0

    # Calculate cancellation rate (p.14 + p.19 + p.23) / p.7 * 100%
    all_ready_count = stats_dict.get('hook7_count', 0)
    if all_ready_count == 0:
        all_ready_count = 1  # Avoid division by zero

    cancellation_count = (
            stats_dict.get('hook14_count', 0) +
            stats_dict.get('hook19_count', 0) +
            stats_dict.get('hook23_count', 0)
    )
    cancellation_rate = round((cancellation_count / all_ready_count) * 100, 2)

    # Calculate missed calls rate (p.15 + p.20 + p.24) / p.7 * 100%
    missed_calls_count = (
            stats_dict.get('hook15_count', 0) +
            stats_dict.get('hook20_count', 0) +
            stats_dict.get('hook24_count', 0)
    )
    missed_calls_rate = round((missed_calls_count / all_ready_count) * 100, 2)

    # Calculate confirmed orders sum (p.13 + p.18 + p.22)
    confirmed_orders_sum = (
            stats_dict.get('hook13_sum', 0) +
            stats_dict.get('hook18_sum', 0) +
            stats_dict.get('hook22_sum', 0)
    )

    # Return KPIs
    return {
        'cancellation_rate': cancellation_rate,
        'missed_calls_rate': missed_calls_rate,
        'confirmed_orders_sum': confirmed_orders_sum
    }


def get_webhooks_by_filter(date=None, hook_type=None, limit=100):
    """Get webhooks by filter criteria"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)  # Increase timeout to avoid database locks
        conn.row_factory = sqlite3.Row  # This enables column access by name
        cursor = conn.cursor()

        # Check if the received_at_moscow column exists
        try:
            cursor.execute("SELECT received_at_moscow FROM webhooks LIMIT 1")
            use_moscow_time = True
        except sqlite3.OperationalError:
            use_moscow_time = False

        if use_moscow_time:
            query = "SELECT id, hook_type, name, summa, received_at_moscow as received_at, processing_date, raw_data FROM webhooks WHERE 1=1"
        else:
            query = "SELECT id, hook_type, name, summa, datetime(received_at, 'localtime') as received_at, processing_date, raw_data FROM webhooks WHERE 1=1"

        params = []

        if date:
            query += " AND processing_date = ?"
            params.append(date)

        if hook_type:
            query += " AND hook_type = ?"
            params.append(hook_type)

        query += " ORDER BY received_at DESC LIMIT ?"
        params.append(limit)

        cursor.execute(query, params)
        rows = cursor.fetchall()

        # Convert to list of dictionaries
        webhooks = []
        for row in rows:
            webhook = {}
            for key in row.keys():
                webhook[key] = row[key]
            webhooks.append(webhook)

        conn.close()
        return webhooks
    except Exception as e:
        logger.error(f"Error getting webhooks: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals() and conn:
            conn.close()
        return []


# API endpoint for filtered webhooks
@app.route('/api/webhooks', methods=['GET'])
def api_webhooks():
    """API endpoint to get filtered webhooks"""
    date = request.args.get('date')
    hook_type = request.args.get('hook_type')
    limit = request.args.get('limit', 100, type=int)

    webhooks = get_webhooks_by_filter(date, hook_type, limit)

    return jsonify({"webhooks": webhooks})


# API endpoint for KPIs
@app.route('/api/kpis', methods=['GET'])
def api_kpis():
    """API endpoint to get KPIs for a specific date"""
    date = request.args.get('date')
    if not date:
        date = get_processing_date()

    stats_dict = get_stats_for_date(date)
    kpis = calculate_kpis(stats_dict)

    return jsonify({"kpis": kpis, "date": date})


# API endpoint for current Moscow time
@app.route('/api/moscow-time', methods=['GET'])
def api_moscow_time():
    """API endpoint to get current Moscow time"""
    moscow_now = get_moscow_now()
    return jsonify({
        "time": moscow_now.strftime('%H:%M:%S'),
        "date": moscow_now.strftime('%d.%m.%Y'),
        "full": moscow_now.strftime('%Y-%m-%d %H:%M:%S'),
        "timestamp": int(moscow_now.timestamp()),
        "timezone": "Europe/Moscow (UTC+3)"
    })


# Create routes for each webhook type
@app.route('/hook<int:hook_num>/<path:path>', methods=['GET', 'POST'])
def handle_webhook(hook_num, path):
    """Generic handler for all webhook types"""
    if hook_num < 1 or hook_num > 25:
        return jsonify({"error": "Invalid webhook number"}), 400

    hook_type = f"hook{hook_num}_count"

    # Get parameters
    if request.method == 'GET':
        name = request.args.get('name', '')
        summa = request.args.get('summa', '')
        raw_data = str(dict(request.args))
    else:  # POST
        if request.is_json:
            data = request.get_json()
            name = data.get('name', '')
            summa = data.get('summa', '')
            raw_data = str(data)
        else:
            name = request.form.get('name', '')
            summa = request.form.get('summa', '')
            raw_data = str(dict(request.form))

    # Add to processing queue
    webhook_queue.put({
        'hook_type': hook_type,
        'name': name,
        'summa': summa,
        'raw_data': raw_data
    })

    logger.info(f"Webhook received: {hook_type}, {name}, {summa}")
    return jsonify({"status": "queued"}), 202


@app.route('/')
def index():
    """Main page showing statistics"""
    try:
        # Get date from query parameter or use current processing date
        date_param = request.args.get('date')
        if date_param:
            processing_date = date_param
        else:
            processing_date = get_processing_date()

        logger.info(f"Rendering index page for date: {processing_date}")

        # Get statistics for the selected date
        stats_dict = get_stats_for_date(processing_date)

        # For template compatibility, ensure all hook counts and sums exist
        for i in range(1, 26):
            count_key = f"hook{i}_count"
            sum_key = f"hook{i}_sum"
            if count_key not in stats_dict or stats_dict[count_key] is None:
                stats_dict[count_key] = 0
            if sum_key not in stats_dict or stats_dict[sum_key] is None:
                stats_dict[sum_key] = 0

        # Calculate KPIs
        kpis = calculate_kpis(stats_dict)

        # Get recent webhooks
        webhooks = get_webhooks_by_filter(date=processing_date, limit=50)
        recent_webhooks = [(webhook['hook_type'], webhook['name'], webhook['summa'], webhook['received_at']) for webhook
                           in webhooks]

        # Get count of unprocessed webhooks in queue
        queue_size = webhook_queue.qsize()

        # Get current Moscow time and date
        moscow_now = get_moscow_now()
        current_datetime = moscow_now.strftime('%d.%m.%Y')
        current_moscow_time = moscow_now.strftime('%H:%M:%S')

        return render_template(
            'index.html',
            stats=stats_dict,
            kpis=kpis,
            recent_webhooks=recent_webhooks,
            queue_size=queue_size,
            current_date=current_datetime,
            current_moscow_time=current_moscow_time,
            processing_date=processing_date
        )
    except Exception as e:
        logger.error(f"Error in index route: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/reset')
def reset_stats():
    """Reset all statistics (for testing purposes)"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)  # Increase timeout to avoid database locks
        cursor = conn.cursor()

        # Delete all webhook data
        cursor.execute("DELETE FROM webhooks")

        # Reset all stats
        cursor.execute("DELETE FROM daily_stats")

        conn.commit()
        conn.close()

        logger.info("All statistics reset")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error resetting stats: {str(e)}")
        logger.error(traceback.format_exc())
        if 'conn' in locals() and conn:
            conn.close()
        return f"Error: {str(e)}", 500


@app.route('/generate-test-data')
def generate_test_data():
    """Generate test data for demonstration"""
    try:
        processing_date = get_processing_date()

        # Sample deal names
        deal_names = [
            "Заказ №12345",
            "Сделка с компанией XYZ",
            "Оптовая закупка",
            "Разовая поставка",
            "Клиент Иванов"
        ]

        # Generate 25 webhooks, one for each type
        import random
        for i in range(1, 26):
            hook_type = f"hook{i}_count"
            name = random.choice(deal_names)
            summa = str(random.randint(5000, 50000))

            # Add to processing queue
            webhook_queue.put({
                'hook_type': hook_type,
                'name': name,
                'summa': summa,
                'raw_data': f"{{'name': '{name}', 'summa': '{summa}'}}"
            })

        logger.info(f"Generated 25 test webhooks")
        return redirect(url_for('index'))
    except Exception as e:
        logger.error(f"Error generating test data: {str(e)}")
        logger.error(traceback.format_exc())
        return f"Error: {str(e)}", 500


@app.route('/debug')
def debug():
    """Debug page to check database and queue status"""
    try:
        conn = sqlite3.connect(DB_PATH, timeout=20)  # Increase timeout to avoid database locks
        cursor = conn.cursor()

        # Get database info
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()

        # Get webhook data
        cursor.execute("SELECT COUNT(*) FROM webhooks")
        webhook_count = cursor.fetchone()[0]

        cursor.execute("SELECT * FROM webhooks ORDER BY received_at DESC LIMIT 10")
        recent_webhooks = cursor.fetchall()

        # Get column names for webhooks table
        cursor.execute("PRAGMA table_info(webhooks)")
        webhook_columns = [column[1] for column in cursor.fetchall()]

        # Get daily stats data
        cursor.execute("SELECT * FROM daily_stats")
        daily_stats = cursor.fetchall()

        # Get column names for daily_stats table
        cursor.execute("PRAGMA table_info(daily_stats)")
        stats_columns = [column[1] for column in cursor.fetchall()]

        conn.close()

        # Format debug info as HTML
        debug_info = f"""
        <h1>Debug Information</h1>
        <h2>Database Tables</h2>
        <ul>
            {''.join(f'<li>{table[0]}</li>' for table in tables)}
        </ul>

        <h2>Webhook Queue</h2>
        <p>Queue size: {webhook_queue.qsize()}</p>

        <h2>Webhooks Table ({webhook_count} total entries)</h2>
        <table border="1">
            <tr>
                {''.join(f'<th>{col}</th>' for col in webhook_columns)}
            </tr>
            {''.join(f'<tr>{"".join(f"<td>{cell}</td>" for cell in row)}</tr>' for row in recent_webhooks)}
        </table>

        <h2>Daily Stats Table</h2>
        <table border="1">
            <tr>
                {''.join(f'<th>{col}</th>' for col in stats_columns)}
            </tr>
            {''.join(f'<tr>{"".join(f"<td>{cell}</td>" for cell in row)}</tr>' for row in daily_stats)}
        </table>

        <h2>Actions</h2>
        <p><a href="/reset" style="color: red;">Reset All Data</a></p>
        <p><a href="/generate-test-data">Generate Test Data</a></p>
        <p><a href="/">Back to Dashboard</a></p>

        <h2>Current Moscow Time</h2>
        <p>{get_moscow_now().strftime('%Y-%m-%d %H:%M:%S (%Z)')}</p>
        <p>Processing date: {get_processing_date()}</p>
        """

        return debug_info
    except Exception as e:
        logger.error(f"Error in debug route: {str(e)}")
        error_traceback = traceback.format_exc()
        if 'conn' in locals() and conn:
            conn.close()
        return f"<h1>Error</h1><pre>{str(e)}</pre><h2>Traceback</h2><pre>{error_traceback}</pre>"


# Handle favicon requests to prevent 404 errors
@app.route('/favicon.ico')
def favicon():
    return '', 204


if __name__ == '__main__':
    # Initialize database
    try:
        init_db()
        logger.info("Database initialized successfully")

        # Test database connection
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Database tables: {[table[0] for table in tables]}")
        conn.close()
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}")
        logger.error(traceback.format_exc())

    # Create templates directory if it doesn't exist
    os.makedirs('templates', exist_ok=True)

    # Start webhook processor thread
    processor_thread = threading.Thread(target=webhook_processor)
    processor_thread.daemon = True
    processor_thread.start()
    logger.info("Webhook processor thread started")

    # Start Flask app
    logger.info("Starting Flask application on port 5001")
    app.run(host='0.0.0.0', port=5004, debug=True)
