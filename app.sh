#!/bin/bash
source /var/app/venv/*/bin/activate
echo "Starting pip install" > /var/log/app.log 2>&1
pip install -r /var/app/staging/requirements.txt >> /var/log/app.log 2>&1 || { echo "pip install failed" >> /var/log/app.log; exit 1; }
echo "Starting Gunicorn" >> /var/log/app.log 2>&1
gunicorn -k uvicorn.workers.UvicornWorker main:app --bind 0.0.0.0:8000 --timeout 60 --log-level debug >> /var/log/app.log 2>&1