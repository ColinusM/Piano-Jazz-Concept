# Gunicorn configuration file
timeout = 120  # 2 minutes for LLM API calls
workers = 1
bind = "0.0.0.0:10000"
