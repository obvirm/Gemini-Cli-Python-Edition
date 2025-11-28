#!/usr/bin/env python3
"""
GEMINI CLI (PYTHON VERSION)
Interactive Chat dengan Agentic Capabilities.
"""
import os
import sys
import logging
from gemini_core.client import GeminiClient
from gemini_core.chat import ChatSession
from gemini_core.chat import ChatSession
from gemini_core.config import DEFAULT_CREDENTIALS_FILE
try:
    import questionary
    from rich.console import Console
    from rich.panel import Panel
    from rich.text import Text
    from rich.live import Live
    from rich import box
    import msvcrt # Windows only
except ImportError:
    print("Error: Missing dependencies (questionary, rich).")
    print("Please run: pip install -r requirements.txt")
    sys.exit(1)

# Configure logging to file only, to keep CLI clean
# Logging configured in main()

# ANSI Colors
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'

import threading
import time
import sys

class Spinner:
    def __init__(self, message="Thinking..."):
        self.message = message
        self.spinning = False
        self.thread = None

    def spin(self):
        chars = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
        i = 0
        while self.spinning:
            sys.stdout.write(f"\r{self.message} {chars[i % len(chars)]}")
            sys.stdout.flush()
            time.sleep(0.1)
            i += 1
        sys.stdout.write("\r" + " " * (len(self.message) + 5) + "\r")
        sys.stdout.flush()

    def start(self):
        if not self.spinning:
            self.spinning = True
            self.thread = threading.Thread(target=self.spin, daemon=True)
            self.thread.start()

    def stop(self):
        if self.spinning:
            self.spinning = False
            if self.thread:
                self.thread.join()

