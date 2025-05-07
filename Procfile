web: sh -c '\
echo "PROCFILE --- Stage 1 - Web process starting"; \
echo "PROCFILE --- Stage 2 - Current directory: $(pwd)"; \
echo "PROCFILE --- Stage 3 - Root directory listing:"; \
ls -la; \
echo "PROCFILE --- Stage 4 - Python version:"; \
python --version; \
echo "PROCFILE --- Stage 5 - Gunicorn version:"; \
gunicorn --version; \
echo "PROCFILE --- Stage 6 - Attempting to start Gunicorn application..."; \
exec gunicorn \
    --bind 0.0.0.0:8080 \
    wsgi:app \
    --workers 1 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --enable-stdio-inheritance \
'