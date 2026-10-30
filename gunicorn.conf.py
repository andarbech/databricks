"""Production WSGI configuration for Databricks Apps and local previews."""

import os

bind = "0.0.0.0:" + os.environ.get("DATABRICKS_APP_PORT", "8000")
workers = 2
threads = 4
timeout = 90
graceful_timeout = 10
accesslog = "-"
errorlog = "-"
preload_app = False
