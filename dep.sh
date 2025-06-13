#!/bin/bash

echo "=== Исправление systemd конфигурации ==="

# Остановка сервиса
sudo systemctl stop webhook-app

cd /var/www/web

# Исправление gunicorn.conf.py
cat > gunicorn.conf.py << 'EOF'
# Gunicorn configuration file

# Server socket
bind = "127.0.0.1:8000"
backlog = 2048

# Worker processes  
workers = 2
worker_class = "sync"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 100

# Timeout
timeout = 60
keepalive = 2
graceful_timeout = 30

# Application
preload_app = True

# Process naming
proc_name = "webhook-app"

# Logging
errorlog = "/var/www/web/gunicorn_error.log"
accesslog = "/var/www/web/gunicorn_access.log"  
loglevel = "info"

# Environment variables
raw_env = [
    'FLASK_ENV=production',
    'PYTHONPATH=/var/www/web'
]

def on_starting(server):
    server.log.info("Starting Gunicorn webhook application...")

def when_ready(server):
    server.log.info("Gunicorn webhook application is ready")

def post_worker_init(worker):
    worker.log.info("Worker initialized successfully")
EOF

echo "✅ gunicorn.conf.py исправлен"

# Исправление systemd сервиса
sudo tee /etc/systemd/system/webhook-app.service > /dev/null << 'EOF'
[Unit]
Description=Webhook Application with Gunicorn
After=network.target

[Service]
Type=exec
User=www-data
Group=www-data
WorkingDirectory=/var/www/web
Environment=PATH=/var/www/web/venv/bin
Environment=PYTHONPATH=/var/www/web
ExecStart=/var/www/web/venv/bin/gunicorn --config gunicorn.conf.py wsgi:application
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStartSec=60
TimeoutStopSec=10

# Restart policy
Restart=always
RestartSec=3

# Security settings
NoNewPrivileges=yes
ProtectSystem=strict
ReadWritePaths=/var/www/web
ProtectHome=yes

# Resource limits
LimitNOFILE=65536
LimitNPROC=4096

[Install]
WantedBy=multi-user.target
EOF

echo "✅ systemd сервис исправлен"

# Перезагрузка systemd
sudo systemctl daemon-reload
echo "✅ systemd перезагружен"

# Запуск сервиса
echo "🚀 Запуск сервиса..."
sudo systemctl start webhook-app

# Ожидание запуска
sleep 5

# Проверка статуса
if sudo systemctl is-active --quiet webhook-app; then
    echo "✅ Сервис запущен успешно"
    
    # Показать краткий статус
    sudo systemctl status webhook-app --no-pager -l | head -15
    
    echo ""
    echo "🧪 Тестирование..."
    sleep 2
    
    # Тест статуса
    if curl -s http://127.0.0.1:8000/status > /dev/null; then
        echo "✅ Приложение отвечает"
        
        # Тест webhook
        RESPONSE=$(curl -s "http://127.0.0.1:8000/hook1/webhook?name=test&summa=500")
        if echo "$RESPONSE" | grep -q "processed"; then
            echo "✅ Webhook работает"
        else
            echo "⚠️ Webhook: $RESPONSE"
        fi
        
        # Показать статус
        echo ""
        echo "📊 Статус приложения:"
        curl -s http://127.0.0.1:8000/status | python3 -m json.tool 2>/dev/null || echo "Не удалось распарсить JSON"
        
    else
        echo "❌ Приложение не отвечает"
    fi
    
else
    echo "❌ Сервис не запустился"
    echo "Последние логи:"
    sudo journalctl -u webhook-app --no-pager -l | tail -10
fi

echo ""
echo "=== Завершено ==="
echo "Проверить: curl https://webhookbitrix24danil.ru/status"
echo "Логи: sudo journalctl -u webhook-app -f"