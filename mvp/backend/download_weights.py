"""Automated Model Weights Setup Utility.

Clones or downloads the trained multif0 Late/Deep weights (model3: exp3multif0.pkl)
from the official research repository (Cuesta et al., 2020) into the local environment.
"""

import os
import sys
import subprocess
import shutil

REPO_URL = "https://github.com/helenacuesta/multif0-estimation-polyvocals"
DEFAULT_TARGET_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "multif0-estimation-polyvocals")
)


def ensure_weights_available(target_dir: str = DEFAULT_TARGET_DIR) -> str:
    """Ensure exp3multif0.pkl weights exist in target directory."""
    weights_path = os.path.join(target_dir, "models", "exp3multif0.pkl")
    if os.path.isfile(weights_path) and os.path.getsize(weights_path) > 100_000:
        print(f"[OK] multif0 model weights found at: {weights_path}")
        return weights_path

    print(f"[*] multif0 weights missing at {weights_path}")
    print(f"[*] Cloning repository from {REPO_URL} (depth=1)...")

    if not os.path.exists(target_dir):
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", REPO_URL, target_dir],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            print(f"[OK] Cloned multif0 repository to {target_dir}")
        except Exception as e:
            print(f"[ERROR] Failed to git clone repository: {e}")
            print(f"Please clone {REPO_URL} manually into {target_dir}")
            sys.exit(1)

    if os.path.isfile(weights_path):
        print(f"[OK] Weights confirmed at {weights_path}")
        return weights_path
    else:
        print(f"[ERROR] Repository cloned but weights not found at {weights_path}")
        sys.exit(1)


if __name__ == "__main__":
    ensure_weights_available()
