import os
import re
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONTEND = ROOT / "frontend"
BACKEND_STATIC = Path(__file__).resolve().parents[1] / "static"


@pytest.fixture(scope="session", autouse=True)
def build_frontend_static() -> None:
    if not (FRONTEND / "package.json").exists():
        pytest.skip("frontend directory not found")

    # Building the frontend is the slow part of the backend suite. Allow
    # skipping it for fast backend-only iteration once a build already exists.
    if os.environ.get("SKIP_FRONTEND_BUILD") and (BACKEND_STATIC / "index.html").exists():
        return

    subprocess.run(["npm", "ci"], cwd=FRONTEND, check=True)
    subprocess.run(["npm", "run", "build"], cwd=FRONTEND, check=True)

    if BACKEND_STATIC.exists():
        shutil.rmtree(BACKEND_STATIC)
    shutil.copytree(FRONTEND / "out", BACKEND_STATIC)
