web: echo "PROCFILE: Attempting to start Gunicorn..." && \
     echo "PROCFILE: Current directory: $(pwd)" && \
     echo "PROCFILE: Listing root directory contents:" && \
     ls -la && \
     echo "PROCFILE: Checking wsgi.py content (if exists):" && \
     (test -f wsgi.py && cat wsgi.py || echo "PROCFILE: wsgi.py not found in root") && \
     echo "PROCFILE: Checking run.py content (if exists):" && \
     (test -f run.py && cat run.py || echo "PROCFILE: run.py not found in root") && \
     echo "PROCFILE: Python version: $(python --version)" && \
     echo "PROCFILE: Gunicorn version: $(gunicorn --version)" && \
     echo "PROCFILE: Starting Gunicorn with explicit logging to stdout/stderr..." && \
     gunicorn \
       --bind 0.0.0.0:8080 \
       wsgi:app \
       --workers 1 \
       --log-level debug \
       --access-logfile - \
       --error-logfile - \
       --enable-stdio-inheritance