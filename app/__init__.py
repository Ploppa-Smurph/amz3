import os
import logging
import base64
import uuid
# Import StreamHandler for logging to stdout/stderr
from logging import StreamHandler
from flask import Flask, render_template, session
from dotenv import load_dotenv
from flask_migrate import Migrate

# Load environment variables (from .env file for local development)
# In Railway, environment variables are set directly in the service settings.
load_dotenv()

# Import shared extensions.
from app.extensions import db, login_manager

def create_app(test_config=None):
    # Determine the project root directory.
    basedir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

    # Create the Flask application.
    # instance_path is less relevant when not using SQLite, but harmless.
    app = Flask(
        __name__,
        template_folder=os.path.join(basedir, 'templates'),
        static_folder=os.path.join(basedir, 'static'),
        instance_path=os.path.join(basedir, 'instance'), # Kept for consistency, less critical now
        instance_relative_config=True # Allows loading config from instance folder if needed
    )

    # --- Configuration Loading ---

    # Set default configuration values
    app.config.from_mapping(
        # IMPORTANT: Set a STRONG secret key in Railway environment variables!
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-insecure-fallback-key'),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SESSION_PERMANENT=False,
        SERVER_RUN_ID=str(uuid.uuid4()) # Used for session invalidation on restart
        # AUTO_CREATE_DB/AUTO_DROP_DB removed as migrations handle this
    )

    # Determine Database URI based on environment (Prioritize Railway's DATABASE_URL)
    database_url = os.getenv('DATABASE_URL') # Railway provides this automatically when DB is linked

    if database_url:
        # Production (Railway) or local development using DATABASE_URL
        # Railway uses postgres:// prefix, SQLAlchemy needs postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.logger.info("Using PostgreSQL database from DATABASE_URL.")
    else:
        # Fallback for local development if DATABASE_URL is not set
        app.logger.warning("DATABASE_URL environment variable not found.")
        app.logger.warning("Falling back to local SQLite database (instance/site.db).")
        # Ensure instance folder exists for SQLite fallback
        instance_path = app.instance_path # Use path from app object
        try:
            os.makedirs(instance_path)
            app.logger.info(f"Created instance folder: {instance_path}")
        except OSError:
            pass # Folder already exists
        sqlite_uri = 'sqlite:///' + os.path.join(instance_path, 'site.db')
        app.config['SQLALCHEMY_DATABASE_URI'] = sqlite_uri

    # Override configuration if test_config is provided (useful for testing)
    if test_config is not None:
        app.config.update(test_config)

    # --- Initialize Extensions ---
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login' # Blueprint name 'auth', route 'login'
    login_manager.login_message_category = 'info'

    # Initialize Flask-Migrate AFTER db is initialized
    # Migrations need to be run separately (e.g., `flask db upgrade`)
    Migrate(app, db)

    # --- Configure Logging for Railway ---
    # Remove file-based logging; log to stdout/stderr so Railway can capture it.
    if not app.debug and not app.testing:
        # Remove default Flask handler if it exists
        # (Sometimes needed, sometimes not, depending on Flask version)
        # from flask.logging import default_handler
        # app.logger.removeHandler(default_handler)

        stream_handler = StreamHandler() # Logs to stderr by default
        stream_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
        ))
        # Set level based on environment variable or default to INFO
        log_level = os.getenv('LOG_LEVEL', 'INFO').upper()
        app.logger.setLevel(getattr(logging, log_level, logging.INFO))
        stream_handler.setLevel(getattr(logging, log_level, logging.INFO))

        # Clear existing handlers and add our stream handler
        # Be careful if other extensions add handlers
        app.logger.handlers.clear()
        app.logger.addHandler(stream_handler)
        app.logger.info('Flask app startup - Logging configured for Railway (stdout/stderr)')


    # --- Register Blueprints ---
    # Ensure blueprint imports are correct relative to the app package
    from app.blueprints.reports import reports_bp
    from app.blueprints.auth import auth_bp
    app.register_blueprint(reports_bp, url_prefix='/reports')
    app.register_blueprint(auth_bp, url_prefix='/auth')

    # --- Register Custom Jinja Filters ---
    @app.template_filter('b64str')
    def b64str_filter(data):
        if not data:
            return ''
        return base64.b64encode(data).decode('utf-8')
    app.jinja_env.filters['b64str'] = b64str_filter

    # Assuming amazon_utils is setup correctly for S3 access
    try:
        from app.utils.amazon_utils import get_public_url
        @app.template_filter('public_url')
        def public_url_filter(key):
            return get_public_url(key)
        app.jinja_env.filters['public_url'] = public_url_filter
    except ImportError:
        app.logger.warning("Could not import amazon_utils. 'public_url' filter not available.")
        pass # Or handle differently if S3 is essential


    # --- Define Base Routes ---
    @app.route('/')
    def home():
        return render_template('home.html')

    @app.route('/about')
    def about():
        return render_template('about.html')

    @app.route('/future-plans')
    def future_plans():
        return render_template('future_plans.html')

    @app.route('/contact')
    def contact():
        # Consider creating a separate contact.html or redirecting
        return render_template('about.html') # Currently reusing about.html

    # --- Custom Error Handlers ---
    @app.errorhandler(404)
    def page_not_found(error):
        return render_template('404.html'), 404

    # --- Request Hooks ---
    from flask_login import current_user, logout_user
    @app.before_request
    def invalidate_old_session():
        """Invalidate session if server has restarted since session was created."""
        if current_user.is_authenticated:
            # Check if the server run ID stored in session matches current server run ID
            if session.get('server_run_id') != app.config.get('SERVER_RUN_ID'):
                app.logger.info(f"Server restart detected. Invalidating session for user {current_user.id}")
                logout_user() # Logs out the user
                session.clear() # Clears the session data


    # --- Default Admin Creation (Run once at startup if needed) ---
    # This runs within the app context after initialization.
    # Be cautious running database operations directly at startup in stateless environments.
    # Consider using a dedicated CLI command for setup if possible.
    with app.app_context():
        try:
            # Check if we have a database connection configured first
            if not app.config.get('SQLALCHEMY_DATABASE_URI'):
                app.logger.warning("Skipping default admin creation: Database URI not configured.")
            else:
                from sqlalchemy import inspect
                from sqlalchemy.exc import OperationalError, ProgrammingError
                inspector = inspect(db.engine)
                if inspector.has_table("users"): # Check if table exists first
                    from app.models import User # Import User model here
                    admin_user = os.getenv('ADMIN_USERNAME', 'admin')
                    admin_pass = os.getenv('DEFAULT_ADMIN_PASSWORD') # Get password from env
                    admin_email = os.getenv('ADMIN_EMAIL', 'admin@example.com')

                    if not admin_pass:
                        app.logger.warning("DEFAULT_ADMIN_PASSWORD not set, using insecure default 'password'. SET THIS IN RAILWAY!")
                        admin_pass = "password"

                    admin = User.query.filter_by(username=admin_user).first()
                    if admin:
                        if admin.role != "admin":
                            admin.role = "admin"
                            # Optionally update password if needed, be careful here
                            # admin.set_password(admin_pass)
                            db.session.commit()
                            app.logger.info(f"Existing user '{admin_user}' updated to admin permissions.")
                        # else:
                        #    app.logger.info(f"Admin user '{admin_user}' already exists with proper permissions.")
                    else:
                        app.logger.info(f"Creating default admin user: '{admin_user}'")
                        admin = User(username=admin_user, email=admin_email, role="admin")
                        admin.set_password(admin_pass) # Hash the password
                        db.session.add(admin)
                        db.session.commit()
                        app.logger.info(f"Default admin user '{admin_user}' created.")
                else:
                    app.logger.warning("Skipping default admin creation: 'users' table does not exist. Run migrations first.")
        # Catch specific DB connection errors during inspection/query
        except (OperationalError, ProgrammingError) as db_err:
             app.logger.error(f"Database connection error during admin check/creation: {db_err}")
        except Exception as e:
            # Catch any other unexpected errors
            app.logger.error(f"Unexpected error during default admin check/creation: {e}", exc_info=True)


    # Note: Database creation/updates are handled by `flask db upgrade`.
    # This command should be run as part of your Railway deployment process
    # (e.g., in the Deploy Command section of your service settings).

    return app

# Optional: Keep __all__ if other parts of your project rely on it.
# __all__ = ['create_app', 'db']