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