# Helper for Boxed Menu
def show_boxed_menu(title, subtitle, options):
    current_idx = 0
    
    def generate_panel(idx):
        menu_text = Text()
        
        # Title with Green '?'
        if title.startswith("?"):
            menu_text.append("? ", style="bold green")
            menu_text.append(title[1:].strip() + "\n\n", style="bold white")
        else:
            menu_text.append(f"{title}\n\n", style="bold white")
            
        if subtitle:
            menu_text.append(f"{subtitle}\n\n", style="white")
        
        for i, option in enumerate(options):
            if i == idx:
                menu_text.append(f"❯ {option}\n", style="bold cyan") # Cyan for selection
            else:
                menu_text.append(f"  {option}\n", style="white")
        
        menu_text.append("\n(Use Enter to select)\n\n", style="dim white")
        menu_text.append("Terms of Services and Privacy Notice for Gemini CLI\n", style="white")
        menu_text.append("https://github.com/google-gemini/gemini-cli/blob/main/docs/tos-privacy.md", style="blue underline")

        return Panel(
            menu_text,
            border_style="blue",
            box=box.ROUNDED,
            expand=False,
            padding=(1, 2)
        )

    # Use Live to render inline without clearing screen
    with Live(generate_panel(current_idx), auto_refresh=False, transient=True) as live:
        # Flush buffer to prevent accidental selection from previous Enter
        while msvcrt.kbhit():
            msvcrt.getch()
            
        while True:
            live.update(generate_panel(current_idx), refresh=True)
            
            # Input Handling
            try:
                key = msvcrt.getch()
                if key == b'\xe0': # Arrow key prefix
                    key = msvcrt.getch()
                    if key == b'H': # Up
                        current_idx = (current_idx - 1) % len(options)
                    elif key == b'P': # Down
                        current_idx = (current_idx + 1) % len(options)
                elif key == b'\r': # Enter
                    return current_idx
                elif key == b'\x03': # Ctrl+C
                    raise KeyboardInterrupt
                elif key in [str(i+1).encode() for i in range(len(options))]:
                     current_idx = int(key) - 1
            except KeyboardInterrupt:
                raise

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Gemini CLI (Python Edition)")
    parser.add_argument('--debug', action='store_true', help="Enable debug logging")
    parser.add_argument('--mode', choices=['oauth', 'apikey', 'vertex'], default='oauth', help="Authentication mode")
    parser.add_argument('--key', help="API Key (for apikey mode)")
    parser.add_argument('--project', help="Google Cloud Project ID (for vertex mode)")
    parser.add_argument('--location', default='us-central1', help="Google Cloud Location (for vertex mode)")
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.DEBUG if args.debug else logging.INFO
    handlers = [logging.FileHandler('gemini_cli.log')]
    if args.debug:
        handlers.append(logging.StreamHandler())
        
    logging.basicConfig(
        level=log_level, 
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=handlers,
        force=True
    )
    
    os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    
    print(f"{Colors.HEADER}{Colors.BOLD}")
    print("="*60)
    print("   GEMINI CLI (PYTHON EDITION)")
    if args.debug:
        print(f"   {Colors.WARNING}[DEBUG MODE ON]{Colors.HEADER}")
    print("="*60)
    print(f"{Colors.ENDC}")
    
    # 0. Interactive Setup (First Run / No Args)
    if args.mode == 'oauth' and not args.key and not args.project and not os.path.exists(DEFAULT_CREDENTIALS_FILE):
        try:
            idx = show_boxed_menu(
                "? Get started",
                "How would you like to authenticate for this project?",
                ["1. Login with Google", "2. Use Gemini API Key", "3. Vertex AI"]
            )
            
            if idx == 0: # Login
                args.mode = 'oauth'
            elif idx == 1: # API Key
                args.mode = 'apikey'
                args.key = input("Enter Gemini API Key: ").strip()
            elif idx == 2: # Vertex
                args.mode = 'vertex'
                args.project = input("Enter Google Cloud Project ID: ").strip()
                args.location = input("Enter Location (default: us-central1): ").strip() or 'us-central1'
                
        except KeyboardInterrupt:
            print("\nGoodbye!")
            sys.exit(0)

    # 1. Init Client
    print(f"{Colors.CYAN}Initializing client ({args.mode})...{Colors.ENDC}")
    try:
        client = GeminiClient(
            DEFAULT_CREDENTIALS_FILE,
            auth_mode=args.mode,
            api_key=args.key,
            vertex_project=args.project,
            vertex_location=args.location
        )
        # Pre-warm connection (setup user)
        client.setup_user()
        
        project_info = client.project_id if client.project_id else (args.project if args.mode == 'vertex' else 'N/A')
        if args.debug:
            print(f"{Colors.GREEN}Connected! Project: {project_info}{Colors.ENDC}")
        else:
            print(f"{Colors.GREEN}Connected!{Colors.ENDC}")
    except Exception as e:
        print(f"{Colors.FAIL}Failed to connect: {e}{Colors.ENDC}")
        print("Try running with --relogin if token is expired.")
        return

    # 2. Init Chat Session
    model = 'gemini-3-pro-preview'
    chat = ChatSession(client, model=model)
    pending_media = [] # Store media (images/video) to be sent with next message
    
    print(f"\nType '/exit' to quit, '/clear' to reset context.")
    print(f"Using model: {Colors.BOLD}{model}{Colors.ENDC}\n")

    # 3. Chat Loop
    last_interrupt_time = 0
    while True:
        try:
            user_input = input(f"{Colors.BLUE}You > {Colors.ENDC}").strip()
            
            if not user_input:
                continue
                
            if user_input.lower() in ['/exit', '/quit']:
                print("Goodbye!")
                break
                
            if user_input.lower() == '/clear':
                chat = ChatSession(client, model=model)
                pending_media = []
                print(f"{Colors.WARNING}Context cleared.{Colors.ENDC}")
                continue

            # --- COMMANDS ---
            
            if user_input.lower().startswith('/image '):
                # ... (kode image tetap sama) ...
                try:
                    filepath = user_input.split(' ', 1)[1].strip()
                    if os.path.exists(filepath):
                        import base64
                        with open(filepath, "rb") as image_file:
                            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                            pending_media.append({
                                'mime_type': 'image/jpeg', 
                                'data': encoded_string
                            })
                            print(f"{Colors.GREEN}Image attached! It will be sent with your next message.{Colors.ENDC}")
                    else:
                        print(f"{Colors.FAIL}File not found: {filepath}{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error reading image: {e}{Colors.ENDC}")
                continue

            if user_input.lower().startswith('/video '):
                # ... (kode video tetap sama) ...
                try:
                    filepath = user_input.split(' ', 1)[1].strip()
                    if os.path.exists(filepath):
                        file_size_mb = os.path.getsize(filepath) / (1024 * 1024)
                        if file_size_mb > 20:
                            print(f"{Colors.WARNING}Warning: Video size is {file_size_mb:.1f}MB. Large files might fail or timeout.{Colors.ENDC}")
                        
                        import base64
                        import mimetypes
                        mime_type, _ = mimetypes.guess_type(filepath)
                        if not mime_type or not mime_type.startswith('video'):
                            mime_type = 'video/mp4' 
                            
                        with open(filepath, "rb") as video_file:
                            encoded_string = base64.b64encode(video_file.read()).decode('utf-8')
                            pending_media.append({
                                'mime_type': mime_type,
                                'data': encoded_string
                            })
                            print(f"{Colors.GREEN}Video attached ({mime_type})! It will be sent with your next message.{Colors.ENDC}")
                    else:
                        print(f"{Colors.FAIL}File not found: {filepath}{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error reading video: {e}{Colors.ENDC}")
                continue

            if user_input.lower().startswith('/model '):
                # ... (kode model tetap sama) ...
                try:
                    new_model = user_input.split(' ')[1]
                    chat.model = new_model
                    print(f"{Colors.WARNING}Switched to model: {new_model}{Colors.ENDC}")
                except IndexError:
                    print(f"{Colors.FAIL}Usage: /model <model_name>{Colors.ENDC}")
                continue

            if user_input.lower().startswith('/mcp '):
                # ... (kode mcp tetap sama) ...
                parts = user_input.split(' ')
                if len(parts) >= 3 and parts[1] == 'connect':
                    cmd = parts[2]
                    args = parts[3:]
                    print(f"{Colors.CYAN}Connecting to MCP Server: {cmd} {args}...{Colors.ENDC}")
                    from gemini_core.mcp import MCPClient
                    from gemini_core.tools import registry
                    mcp_client = MCPClient(cmd, args)
                    if mcp_client.connect():
                        registry.register_mcp(mcp_client)
                        print(f"{Colors.GREEN}Successfully connected! Discovered tools:{Colors.ENDC}")
                        for tool in mcp_client.tools:
                            print(f"  - {tool['name']}: {tool.get('description', '')[:50]}...")
                    else:
                        print(f"{Colors.FAIL}Failed to connect to MCP Server.{Colors.ENDC}")
                else:
                    print("Usage: /mcp connect <command> [args...]")
                continue

            if user_input.lower().startswith('/persona '):
                # ... (kode persona tetap sama) ...
                try:
                    persona_name = user_input.split(' ')[1]
                    from gemini_core.personas import get_persona
                    new_instruction = get_persona(persona_name)
                    chat.system_instruction = new_instruction
                    chat.history = [] 
                    print(f"{Colors.WARNING}Switched to persona: {persona_name}{Colors.ENDC}")
                    print(f"{Colors.CYAN}Context cleared to apply new persona.{Colors.ENDC}")
                except IndexError:
                    print(f"{Colors.FAIL}Usage: /persona <name>{Colors.ENDC}")
                continue

            if user_input.lower().startswith('/load '):
                # ... (kode load tetap sama) ...
                try:
                    filepath = user_input.split(' ', 1)[1].strip()
                    if os.path.exists(filepath):
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        context_msg = f"Context loaded from file '{filepath}':\n\n```\n{content}\n```\n\nPlease use this context for future questions."
                        chat.history.append({"role": "user", "parts": [{"text": context_msg}]})
                        chat.history.append({"role": "model", "parts": [{"text": f"Understood. I have loaded the context from '{filepath}'."}]})
                        print(f"{Colors.GREEN}Successfully loaded '{filepath}' ({len(content)} chars) into context.{Colors.ENDC}")
                    else:
                        print(f"{Colors.FAIL}File not found: {filepath}{Colors.ENDC}")
                except Exception as e:
                    print(f"{Colors.FAIL}Error reading file: {e}{Colors.ENDC}")
                continue

            if user_input.lower() == '/safe':
                import gemini_core.config as config
                config.SAFE_MODE = not config.SAFE_MODE
                status = "ON" if config.SAFE_MODE else "OFF"
                color = Colors.GREEN if config.SAFE_MODE else Colors.FAIL
                print(f"{Colors.WARNING}Safe Mode is now: {color}{status}{Colors.ENDC}")
                continue

            if user_input.lower().startswith('/auth'):
                # Auto-Logout / Clean Slate
                subtitle_extra = ""
                if os.path.exists(DEFAULT_CREDENTIALS_FILE):
                    try:
                        os.remove(DEFAULT_CREDENTIALS_FILE)
                        subtitle_extra = " (Session cleared)"
                    except Exception as e:
                        print(f"{Colors.FAIL}Failed to clear session: {e}{Colors.ENDC}")
                
                # Interactive Menu
                try:
                    # Small delay to ensure input buffer is ready for flushing
                    time.sleep(0.2)
                    
                    idx = show_boxed_menu(
                        "? Authentication",
                        f"How would you like to authenticate?{subtitle_extra}",
                        ["1. Login with Google", "2. Use Gemini API Key", "3. Vertex AI"]
                    )
                    
                    new_mode = None
                    new_key = None
                    new_project = None
                    new_location = 'us-central1'
                    
                    if idx == 0: # Login
                        new_mode = 'oauth'
                    elif idx == 1: # API Key
                        new_mode = 'apikey'
                        new_key = input("Enter Gemini API Key: ").strip()
                    elif idx == 2: # Vertex
                        new_mode = 'vertex'
                        new_project = input("Enter Google Cloud Project ID: ").strip()
                        new_location = input("Enter Location (default: us-central1): ").strip() or 'us-central1'
                    
                    # Re-initialize Client
                    print(f"{Colors.CYAN}Re-initializing client ({new_mode})...{Colors.ENDC}")
                    client = GeminiClient(
                        DEFAULT_CREDENTIALS_FILE,
                        auth_mode=new_mode,
                        api_key=new_key,
                        vertex_project=new_project,
                        vertex_location=new_location
                    )
                    
                    # Force login if oauth
                    if new_mode == 'oauth':
                         client.auth.authenticate(force_login=True)
                         
                    client.setup_user()
                    
                    # Update Chat Session
                    chat = ChatSession(client, model=model)
                    
                    # Update Args (for debug/status)
                    args.mode = new_mode
                    args.key = new_key
                    args.project = new_project
                    args.location = new_location

                    project_info = client.project_id if client.project_id else (args.project if args.mode == 'vertex' else 'N/A')
                    if args.debug:
                        print(f"{Colors.GREEN}Authentication successful! Project: {project_info}{Colors.ENDC}")
                    else:
                        print(f"{Colors.GREEN}Authentication successful!{Colors.ENDC}")
                        
                except KeyboardInterrupt:
                    # Re-raise to trigger main loop's interactive exit prompt
                    raise
                except Exception as e:
                    print(f"{Colors.FAIL}Authentication failed: {e}{Colors.ENDC}")
                
                continue

            # --- CHAT & STREAMING ---

            # print(f"{Colors.GREEN}Gemini > {Colors.ENDC}", end='', flush=True) # Dipindah ke on_stream
            
            spinner = Spinner(f"{Colors.CYAN}Thinking...{Colors.ENDC}")
            spinner.start()
            
            first_token_received = False
            
            def on_stream(text):
                nonlocal first_token_received
                
                # Handle Tool Execution Logs
                if text.startswith('[Running tool:'):
                    spinner.stop() # Clear spinner line
                    tool_info = text.replace('[Running tool:', '').strip(']')
                    print(f"\n{Colors.WARNING}⠹ Proceeding with Execution: {tool_info}{Colors.ENDC}")
                    # Restart spinner with new status
                    spinner.message = f"{Colors.CYAN}Executing tool...{Colors.ENDC}"
                    spinner.start()
                    return

                # Handle Tool Results
                if text.startswith('[Result:'):
                    spinner.stop() # Clear spinner line
                    print(f"{Colors.CYAN}{text}{Colors.ENDC}")
                    # Restart spinner with new status
                    spinner.message = f"{Colors.CYAN}Analyzing result...{Colors.ENDC}"
                    spinner.start()
                    return

                # Handle Actual Content
                spinner.stop() # Stop spinner permanently for content
                
                if not first_token_received:
                    print(f"{Colors.GREEN}Gemini > {Colors.ENDC}", end='', flush=True)
                    first_token_received = True
                
                # Strip markdown bolding (**) as requested
                clean_text = text.replace('**', '')
                print(clean_text, end='', flush=True)
            
            try:
                response = chat.send_message(user_input, media_items=pending_media, stream_callback=on_stream)
            except KeyboardInterrupt:
                print(f"\n{Colors.WARNING}Generation cancelled by user.{Colors.ENDC}")
            finally:
                spinner.stop() # Ensure stopped if no stream or interrupted
                if not first_token_received:
                     print(f"{Colors.GREEN}Gemini > {Colors.ENDC}", end='', flush=True)
            
            if pending_media:
                pending_media = []
            
            print()
            
        except KeyboardInterrupt:
            current_time = time.time()
            if current_time - last_interrupt_time < 2.0:
                print("\nGoodbye!")
                break
            else:
                try:
                    # Transient warning
                    # \033[?25l = Hide Cursor
                    msg = f"\n{Colors.WARNING}Press Ctrl+C again to exit.{Colors.ENDC}"
                    print(f"\033[?25l{msg}", end="", flush=True)
                    time.sleep(1.5)
                    
                    # Clean up: Clear warning line AND the blank line
                    # \033[2K = Clear entire line
                    # \033[A  = Move cursor up
                    # \033[?25h = Show Cursor
                    print(f"\r\033[2K\033[A\033[2K\033[?25h", end="", flush=True)
                    
                except KeyboardInterrupt:
                    # If Ctrl+C pressed during wait, exit immediately
                    print("\nGoodbye!")
                    break
        except Exception as e:
            print(f"\n{Colors.FAIL}Error: {e}{Colors.ENDC}")

if __name__ == "__main__":
    main()
