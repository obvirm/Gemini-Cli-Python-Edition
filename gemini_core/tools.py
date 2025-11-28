import os
import json
import logging
import subprocess
import glob

logger = logging.getLogger(__name__)

class ToolRegistry:
    def __init__(self):
        self.tools = {}
        self.mcp_clients = [] # List of connected MCP clients

    def register_mcp(self, mcp_client):
        """Register MCP Client"""
        self.mcp_clients.append(mcp_client)

    def register(self, func):
        """Decorator untuk mendaftarkan tool local"""
        self.tools[func.__name__] = func
        return func

    def get_tool_definitions(self):
        """Mengembalikan definisi tools (Local + MCP)"""
        definitions = []
        
        # 1. Local Tools
        for name, func in self.tools.items():
            description = func.__doc__ or "No description provided"
            parameters = self._get_params_schema(name)
            definitions.append({
                "name": name,
                "description": description,
                "parameters": parameters
            })
            
        # 2. MCP Tools
        for client in self.mcp_clients:
            if client.is_connected:
                definitions.extend(client.get_tool_definitions())
                
        return {"function_declarations": definitions}

    def _get_params_schema(self, func_name):
        """Schema parameter manual"""
        if func_name == "read_file":
            return {
                "type": "OBJECT",
                "properties": {
                    "filepath": {"type": "STRING", "description": "Path absolut atau relatif ke file yang akan dibaca"}
                },
                "required": ["filepath"]
            }
        elif func_name == "write_file":
            return {
                "type": "OBJECT",
                "properties": {
                    "filepath": {"type": "STRING", "description": "Path absolut atau relatif untuk file baru"},
                    "content": {"type": "STRING", "description": "Isi text yang akan ditulis ke file"}
                },
                "required": ["filepath", "content"]
            }
        elif func_name == "list_directory":
            return {
                "type": "OBJECT",
                "properties": {
                    "path": {"type": "STRING", "description": "Path directory yang akan di-list (default: current directory)"}
                },
                "required": []
            }
        elif func_name == "run_terminal":
            return {
                "type": "OBJECT",
                "properties": {
                    "command": {"type": "STRING", "description": "Command terminal yang akan dijalankan (misal: 'pip install requests', 'git status')"}
                },
                "required": ["command"]
            }
        elif func_name == "search_files":
            return {
                "type": "OBJECT",
                "properties": {
                    "pattern": {"type": "STRING", "description": "Glob pattern untuk file (misal: '**/*.py')"},
                    "query": {"type": "STRING", "description": "Text yang dicari di dalam file"}
                },
                "required": ["pattern", "query"]
            }
        elif func_name == "web_search":
            return {
                "type": "OBJECT",
                "properties": {
                    "query": {"type": "STRING", "description": "Kata kunci pencarian"}
                },
                "required": ["query"]
            }
        return {"type": "OBJECT", "properties": {}}

    def execute(self, tool_name, args):
        """Eksekusi tool (Local atau MCP) dengan Safe Mode Check"""
        import gemini_core.config as config
        
        # Daftar tool sensitif yang butuh konfirmasi
        SENSITIVE_TOOLS = ['run_terminal', 'write_file']
        
        # Cek Safe Mode
        if config.SAFE_MODE and tool_name in SENSITIVE_TOOLS:
            print(f"\n⚠️  [SAFE MODE] Gemini wants to execute: {tool_name}")
            print(f"   Args: {json.dumps(args, indent=2)}")
            user_confirm = input("   Allow this action? (y/n): ").strip().lower()
            if user_confirm != 'y':
                return "Error: User denied execution."

        # 1. Cek Local Tools
        if tool_name in self.tools:
            try:
                logger.info(f"Executing Local Tool: {tool_name}")
                return self.tools[tool_name](**args)
            except Exception as e:
                return f"Error executing {tool_name}: {str(e)}"
        
        # 2. Cek MCP Tools
        for client in self.mcp_clients:
            if client.is_connected:
                # Cek apakah tool ini milik client ini
                for tool in client.tools:
                    if tool["name"] == tool_name:
                        # MCP Tools dianggap sensitif secara default di Safe Mode?
                        # Untuk sekarang kita anggap aman kecuali kita punya list spesifik
                        # Atau kita bisa tanya user untuk SEMUA MCP tool jika paranoid
                        if config.SAFE_MODE:
                             print(f"\n⚠️  [SAFE MODE] Gemini wants to execute MCP Tool: {tool_name}")
                             print(f"   Args: {json.dumps(args, indent=2)}")
                             user_confirm = input("   Allow this action? (y/n): ").strip().lower()
                             if user_confirm != 'y':
                                 return "Error: User denied execution."

                        logger.info(f"Executing MCP Tool: {tool_name}")
                        result = client.call_tool(tool_name, args)
                        # MCP return dict {content: [...], isError: bool}
                        if result and "content" in result:
                            # Ambil text content pertama
                            for item in result["content"]:
                                if item["type"] == "text":
                                    return item["text"]
                        return str(result)
                        
        return f"Error: Tool '{tool_name}' not found."

