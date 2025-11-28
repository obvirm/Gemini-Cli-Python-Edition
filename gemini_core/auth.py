import os
import json
import socket
import logging
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import urlparse, parse_qs

from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from .config import (
    OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET, OAUTH_SCOPES,
    SIGN_IN_SUCCESS_URL, SIGN_IN_FAILURE_URL
)

logger = logging.getLogger(__name__)

class OAuthCallbackHandler(BaseHTTPRequestHandler):
    """Handler untuk menerima callback dari Google OAuth"""
    def log_message(self, format, *args): pass # Silent logging
    
    def do_GET(self):
        parsed_url = urlparse(self.path)
        if parsed_url.path != '/oauth2callback':
            self.send_response(404)
            return
        
        query_params = parse_qs(parsed_url.query)
        if 'code' in query_params:
            self.send_response(301)
            self.send_header('Location', SIGN_IN_SUCCESS_URL)
            self.end_headers()
            self.server.auth_code = query_params['code'][0]
        else:
            self.send_response(301)
            self.send_header('Location', SIGN_IN_FAILURE_URL)
            self.end_headers()
            self.server.auth_code = None

class GoogleAuth:
    def __init__(self, credentials_file):
        self.credentials_file = credentials_file
        self.creds = None

    def _get_free_port(self):
        sock = socket.socket()
        sock.bind(('localhost', 0))
        port = sock.getsockname()[1]
        sock.close()
        return port

    def authenticate(self, force_login=False):
        """
        Main authentication flow.
        1. Coba load dari file
        2. Jika expired, refresh
        3. Jika tidak ada/invalid, mulai login flow baru
        """
        # 1. Cek Token Cache
        if not force_login and os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r') as f:
                    data = json.load(f)
                    self.creds = Credentials.from_authorized_user_info(data, OAUTH_SCOPES)
                
                if self.creds.valid:
                    return self.creds
                
                if self.creds.expired and self.creds.refresh_token:
                    logger.info("Token expired, refreshing...")
                    self.creds.refresh(Request())
                    self._save_credentials()
                    return self.creds
            except Exception as e:
                logger.warning(f"Error loading saved credentials: {e}")
        
        # 2. Login Baru (Web Flow)
        return self._start_login_flow()

    def _start_login_flow(self):
        logger.info("Starting new login flow...")
        port = self._get_free_port()
        redirect_uri = f'http://localhost:{port}/oauth2callback'
        
        flow = Flow.from_client_config(
            {
                "installed": {
                    "client_id": OAUTH_CLIENT_ID, 
                    "client_secret": OAUTH_CLIENT_SECRET, 
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth", 
                    "token_uri": "https://oauth2.googleapis.com/token"
                }
            },
            scopes=OAUTH_SCOPES,
            redirect_uri=redirect_uri
        )
        
        auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
        logger.info(f"Opening browser for authentication...")
        print(f"Opening browser for authentication...")
        logger.debug(f"Please login in your browser: {auth_url}")
        webbrowser.open(auth_url)
        
        server = HTTPServer(('localhost', port), OAuthCallbackHandler)
        server.timeout = 1 # Check for interrupt every 1 second
        try:
            # Loop until auth_code is received or interrupted
            while not getattr(server, 'auth_code', None):
                server.handle_request()
        except KeyboardInterrupt:
            server.server_close()
            print("\nLogin cancelled by user.")
            raise Exception("Login cancelled by user.")
        finally:
            server.server_close()
        
        if not getattr(server, 'auth_code', None):
            raise Exception("Login failed or cancelled.")
            
        flow.fetch_token(code=server.auth_code)
        self.creds = flow.credentials
        self._save_credentials()
        
        logger.info("Login successful!")
        return self.creds

    def refresh(self):
        """Force refresh token"""
        if self.creds and self.creds.refresh_token:
            logger.info("Refreshing token...")
            self.creds.refresh(Request())
            self._save_credentials()
            return True
        return False

    def _save_credentials(self):
        if self.creds:
            with open(self.credentials_file, 'w') as f:
                f.write(self.creds.to_json())
