#!/usr/bin/env python3
"""
Main entry point for the Parking Lot Management System
Flask Application using the application factory pattern
"""

import os
from app import create_app
from flask import Flask

# Create Flask application instance
app = create_app()

if __name__ == '__main__':
    # Configuration for development
    debug_mode = os.environ.get('FLASK_ENV') == 'development'
    port = int(os.environ.get('PORT', 5000))
    host = os.environ.get('HOST', '127.0.0.1')
    
    print(f"Starting Parking Lot Management System API...")
    print(f"Environment: {os.environ.get('FLASK_ENV', 'development')}")
    print(f"Server: http://{host}:{port}")
    print(f"Health check: http://{host}:{port}/health")
    
    app.run(
        host=host,
        port=port,
        debug=debug_mode,
        threaded=True
    )