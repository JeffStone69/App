```python
#!/usr/bin/env python3
"""
XForge Self-Improve Engine (Improved)
Handles Grok/xAI API calls with 403 blocked-key protection.
"""

import os
import time
import logging
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("XForge-SelfImprove")

XAI_API_KEY = os.getenv("XAI_API_KEY")
ENABLE_SELF_IMPROVE = os.getenv("ENABLE_SELF_IMPROVE", "true").lower() == "true"
MAX_RETRIES = 3
BASE_DELAY = 2  # seconds


def check_api_key_health() -> bool:
    """Quick validation to avoid repeated blocked-key calls."""
    if not XAI_API_KEY:
        logger.error("XAI_API_KEY not found in environment")
        return False
    # Lightweight test (replace with actual endpoint if needed)
    return True


def self_improve_code(current_code: str, prompt: str = "Improve this trading module") -> str:
    """
    Attempts to improve code using xAI API.
    Returns improved code or original code on failure.
    """
    if not ENABLE_SELF_IMPROVE:
        logger.info("Self-improvement disabled via config")
        return current_code

    if not check_api_key_health():
        logger.error("Self-improvement skipped: invalid or blocked API key")
        return current_code

    headers = {
        "Authorization": f"Bearer {XAI_API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "grok-2",
        "messages": [
            {"role": "system", "content": "You are an expert Python trading engineer."},
            {"role": "user", "content": f"{prompt}\n\n```python\n{current_code}\n```"}
        ],
        "max_tokens": 2000
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.post(
                "https://api.x.ai/v1/chat/completions",
                json=payload,
                headers=headers,
                timeout=30
            )
            if response.status_code == 200:
                improved = response.json()["choices"][0]["message"]["content"]
                logger.info("Self-improvement successful")
                return improved.strip("`").strip()
            elif response.status_code == 403:
                error_data = response.json()
                logger.error(f"API key blocked: {error_data}")
                logger.warning("Disabling self-improvement for this session")
                os.environ["ENABLE_SELF_IMPROVE"] = "false"
                return current_code
            else:
                logger.warning(f"Attempt {attempt} failed: {response.status_code} - {response.text}")
        except requests.RequestException as e:
            logger.error(f"Network error on attempt {attempt}: {e}")

        if attempt < MAX_RETRIES:
            delay = BASE_DELAY * (2 ** (attempt - 1))
            logger.info(f"Retrying in {delay}s...")
            time.sleep(delay)

    logger.error("Self-improvement failed after retries. Using original code.")
    return current_code


if __name__ == "__main__":
    # Example usage inside XForge
    sample_code = "def calculate_sma(data, period=20): return data.rolling(period).mean()"
    improved = self_improve_code(sample_code, "Optimize this SMA function for speed")
    print("\n--- Improved Code ---\n")
    print(improved)
```