# --- Implementasi Tools ---

registry = ToolRegistry()

@registry.register
def read_file(filepath):
    """Membaca isi file text."""
    try:
        if not os.path.exists(filepath):
            return f"Error: File '{filepath}' not found."
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"

@registry.register
def write_file(filepath, content):
    """Menulis content ke file (overwrite)."""
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"Successfully wrote to '{filepath}'"
    except Exception as e:
        return f"Error writing file: {e}"

@registry.register
def list_directory(path="."):
    """List isi directory."""
    try:
        if not os.path.exists(path):
            return f"Error: Path '{path}' not found."
        items = os.listdir(path)
        result = []
        for item in items:
            full_path = os.path.join(path, item)
            type_str = "DIR" if os.path.isdir(full_path) else "FILE"
            result.append(f"[{type_str}] {item}")
        return "\n".join(result)
    except Exception as e:
        return f"Error listing directory: {e}"

@registry.register
def run_terminal(command):
    """Menjalankan command terminal/shell dan mengembalikan outputnya."""
    try:
        # PENTING: Shell=True berbahaya jika input tidak divalidasi.
        # Untuk tool pribadi ini oke, tapi hati-hati.
        result = subprocess.run(
            command, 
            shell=True, 
            capture_output=True, 
            text=True, 
            timeout=60
        )
        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"
        return output if output.strip() else "(No output)"
    except subprocess.TimeoutExpired:
        return "Error: Command timed out (60s limit)"
    except Exception as e:
        return f"Error running command: {e}"

@registry.register
def search_files(pattern, query):
    """Mencari text di dalam file-file yang cocok dengan pattern."""
    try:
        matches = []
        files = glob.glob(pattern, recursive=True)
        for filepath in files:
            if os.path.isfile(filepath):
                try:
                    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if query in content:
                            matches.append(filepath)
                except:
                    pass
        if not matches:
            return "No matches found."
        return "Found in files:\n" + "\n".join(matches)
    except Exception as e:
        return f"Error searching files: {e}"

@registry.register
def web_search(query):
    """
    Melakukan pencarian di internet (Web Search) untuk mendapatkan informasi terkini.
    Gunakan ini jika user bertanya tentang berita terbaru, dokumentasi library, atau hal yang tidak ada di knowledge base.
    """
    try:
        try:
            from duckduckgo_search import DDGS
        except ImportError:
            from ddgs import DDGS
        
        import warnings
        # Suppress specific RuntimeWarning from duckduckgo_search by message
        warnings.filterwarnings("ignore", message=".*renamed to.*ddgs.*", category=RuntimeWarning)
        
        logger.info(f"Searching web for: {query}")
        # Use region='id-id' for better local results, safesearch='moderate'
        results = DDGS().text(query, region='id-id', safesearch='moderate', max_results=5)
        
        if not results:
            return "No results found."
            
        formatted_results = []
        for r in results:
            title = r.get('title', 'No Title')
            link = r.get('href', '#')
            body = r.get('body', '')
            formatted_results.append(f"Title: {title}\nLink: {link}\nSnippet: {body}\n")
            
        return "\n---\n".join(formatted_results)
    except ImportError:
        return "Error: Library 'ddgs' (or 'duckduckgo-search') not installed. Please install it to use this tool."
    except Exception as e:
        return f"Error performing web search: {e}"
