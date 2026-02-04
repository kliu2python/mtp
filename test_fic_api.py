from flask import Flask, request, jsonify
import requests
import json
import os
from urllib3.exceptions import InsecureRequestWarning
from config import Config

# Suppress SSL warnings for self-signed certificates
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

# Import configuration
CERT_FILE = Config.CERT_FILE
KEY_FILE = Config.KEY_FILE
CERT_FILES_EXIST = Config.CERT_FILES_EXIST

app = Flask(__name__)

class FTMFICAPIServer:
    def __init__(self):
        self.sessions = {}  # Store active sessions

    def portal_login(self, server_ip, account_id, port=8689):
        """
        Perform portal login to establish a session
        """
        url = f"https://{server_ip}:{port}/login"

        payload = {
            'h_key': json.dumps({"account_id": account_id})
        }

        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }

        # Prepare SSL certificate parameters
        ssl_params = {}
        if CERT_FILES_EXIST:
            ssl_params['cert'] = (CERT_FILE, KEY_FILE)

        # Always disable SSL verification for self-signed certificates
        ssl_params['verify'] = False

        try:
            response = requests.post(url, data=payload, headers=headers, **ssl_params)

            # Status 200 or 201 both indicate successful login
            if response.status_code in [200, 201]:
                # Store session information
                session_key = f"{server_ip}_{account_id}"
                self.sessions[session_key] = {
                    'server_ip': server_ip,
                    'account_id': account_id,
                    'port': port,
                    'session_data': response.json() if response.content else {},
                    'cookies': response.cookies
                }
                return {
                    'success': True,
                    'session_key': session_key,
                    'data': response.json() if response.content else {}
                }
            else:
                return {
                    'success': False,
                    'error': f"Login failed with status {response.status_code}",
                    'details': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def make_authenticated_request(self, session_key, method, endpoint, data=None, params=None):
        """
        Make an authenticated request using an existing session
        """
        if session_key not in self.sessions:
            return {
                'success': False,
                'error': 'Session not found. Please login first.'
            }

        session = self.sessions[session_key]
        server_ip = session['server_ip']
        port = session['port']
        cookies = session['cookies']

        url = f"https://{server_ip}:{port}/api/v1/{endpoint}"

        headers = {
            'Content-Type': 'application/json'
        }

        try:
            # Prepare SSL certificate parameters
            ssl_params = {}
            if CERT_FILES_EXIST:
                ssl_params['cert'] = (CERT_FILE, KEY_FILE)

            # Always disable SSL verification for self-signed certificates
            ssl_params['verify'] = False

            if method.upper() == 'GET':
                response = requests.get(url, headers=headers, params=params, cookies=cookies, **ssl_params)
            elif method.upper() == 'POST':
                response = requests.post(url, headers=headers, json=data, cookies=cookies, **ssl_params)
            elif method.upper() == 'PUT':
                response = requests.put(url, headers=headers, json=data, cookies=cookies, **ssl_params)
            elif method.upper() == 'DELETE':
                response = requests.delete(url, headers=headers, json=data, cookies=cookies, **ssl_params)
            else:
                return {
                    'success': False,
                    'error': f'Unsupported HTTP method: {method}'
                }

            # Status 200 or 201 both indicate successful requests
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': response.json() if response.content else {}
                }
            else:
                return {
                    'success': False,
                    'error': f"Request failed with status {response.status_code}",
                    'details': response.text
                }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

# Initialize the API server
api_server = FTMFICAPIServer()

@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy'})

@app.route('/login', methods=['POST'])
def login():
    """
    Login endpoint to establish a session with FortiToken Cloud
    Expected JSON payload:
    {
        "server_ip": "10.160.83.46",
        "account_id": 1224184,
        "port": 8689  # Optional, defaults to 8689
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'success': False, 'error': 'No JSON data provided'}), 400

        server_ip = data.get('server_ip')
        account_id = data.get('account_id')
        port = data.get('port', 8689)

        if not server_ip or not account_id:
            return jsonify({
                'success': False,
                'error': 'Both server_ip and account_id are required'
            }), 400

        result = api_server.portal_login(server_ip, account_id, port)
        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/<path:endpoint>', methods=['GET', 'POST', 'PUT', 'DELETE'])
def proxy_request(endpoint):
    """
    Proxy endpoint for making authenticated requests to FortiToken Cloud API
    Expected headers:
    - X-Session-Key: Session key returned from login

    Query parameters and JSON body will be forwarded to the API
    """
    try:
        # Get session key from headers
        session_key = request.headers.get('X-Session-Key')
        if not session_key:
            return jsonify({
                'success': False,
                'error': 'X-Session-Key header is required'
            }), 400

        method = request.method
        data = request.get_json() if request.is_json else None
        params = request.args.to_dict()

        result = api_server.make_authenticated_request(
            session_key, method, endpoint, data, params
        )

        status_code = 200 if result['success'] else 400
        return jsonify(result), status_code

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/sessions', methods=['GET'])
def list_sessions():
    """
    List all active sessions
    """
    return jsonify({
        'success': True,
        'sessions': list(api_server.sessions.keys())
    })

if __name__ == '__main__':
    app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)