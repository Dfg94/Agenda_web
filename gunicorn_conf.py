import os

# Puerto proporcionado por Render o 5000 por defecto
port = os.environ.get("PORT", "5000")
bind = f"0.0.0.0:{port}"

# Workers para evitar bloqueos en entrada/salida de archivos (datos.json)
workers = 2
threads = 4
worker_class = "gthread"

# Tiempos de espera ampliados por si Render está procesando discos lentos
timeout = 120
keepalive = 5
