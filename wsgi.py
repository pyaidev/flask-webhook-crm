#!/usr/bin/env python3
"""
WSGI точка входа для Gunicorn
"""

import os
import sys
import logging

# Добавляем текущую директорию в путь
sys.path.insert(0, os.path.dirname(__file__))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Импортируем наше приложение
try:
    from work import app, init_db, logger
    
    # Инициализируем базу данных при запуске
    logger.info("Initializing database for WSGI...")
    init_db()
    logger.info("Database initialized successfully for WSGI")
    
    # Экспортируем приложение для Gunicorn
    application = app
    
except Exception as e:
    logging.error(f"Failed to initialize application: {e}")
    raise

if __name__ == "__main__":
    # Если запускается напрямую
    application.run(host='0.0.0.0', port=8000, debug=False)
