# Setup Prompts & Guides for macOS

This directory contains complete setup prompts and instructions for deploying the **Sovereign On-Prem Agentic AI Workbench** on macOS.

---

### Files Included

1. **[GEMINI_FLASH_MAC_SETUP_PROMPT.md](GEMINI_FLASH_MAC_SETUP_PROMPT.md)**:
   - **Primary Master Prompt for Gemini 3.7 Flash IDE**: Copy and paste directly into Gemini 3.7 Flash in your Mac IDE (VS Code, Cursor, Windsurf, Gemini Code Assist). It directs the agent to autonomously configure Docker Postgres, install dependencies, pull the 5 models, run migrations, seed ChromaDB, verify all test suites, and launch both dev servers.

2. **[ANTIGRAVITY_MAC_SETUP_PROMPT.md](ANTIGRAVITY_MAC_SETUP_PROMPT.md)**:
   - Setup prompt formatted for Antigravity instances.

3. **[MAC_MANUAL_SETUP_GUIDE.md](MAC_MANUAL_SETUP_GUIDE.md)**:
   - Comprehensive step-by-step developer cheat sheet with exact terminal commands, Docker port configurations, and macOS-specific troubleshooting notes.

4. **[QUICK_START_MAC.sh](QUICK_START_MAC.sh)**:
   - Automated one-click bash setup script. Run `chmod +x prompts/QUICK_START_MAC.sh && ./prompts/QUICK_START_MAC.sh` to initialize Docker, Python virtual environment, Ollama models, migrations, ChromaDB SOP vectors, and frontend packages.
