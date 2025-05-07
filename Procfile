web: sh -c ' \
    echo "PROCFILE - Step 1: Attempting to start Gunicorn..." && \
    echo "PROCFILE - Step 2: Current directory: $(pwd)" && \
    echo "PROCFILE - Step 3: Listing root directory contents:" && \
    ls -la && \
    echo "PROCFILE - Step 4: Checking wsgi.py content (if exists):" && \
    (test -f wsgi.py && cat wsgi.py || echo "PROCFILE - wsgi.py not found in root") && \
    echo "PROCFILE - Step 5: Checking run.py content (if exists):" && \
    (test -f run.py && cat run.py || echo "PROCFILE - run.py not found in root") && \
    echo "PROCFILE - Step 6: Python version: $(python --version)" && \
    echo "PROCFILE - Step 7: Gunicorn version: $(gunicorn --version)" && \
    echo "PROCFILE - Step 8: Starting Gunicorn with explicit logging..." && \
    exec gunicorn \
      --bind 0.0.0.0:8080 \
      wsgi:app \
      --workers 1 \
      --log-level debug \
      --access-logfile - \
      --error-logfile - \
      --enable-stdio-inheritance \
    '