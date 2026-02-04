import os

class Config:
    # SSL certificate paths
    CERT_FILE = os.environ.get('CERT_FILE', 'server.crt')
    KEY_FILE = os.environ.get('KEY_FILE', 'server.key')

    # Check if certificate files exist
    CERT_FILES_EXIST = os.path.exists(CERT_FILE) and os.path.exists(KEY_FILE)

    # Server configuration
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_DEBUG', 'false').lower() == 'true'