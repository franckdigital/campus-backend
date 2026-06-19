# Gunicorn configuration file
import multiprocessing

# Bind
bind = "127.0.0.1:8001"

# Workers
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 5

# Logging
accesslog = "/var/log/campus/gunicorn_access.log"
errorlog = "/var/log/campus/gunicorn_error.log"
loglevel = "info"

# Process naming
proc_name = "campus_gunicorn"

# Server mechanics
daemon = False
pidfile = "/var/run/campus/gunicorn.pid"
user = "www-data"
group = "www-data"

# SSL (if needed, otherwise use Nginx for SSL termination)
# keyfile = "/etc/ssl/private/campus.key"
# certfile = "/etc/ssl/certs/campus.crt"
