import os
import json
import logging
import subprocess
import threading
import queue

logger = logging.getLogger(__name__)

class MCPClient:
    def __init__(self, command, args=None):
        """
        Inisialisasi MCP Client yang menjalankan server via subprocess (Stdio).
        """
        self.command = command
        self.args = args or []
        self.process = None
        self.request_id = 0
        self.pending_requests = {}
        self.tools = []
        self.is_connected = False
        
        # Queue untuk membaca output
        self.response_queue = queue.Queue()

    def connect(self):
        """Jalankan server dan handshake"""
        try:
            full_cmd = [self.command] + self.args
            logger.info(f"Starting MCP Server: {full_cmd}")
            
            # Start subprocess dengan pipe untuk stdin/stdout
            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1 # Line buffered
            )
            
            # Start thread untuk baca stdout
            threading.Thread(target=self._read_loop, daemon=True).start()
            threading.Thread(target=self._error_loop, daemon=True).start()
            
            # Initialize (Handshake)
            init_result = self.send_request("initialize", {
                "protocolVersion": "0.1.0",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "gemini-python-client",
                    "version": "1.0.0"
                }
            })
            
            if init_result:
                self.send_notification("notifications/initialized")
                self.is_connected = True
                logger.info("MCP Server initialized successfully!")
                
                # Discover Tools
                self._refresh_tools()
                return True
                
        except Exception as e:
            logger.error(f"Failed to connect to MCP Server: {e}")
            return False
        return False

    def _read_loop(self):
        """Loop membaca stdout dari server"""
        while self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if line:
                try:
                    message = json.loads(line)
                    if "id" in message and message["id"] in self.pending_requests:
                        # Response untuk request kita
                        self.pending_requests[message["id"]].put(message)
                    else:
                        # Notification atau request dari server (belum dihandle)
                        pass
                except json.JSONDecodeError:
                    pass

    def _error_loop(self):
        """Loop membaca stderr (log) dari server"""
        while self.process and self.process.poll() is None:
            line = self.process.stderr.readline()
            if line:
                # logger.debug(f"MCP STDERR: {line.strip()}")
                pass

    def send_request(self, method, params=None):
        """Kirim JSON-RPC Request"""
        self.request_id += 1
        req_id = self.request_id
        
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        
        # Siapkan queue untuk response
        resp_queue = queue.Queue()
        self.pending_requests[req_id] = resp_queue
        
        # Kirim
        try:
            json_str = json.dumps(request)
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()
        except Exception as e:
            logger.error(f"Failed to send request: {e}")
            return None
            
        # Tunggu response (timeout 10s)
        try:
            response = resp_queue.get(timeout=10)
            del self.pending_requests[req_id]
            
            if "error" in response:
                logger.error(f"MCP Error: {response['error']}")
                return None
                
            return response.get("result")
        except queue.Empty:
            logger.error(f"MCP Request timeout: {method}")
            return None

    def send_notification(self, method, params=None):
        """Kirim JSON-RPC Notification (tanpa response)"""
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {}
        }
        try:
            json_str = json.dumps(notification)
            self.process.stdin.write(json_str + "\n")
            self.process.stdin.flush()
        except:
            pass

    def _refresh_tools(self):
        """Ambil daftar tools dari server"""
        result = self.send_request("tools/list")
        if result and "tools" in result:
            self.tools = result["tools"]
            logger.info(f"Discovered {len(self.tools)} tools from MCP Server")

    def get_tool_definitions(self):
        """Konversi MCP tools ke format Gemini API"""
        definitions = []
        for tool in self.tools:
            definitions.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": tool.get("inputSchema", {})
            })
        return definitions

    def call_tool(self, name, arguments):
        """Panggil tool di MCP Server"""
        return self.send_request("tools/call", {
            "name": name,
            "arguments": arguments
        })

    def close(self):
        if self.process:
            self.process.terminate()
