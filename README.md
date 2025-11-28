# 🚀 Gemini CLI (Python Edition)

**Gemini CLI** is a next-generation terminal interface for Google's **Gemini 3 Pro** models. It goes beyond simple chat by offering full **Agentic Capabilities**—allowing the AI to read files, search the web, and execute terminal commands autonomously.

Designed for developers, it features a robust **Multi-Authentication System** (Google OAuth, API Key, or Vertex AI), **Multimodal Inputs** (Images & Video), and seamless integration with the **Model Context Protocol (MCP)**.

## ✨ Key Features

*   **🔐 Multi-Auth Support**: Flexible login via Google OAuth (Code Assist), Standard API Key, or Vertex AI.
*   **🤖 Agentic Workflow**: Autonomous tool use for File I/O, Web Search (DuckDuckGo), and System Commands.
*   **👁️ Multimodal**: Drag-and-drop support for Images (`.jpg`, `.png`) and Videos (`.mp4`).
*   **🔌 MCP Integration**: Connect to any MCP Server to extend capabilities infinitely.
*   **🛡️ Safe Mode**: Built-in sandbox with user-confirmation loops for sensitive actions.
*   **🎨 Rich UI**: Beautiful, interactive terminal interface with spinners, boxed menus, and syntax highlighting.

## 📦 Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/obvirm/Gemini-Cli-Python-Edition.git
    cd Gemini-Cli-Python-Edition
    ```

2.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
    *(Requires Python 3.8+)*

## 🚀 Usage

Run the main script:

```bash
python gemini_cli.py
```

On the first run, you'll be prompted to authenticate. You can choose between:
1.  **Login with Google** (OAuth - Recommended for Code Assist users)
2.  **Gemini API Key** (Standard API)
3.  **Vertex AI** (Google Cloud)

### 🎮 Commands

| Command | Description | Example |
| :--- | :--- | :--- |
| `/image <path>` | Attach an image to the next message | `/image ./cat.jpg` |
| `/video <path>` | Attach a video to the next message | `/video ./demo.mp4` |
| `/load <path>` | Load file content into chat context | `/load main.py` |
| `/auth` | Manage authentication / Logout | `/auth` |
| `/safe` | Toggle Safe Mode (ON/OFF) | `/safe` |
| `/persona <name>` | Switch AI Persona | `/persona pirate` |
| `/mcp connect ...`| Connect to MCP Server | `/mcp connect npx ...` |
| `/model <name>` | Switch Gemini Model | `/model gemini-2.0-flash` |
| `/clear` | Clear chat history | `/clear` |
| `/exit` | Exit application | `/exit` |

## 📂 Project Structure

*   `gemini_cli.py`: Main entry point and CLI loop.
*   `gemini_core/`:
    *   `client.py`: Core API communication logic.
    *   `chat.py`: Chat engine and tool execution loop.
    *   `tools.py`: Native tool implementations (File, Search, Terminal).
    *   `auth.py`: OAuth 2.0 authentication handler.
    *   `config.py`: Global configuration.
    *   `personas.py`: System instruction templates.

## ⚠️ Important Notes

*   **Video Size**: Recommended < 20MB (sent via Base64).
*   **Safe Mode**: ON by default. Disable with `/safe` for fully autonomous agentic behavior.
*   **Privacy**: Tokens are stored locally in `credentials.json`. Do not share this file.

---
*Happy Coding with Gemini!* 🤖
