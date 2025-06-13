#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных webhooks
"""

import sqlite3
import os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = "webhooks.db"

def init_db():
    """Initialize the database with required tables"""
    try:
        # Удаляем старую базу если она пуста
        if os.path.exists(DB_PATH) and os.path.getsize(DB_PATH) == 0:
            os.remove(DB_PATH)
            logger.info("Removed empty database file")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        logger.info("Creating webhooks table...")
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
        logger.info("✅ webhooks table created")

        logger.info("Creating daily_stats table...")
        # Table for storing daily statistics with sum columns (до 46)
        base_columns = "date TEXT PRIMARY KEY, total_count INTEGER DEFAULT 0, total_sum INTEGER DEFAULT 0"
        special_columns = "website_confirmations_sum INTEGER DEFAULT 0, whatsapp_night_sum INTEGER DEFAULT 0, whatsapp_work_sum INTEGER DEFAULT 0"
        
        # Generate hook columns dynamically
        hook_columns = []
        for i in range(1, 47):  # 1-46
            hook_columns.append(f"hook{i}_count INTEGER DEFAULT 0")
            hook_columns.append(f"hook{i}_sum INTEGER DEFAULT 0")
        
        all_columns = f"{base_columns}, {', '.join(hook_columns)}, {special_columns}"
        
        cursor.execute(f'''
        CREATE TABLE IF NOT EXISTS daily_stats (
            {all_columns}
        )
        ''')
        logger.info("✅ daily_stats table created")

        # Проверяем создание таблиц
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        logger.info(f"Created tables: {[table[0] for table in tables]}")

        # Проверяем структуру таблицы webhooks
        cursor.execute("PRAGMA table_info(webhooks)")
        webhook_columns = cursor.fetchall()
        logger.info(f"webhooks table columns: {len(webhook_columns)}")
        for col in webhook_columns:
            logger.info(f"  - {col[1]} ({col[2]})")

        # Проверяем структуру таблицы daily_stats
        cursor.execute("PRAGMA table_info(daily_stats)")
        stats_columns = cursor.fetchall()
        logger.info(f"daily_stats table columns: {len(stats_columns)}")
        logger.info(f"First few columns: {[col[1] for col in stats_columns[:10]]}")

        conn.commit()
        conn.close()
        
        # Проверяем размер файла после создания
        file_size = os.path.getsize(DB_PATH)
        logger.info(f"✅ Database file size after initialization: {file_size} bytes")
        
        if file_size > 0:
            logger.info("🎉 Database initialized successfully!")
            return True
        else:
            logger.error("❌ Database file is still empty after initialization")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error initializing database: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def test_database():
    """Test database functionality"""
    try:
        logger.info("Testing database functionality...")
        
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Test inserting a webhook
        test_data = (
            'hook1_count',
            'Test webhook',
            '500',
            '2025-06-13 15:00:00',
            '13.06.2025',
            '{"test": "data"}'
        )
        
        cursor.execute("""
            INSERT INTO webhooks (hook_type, name, summa, received_at_moscow, processing_date, raw_data)
            VALUES (?, ?, ?, ?, ?, ?)
        """, test_data)
        
        logger.info("✅ Test webhook inserted")
        
        # Test inserting daily stats
        cursor.execute("""
            INSERT OR IGNORE INTO daily_stats (date, total_count, total_sum, hook1_count, hook1_sum)
            VALUES ('13.06.2025', 1, 500, 1, 500)
        """)
        
        logger.info("✅ Test daily stats inserted")
        
        # Verify data
        cursor.execute("SELECT COUNT(*) FROM webhooks")
        webhook_count = cursor.fetchone()[0]
        logger.info(f"📊 Webhooks in database: {webhook_count}")
        
        cursor.execute("SELECT COUNT(*) FROM daily_stats")
        stats_count = cursor.fetchone()[0]
        logger.info(f"📊 Daily stats records: {stats_count}")
        
        conn.commit()
        conn.close()
        
        logger.info("🎉 Database test completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Database test failed: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    logger.info("=== INITIALIZING WEBHOOKS DATABASE ===")
    
    # Check current directory and permissions
    current_dir = os.getcwd()
    logger.info(f"Current directory: {current_dir}")
    logger.info(f"Database path: {os.path.abspath(DB_PATH)}")
    
    # Check write permissions
    try:
        test_file = "test_write.tmp"
        with open(test_file, 'w') as f:
            f.write("test")
        os.remove(test_file)
        logger.info("✅ Write permissions OK")
    except Exception as e:
        logger.error(f"❌ No write permissions: {e}")
        return False
    
    # Initialize database
    if init_db():
        logger.info("Database initialization successful")
        
        # Test database
        if test_database():
            logger.info("Database testing successful")
            
            logger.info("\n=== NEXT STEPS ===")
            logger.info("1. Restart your Flask application")
            logger.info("2. Test a webhook: /hook1/webhook?name=test&summa=500")
            logger.info("3. Check the main page to see if data appears")
            
            return True
        else:
            logger.error("Database testing failed")
            return False
    else:
        logger.error("Database initialization failed")
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 SUCCESS: Database is ready!")
    else:
        print("\n❌ FAILED: Check the logs above")