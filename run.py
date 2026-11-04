import subprocess
import sys
from pathlib import Path

app_path = Path(__file__).resolve().parent / "app.py"
print(f"Launching SecureShield Pro from {app_path}...")
cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
cmd.extend(sys.argv[1:])
subprocess.run(cmd)
