import os
import subprocess
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[3]

# Runs in a fresh interpreter, so Django configures logging from settings exactly as gunicorn does,
# outside pytest's own log capture.
LOG_A_REQUEST_ERROR = """
import django, logging
django.setup()
try:
    raise RuntimeError("boom")
except RuntimeError:
    logging.getLogger("django.request").exception("Internal Server Error: /api/v1/x")
"""


def test_request_errors_reach_stderr_with_traceback_when_debug_is_off() -> None:
    env = {**os.environ, "DJANGO_DEBUG": "false", "DJANGO_SETTINGS_MODULE": "config.settings"}

    result = subprocess.run(  # noqa: S603 - fixed argv, no external input
        [sys.executable, "-c", LOG_A_REQUEST_ERROR],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )

    assert "ERROR django.request: Internal Server Error: /api/v1/x" in result.stderr
    assert "RuntimeError: boom" in result.stderr
