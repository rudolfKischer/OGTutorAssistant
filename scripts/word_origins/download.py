import subprocess
import time

from .settings import SETTINGS


def curl(url: str) -> bytes:
    for attempt in range(1, SETTINGS["retries"] + 1):
        result = subprocess.run(["curl", "-sSL", "-m", str(SETTINGS["timeout_seconds"] * 8), "-A", SETTINGS["user_agent"], url],
                                capture_output=True)
        if result.returncode == 0 and result.stdout:
            return result.stdout
        time.sleep(SETTINGS["retry_delay_seconds"] * attempt)
    raise RuntimeError(f"download failed: {url}")
