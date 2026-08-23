#!/usr/bin/env python3
"""Wake ChatGPT Executive (Plus account) via BrowserOS neo CDP :9110.

Thin wrapper over wake_division01.py with Executive defaults.
Usage identical: wake_executive.py "briefing" | --new | --list
"""
import sys
sys.argv.insert(1, "--port")
sys.argv.insert(2, "9110")
sys.argv.insert(3, "--home")
import os
sys.argv.insert(4, os.path.expanduser("~/.codex-EXECUTIVE"))

import wake_division01

wake_division01.DEBUG_PORT = 9110
from pathlib import Path
wake_division01.CODE_HOME = Path.home() / ".codex-EXECUTIVE"
wake_division01.WAKE_JSON = wake_division01.CODE_HOME / "wake.json"

if __name__ == "__main__":
    wake_division01.main()
