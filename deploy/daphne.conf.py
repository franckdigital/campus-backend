# Daphne configuration for WebSocket
# Run with: daphne -b 127.0.0.1 -p 8002 config.asgi:application

# Daphne settings (passed as command line args)
DAPHNE_SETTINGS = {
    'bind': '127.0.0.1',
    'port': 8002,
    'verbosity': 1,
    'access_log': '/var/log/campus/daphne_access.log',
}
