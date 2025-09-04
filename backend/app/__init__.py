import os
from flask import Flask, render_template
from flask_cors import CORS
from config import config


def create_app(config_name=None):
    """Application factory pattern for Flask app"""
    
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'default')
    
    # Set static and template folders to serve frontend files
    # Go up from backend/app to project root, then to frontend
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    project_root = os.path.dirname(backend_dir)
    frontend_path = os.path.join(project_root, 'frontend')
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    
    # Enable CORS for frontend integration
    CORS(app, supports_credentials=True)
    
    # Configure session
    app.secret_key = app.config['SECRET_KEY']
    
    # Register blueprints
    from .api.kiosk_routes import kiosk_bp
    from .api.hardware_routes import hardware_bp
    from .api.admin_routes import admin_bp
    
    app.register_blueprint(kiosk_bp)
    app.register_blueprint(hardware_bp)
    app.register_blueprint(admin_bp)
    
    # Root route for API health check
    @app.route('/')
    def index():
        return {
            'message': 'Parking Lot Management System API',
            'version': '1.0.0',
            'status': 'running'
        }
    
    # Serve kiosk interface
    @app.route('/kiosk')
    def kiosk():
        return render_template('kiosk/index.html')
    
    # Serve admin interface  
    @app.route('/admin')
    def admin():
        return render_template('admin/index.html')
    
    @app.route('/health')
    def health_check():
        """Health check endpoint"""
        try:
            from .utils.db_connector import db_connector
            # Test database connection
            db_connector.execute_query("SELECT 1 as test", fetch=True)
            return {'status': 'healthy', 'database': 'connected'}
        except Exception as e:
            return {'status': 'unhealthy', 'error': str(e)}, 500
    
    @app.route('/debug/admins')
    def debug_admins():
        """Debug endpoint to check admin records"""
        try:
            from .utils.db_connector import db_connector
            result = db_connector.execute_query("SELECT Username, RoleLevel, PasswordHash FROM ADMINS WHERE Username = %s", ('superadmin',), fetch=True)
            import hashlib
            test_hash = hashlib.sha256('admin123'.encode()).hexdigest().upper()
            return {'admin': result, 'expected_hash': test_hash}
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/debug/fix-passwords')
    def fix_passwords():
        """Fix admin password hashes"""
        try:
            from .utils.db_connector import db_connector
            import hashlib
            correct_hash = hashlib.sha256('admin123'.encode()).hexdigest().upper()
            
            # Update all admin passwords
            result = db_connector.execute_query(
                "UPDATE ADMINS SET PasswordHash = %s", 
                (correct_hash,), 
                fetch=False
            )
            return {'message': f'Updated {result} admin passwords', 'hash': correct_hash}
        except Exception as e:
            return {'error': str(e)}, 500
    
    @app.route('/debug/add-test-vehicle')
    def add_test_vehicle():
        """Add a test vehicle for kiosk testing"""
        try:
            from .utils.db_connector import db_connector
            from datetime import datetime
            
            # Insert test vehicle
            query = """
                INSERT INTO PARKING_RECORD (ParkingLotID, VehicleNumber, EntryTime)
                VALUES (%s, %s, %s)
            """
            
            result = db_connector.execute_query(
                query, 
                (1, 'XYZ-9999', datetime.now()), 
                fetch=False
            )
            
            return {'message': f'Added test vehicle XYZ-9999, rows affected: {result}'}
        except Exception as e:
            return {'error': str(e)}, 500
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Resource not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return {'error': 'Internal server error'}, 500
    
    @app.errorhandler(400)
    def bad_request(error):
        return {'error': 'Bad request'}, 400
    
    return app