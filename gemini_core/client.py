import os
import json
import time
import logging
import requests
from .config import CODE_ASSIST_ENDPOINT, CODE_ASSIST_API_VERSION
from .auth import GoogleAuth

logger = logging.getLogger(__name__)

class GeminiClient:
    def __init__(self, credentials_file, auth_mode='oauth', api_key=None, vertex_project=None, vertex_location='us-central1'):
        self.auth_mode = auth_mode
        self.api_key = api_key
        self.vertex_project = vertex_project
        self.vertex_location = vertex_location
        
        self.auth = None
        self.creds = None
        
        # OAuth & Vertex butuh GoogleAuth
        if self.auth_mode in ['oauth', 'vertex']:
            self.auth = GoogleAuth(credentials_file)
            self.creds = self.auth.authenticate() 
            
        self.project_id = None
        self.user_tier = None
        self.session_setup = False

    def _get_headers(self):
        if self.auth_mode == 'apikey':
            return {'Content-Type': 'application/json'}
            
        return {
            'Authorization': f'Bearer {self.creds.token}',
            'Content-Type': 'application/json',
        }

    def _request(self, method, payload=None, stream=False):
        """Helper untuk melakukan request ke Code Assist Server"""
        url = f"{CODE_ASSIST_ENDPOINT}/{CODE_ASSIST_API_VERSION}:{method}"
        if stream:
            url += "?alt=sse"
        
        try:
            response = requests.post(
                url, 
                headers=self._get_headers(), 
                json=payload or {},
                stream=stream
            )
            return response
        except Exception as e:
            logger.error(f"Request failed: {e}")
            return None

    def setup_user(self):
        """
        Melakukan onboarding user untuk mendapatkan managed project ID.
        Ini adalah kunci untuk mendapatkan akses unlimited (standard tier).
        """
        if self.session_setup:
            return

        if self.auth_mode != 'oauth':
            # API Key & Vertex tidak butuh onboarding
            self.session_setup = True
            return

        logger.info("Setting up user session (Onboarding)...")
        
        # 1. Cek status user saat ini
        env_project = os.getenv('GOOGLE_CLOUD_PROJECT') or os.getenv('GOOGLE_CLOUD_PROJECT_ID')
        
        load_payload = {
            'cloudaicompanionProject': env_project,
            'metadata': {
                'ideType': 'IDE_UNSPECIFIED',
                'platform': 'PLATFORM_UNSPECIFIED',
                'pluginType': 'GEMINI',
                'duetProject': env_project,
            }
        }
        
        res = self._request('loadCodeAssist', load_payload)
        if not res or res.status_code != 200:
            raise Exception("Gagal loadCodeAssist")
            
        load_data = res.json()
        
        # Jika sudah punya tier, gunakan itu
        if load_data.get('currentTier'):
            self.user_tier = load_data['currentTier'].get('id')
            self.project_id = load_data.get('cloudaicompanionProject', env_project)
            self.session_setup = True
            logger.info(f"User already setup. Project: {self.project_id}, Tier: {self.user_tier}")
            return

        # 2. Jika belum, lakukan onboarding
        logger.info("User belum setup, melakukan onboarding...")
        
        # Tentukan tier (default FREE/STANDARD)
        tier_id = 'FREE'
        if load_data.get('allowedTiers'):
            for tier in load_data['allowedTiers']:
                if tier.get('isDefault'):
                    tier_id = tier.get('id', 'FREE')
                    break
        
        # Payload onboarding
        # PENTING: Untuk FREE tier, cloudaicompanionProject harus NULL/None
        onboard_payload = {
            'tierId': tier_id,
            'cloudaicompanionProject': None if tier_id == 'FREE' else env_project,
            'metadata': {
                'ideType': 'IDE_UNSPECIFIED',
                'platform': 'PLATFORM_UNSPECIFIED',
                'pluginType': 'GEMINI',
            }
        }
        
        # Poll sampai selesai
        lro_res = self._request('onboardUser', onboard_payload)
        if not lro_res:
            raise Exception("Gagal start onboarding")
            
        lro_data = lro_res.json()
        max_polls = 10
        poll_count = 0
        
        while not lro_data.get('done') and poll_count < max_polls:
            poll_count += 1
            logger.info(f"Polling onboarding status ({poll_count}/{max_polls})...")
            time.sleep(3)
            lro_res = self._request('onboardUser', onboard_payload)
            if lro_res:
                lro_data = lro_res.json()
            else:
                break
        
        if not lro_data.get('done'):
            raise Exception("Onboarding timeout")
            
        # Extract project ID hasil onboarding
        if lro_data.get('response', {}).get('cloudaicompanionProject', {}).get('id'):
            self.project_id = lro_data['response']['cloudaicompanionProject']['id']
        else:
            self.project_id = env_project
            
        self.user_tier = tier_id
        self.session_setup = True
        logger.info(f"Onboarding sukses! Project: {self.project_id}, Tier: {self.user_tier}")

    def _request_generate(self, payload):
        """Internal method untuk kirim request generate dan parse response"""
        logger.info(f"Sending request to {payload['model']}...")
        
        # DEBUG: Print Payload Content Structure
        # if 'request' in payload and 'contents' in payload['request']:
        #     print(f"DEBUG PAYLOAD CONTENTS: {json.dumps(payload['request']['contents'], indent=2)}")
            
        # Determine URL & Payload based on Mode
        if self.auth_mode == 'apikey':
            if not self.api_key:
                return {'success': False, 'error': "API Key is missing!"}
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{payload['model']}:streamGenerateContent?key={self.api_key}&alt=sse"
            json_payload = payload['request'] # Direct payload
            
        elif self.auth_mode == 'vertex':
            if not self.vertex_project:
                return {'success': False, 'error': "Vertex Project ID is missing!"}
            url = f"https://{self.vertex_location}-aiplatform.googleapis.com/v1/projects/{self.vertex_project}/locations/{self.vertex_location}/publishers/google/models/{payload['model']}:streamGenerateContent?alt=sse"
            json_payload = payload['request'] # Direct payload
            
        else: # oauth (Internal API)
            url = f"{CODE_ASSIST_ENDPOINT}/{CODE_ASSIST_API_VERSION}:streamGenerateContent?alt=sse"
            json_payload = payload # Wrapped payload
            
        headers = self._get_headers()
        
        try:
            response = requests.post(url, headers=headers, json=json_payload, stream=True)
            
            # DEBUG: Cek status code
            if response.status_code != 200:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', response.text)
                    if response.status_code == 429:
                        return {'success': False, 'error': f"⏳ RATE LIMIT: {error_msg}"}
                    return {'success': False, 'error': f"API Error {response.status_code}: {error_msg}"}
                except:
                    return {'success': False, 'error': f"HTTP {response.status_code}"}
                
            final_text = []
            function_calls = []
            thought_signature = None
            
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8')
                    if decoded_line.startswith('data: '):
                        try:
                            json_str = decoded_line[6:] # Skip 'data: '
                            data = json.loads(json_str)
                            
                            # ... (error handling & wrapper logic sama) ...
                            if 'error' in data:
                                return {'success': False, 'error': data['error']['message']}
                            
                            actual_data = data.get('response', data)
                            
                            if 'candidates' in actual_data and len(actual_data['candidates']) > 0:
                                candidate = actual_data['candidates'][0]
                                if 'content' in candidate and 'parts' in candidate['content']:
                                    for part in candidate['content']['parts']:
                                        if 'text' in part:
                                            final_text.append(part['text'])
                                        if 'functionCall' in part:
                                            function_calls.append(part['functionCall'])
                                        if 'thoughtSignature' in part:
                                            thought_signature = part['thoughtSignature']
                                            
                        except json.JSONDecodeError:
                            pass
                            
            if not final_text and not function_calls:
                 return {'success': False, 'error': "Unknown error (Empty response)"}

            return {
                'success': True,
                'text': "".join(final_text),
                'function_calls': function_calls,
                'thought_signature': thought_signature
            }
            
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def generate_content(self, model, prompt, tools=None, system_instruction=None, media_items=None):
        """
        Generate content menggunakan Gemini model via Code Assist Server.
        Support Function Calling (Tools), System Instruction, & Multimodal (Images/Video).
        
        Args:
            media_items (list): List of dict {'mime_type': str, 'data': base64_str}
        """
        if not self.session_setup:
            self.setup_user()
            
        parts = [{"text": prompt}]
        
        # Inject Media (Images/Video)
        if media_items:
            for item in media_items:
                parts.append({
                    "inlineData": {
                        "mimeType": item.get('mime_type', 'image/jpeg'),
                        "data": item.get('data')
                    }
                })
            
        request_payload = {
            "contents": [{
                "role": "user",
                "parts": parts
            }],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 2048,
            }
        }

        # Inject System Instruction
        if system_instruction:
            request_payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        # Inject Tools jika ada
        if tools:
            request_payload["tools"] = [tools.get_tool_definitions()]

        payload = {
            "model": model,
            "project": self.project_id,
            "user_prompt_id": f"python-client-{int(time.time() * 1000)}",
            "request": request_payload
        }
        
        return self._request_generate(payload)
