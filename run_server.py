#!/usr/bin/env python3
"""
Standalone server runner with comprehensive startup logging
Designed to start the Flask app and stay running
"""

import os
import sys
import logging

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

# Set Flask environment
os.environ['FLASK_APP'] = 'app.py'
os.environ['FLASK_PORT'] = '5000'
os.environ['FLASK_DEBUG'] = 'False'

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)

try:
    from app import app
    
    logger = logging.getLogger(__name__)
    
    print("\n" + "="*70)
    print("DENTALVOICE AI BACKEND SERVER")
    print("="*70)
    
    # Start server
    logger.info("Starting Flask server on http://0.0.0.0:5000")
    logger.info("Press Ctrl+C to stop")
    
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=False,
        use_reloader=False,
        threaded=True
    )
    
except Exception as e:
    print(f"ERROR: Failed to start server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
