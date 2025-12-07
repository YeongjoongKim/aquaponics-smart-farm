# -------------------------------------------------------------
# flask_app.py
# Central Flask Application Configuration (App Factory)
# Responsible for: 
# 1. Creating the main Flask application instance.
# 2. Registering Blueprints (api.py and dashboard.py).
# 3. Injecting global managers (Config, DB, SensorManager) into Blueprints.
# -------------------------------------------------------------

from flask import Flask, jsonify
from flask_cors import CORS
import os
import logging

# Import Blueprints and manager setup functions
# These modules must expose setup functions to receive global objects
from .api import api_bp, setup_api_managers
from .dashboard import dashboard_bp, setup_dashboard_managers
from .config import ConfigLoader
from .database import DatabaseManager
from .sensors import SensorManager

logger = logging.getLogger(__name__)

def create_app(config: ConfigLoader, db_manager: DatabaseManager, sensor_manager: SensorManager) -> Flask:
    """
    Factory function to create and configure the Flask app.
    
    This function takes the initialized global managers (Config, DB, Sensor)
    and injects them into the API and Dashboard modules before registering them.
    This ensures all parts of the app share the same singletons.
    """
    
    # 1. Initialize Flask app. 
    # Template and static folders are set relative to this 'app' folder structure.
    app = Flask(__name__, 
                template_folder=os.path.join(os.path.dirname(__file__), 'templates'), 
                static_folder=os.path.join(os.path.dirname(__file__), 'static'))

    # Load web server config details from config.json
    web_config = config.get_all().get('web_server', {})
    
    # Configuration settings
    # Set a robust SECRET_KEY (critical for production session security)
    # Priority: Environment Variable > Config File > Default Fallback
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'aquaponics-smart-farm-default-secret-key-12345')
    
    # Set debug mode
    # Priority: FLASK_DEBUG env var (handled by Flask internals usually, but explicit here for clarity) > config.json > False
    # Note: In production (Docker), FLASK_DEBUG=0 is set, so this will be False.
    debug_env = os.environ.get('FLASK_DEBUG')
    if debug_env is not None:
        app.config['DEBUG'] = (debug_env == '1' or debug_env.lower() == 'true')
    else:
        app.config['DEBUG'] = web_config.get('debug_mode', False)
    
    # 2. Initialize CORS (Allows cross-origin requests from the dashboard/other devices)
    # Allows all origins (*) for local LAN access, as per API.md specification.
    # In a stricter environment, you might restrict this to specific domains.
    CORS(app) 
    logger.info("CORS enabled for all origins (*).")
    
    # 3. Inject global managers into Blueprints (Dependency Injection)
    # Pass the core initialized objects to the Blueprint modules for method access.
    # This avoids circular imports and ensures shared state.
    setup_api_managers(config, db_manager, sensor_manager)
    setup_dashboard_managers(config, db_manager)
    
    # 4. Register Blueprints
    # The API is prefixed with /api, the Dashboard is at the root.
    app.register_blueprint(api_bp)       # /api/... endpoints
    app.register_blueprint(dashboard_bp) # / and /settings endpoints

    # 5. Basic Error Handler for unhandled exceptions
    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Unhandled Server Error: {e}")
        # Return JSON for API clients, could be improved to return HTML for browser users
        return jsonify({"status": "error", "message": "Internal Server Error"}), 500

    @app.errorhandler(404)
    def page_not_found(e):
        return jsonify({"status": "error", "message": "Resource not found"}), 404

    logger.info(f"Flask Application created. Debug Mode: {app.config['DEBUG']}")
    
    # Note: Gunicorn will run this factory function to get the 'app' object.
    return app