import logging
import time
from .tools import registry

logger = logging.getLogger(__name__)

class ChatSession:
    def __init__(self, client, model='gemini-3-pro-preview', system_instruction=None):
        self.client = client
        self.model = model
        self.system_instruction = system_instruction
        self.history = [] # List of content objects
        self.tools = registry

    # ... (send_message method tetap sama) ...

    def _generate_with_history(self):
        """Internal helper untuk call API dengan full history"""
        if not self.client.session_setup:
            self.client.setup_user()
            
        request_payload = {
            "contents": self.history,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 4096,
            },
            "tools": [self.tools.get_tool_definitions()]
        }

        # Inject System Instruction
        if self.system_instruction:
            request_payload["systemInstruction"] = {
                "parts": [{"text": self.system_instruction}]
            }

        payload = {
            "model": self.model,
            "project": self.client.project_id,
            "user_prompt_id": f"chat-{int(time.time() * 1000)}",
            "request": request_payload
        }
        
        return self.client._request_generate(payload)

    def send_message(self, message, media_items=None, stream_callback=None):
        """
        Mengirim pesan user dan menangani loop tool execution secara otomatis.
        
        Args:
            message (str): Pesan user.
            media_items (list): List of dict {'mime_type': str, 'data': base64_str} (optional).
            stream_callback (func): Fungsi untuk streaming text output (opsional).
        
        Returns:
            str: Jawaban final dari model.
        """
        # 1. Tambahkan pesan user ke history
        parts = [{"text": message}]
        if media_items:
            for item in media_items:
                parts.append({
                    "inlineData": {
                        "mimeType": item.get('mime_type', 'image/jpeg'), 
                        "data": item.get('data')
                    }
                })
                
        user_content = {
            "role": "user",
            "parts": parts
        }
        self.history.append(user_content)
        
        # Loop untuk menangani multi-turn tool execution
        max_turns = 10
        current_turn = 0
        
        while current_turn < max_turns:
            current_turn += 1
            
            # Kirim request ke API dengan history lengkap
            response = self._generate_with_history()
            
            if not response['success']:
                return f"Error: {response.get('error')}"
            
            # Handle Text Response (Streaming)
            text_response = response.get('text', '')
            if text_response:
                if stream_callback:
                    stream_callback(text_response)
            
            # Handle Function Calls
            function_calls = response.get('function_calls')
            
            if not function_calls:
                # Jika tidak ada function call, berarti ini jawaban final
                # Simpan jawaban model ke history
                model_content = {
                    "role": "model",
                    "parts": [{"text": text_response}]
                }
                self.history.append(model_content)
                return text_response
            
            # Jika ada function call, eksekusi tool
            # Simpan request function call ke history dulu (PENTING!)
            fc_parts = []
            
            # PENTING: Sertakan thoughtSignature jika ada!
            thought_sig = response.get('thought_signature')
            # print(f"DEBUG: Captured Thought Signature: {thought_sig[:20]}..." if thought_sig else "DEBUG: No Thought Signature captured!")
            
            # if thought_sig:
            #    fc_parts.append({"thoughtSignature": thought_sig})

            if text_response:
                fc_parts.append({"text": text_response})
            
            for fc in function_calls:
                part_dict = {"functionCall": fc}
                if thought_sig:
                    part_dict["thoughtSignature"] = thought_sig
                fc_parts.append(part_dict)
            
            self.history.append({
                "role": "model",
                "parts": fc_parts
            })
            
            # Eksekusi setiap tool dan kumpulkan hasilnya
            fr_parts = []
            for fc in function_calls:
                tool_name = fc['name']
                args = fc['args']
                
                if stream_callback:
                    stream_callback(f"\n[Running tool: {tool_name}({args})]\n")
                
                # Execute
                tool_result = self.tools.execute(tool_name, args)
                
                # Format Function Response
                fr_parts.append({
                    "functionResponse": {
                        "name": tool_name,
                        "response": {"name": tool_name, "content": str(tool_result)}
                    }
                })
                
                if stream_callback:
                    # Tampilkan preview hasil (dipotong biar gak kepanjangan)
                    preview = str(tool_result)[:200] + "..." if len(str(tool_result)) > 200 else str(tool_result)
                    stream_callback(f"[Result: {preview}]\n")

            # Tambahkan hasil tool ke history sebagai 'function' role (atau user role dengan functionResponse)
            # Di API Code Assist, biasanya functionResponse dikirim sebagai bagian dari conversation
            self.history.append({
                "role": "user", # Atau 'function' tergantung API version, tapi 'user' biasanya aman
                "parts": fr_parts
            })
            
            # Loop akan berlanjut, mengirim history baru (termasuk hasil tool) ke model
            
        return "Error: Max tool execution turns reached."


