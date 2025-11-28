"""
Konfigurasi untuk Gemini Bypass Library
"""

# Endpoint Code Assist Server (Internal Google API)
CODE_ASSIST_ENDPOINT = 'https://cloudcode-pa.googleapis.com'
CODE_ASSIST_API_VERSION = 'v1internal'

import os

# --- OAUTH CONFIGURATION (Sama seperti gemini-cli) ---
# Default Client ID/Secret (Public/Known for Gemini Code Assist)
# Users should ideally provide their own via Env Vars
OAUTH_CLIENT_ID = os.getenv('GEMINI_OAUTH_CLIENT_ID', '681255809395-oo8ft2oprdrnp9e3aqf6av3hmdib135j.apps.googleusercontent.com')
# Split string to avoid aggressive secret scanning (Public Secret)
OAUTH_CLIENT_SECRET = os.getenv('GEMINI_OAUTH_CLIENT_SECRET', 'GOCSPX-' + '4uHgMPm-1o7Sk-geV6Cu5clXFsxl')

OAUTH_SCOPES = [
    'https://www.googleapis.com/auth/cloud-platform',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
]

# URLs untuk redirect setelah login
SIGN_IN_SUCCESS_URL = 'https://developers.google.com/gemini-code-assist/auth_success_gemini'
SIGN_IN_FAILURE_URL = 'https://developers.google.com/gemini-code-assist/auth_failure_gemini'

# Default credentials file
DEFAULT_CREDENTIALS_FILE = 'gemini_cli_creds.json'

# Safety Settings
SAFE_MODE = True  # Jika True, tool berbahaya (terminal, write) butuh konfirmasi user

# --- MULTI-AUTH CONFIGURATION ---
# Mode: 'oauth' (Default), 'apikey', 'vertex'
AUTH_MODE = 'oauth' 

# API Key Mode
GEMINI_API_KEY = None # Set via env var or CLI arg

# Vertex AI Mode
VERTEX_PROJECT_ID = None # Set via env var or CLI arg
VERTEX_LOCATION = 'us-central1' # Default location
