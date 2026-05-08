#!/usr/bin/env python3
"""WeChat QR Login script for Hermes Agent."""
import asyncio
import json
import os
import sys

# Add hermes-agent to path
sys.path.insert(0, os.path.expanduser("~/.hermes/hermes-agent"))

from gateway.platforms.weixin import qr_login
from hermes_constants import get_hermes_home


async def main():
    hermes_home = get_hermes_home()
    print(f"Hermes home: {hermes_home}")
    print("Starting WeChat QR login...\n")

    result = await qr_login(hermes_home)

    if result:
        account_id = result.get("account_id", "")
        token = result.get("token", "")

        print(f"\n\n=== Login Successful ===")
        print(f"Account ID: {account_id}")
        print(f"Token: {token}")

        # Save to .env
        env_path = os.path.join(hermes_home, ".env")
        env_content = ""
        if os.path.exists(env_path):
            with open(env_path) as f:
                env_content = f.read()

        # Remove existing WEIXIN entries
        lines = env_content.split("\n")
        lines = [l for l in lines if not l.startswith("WEIXIN_ACCOUNT_ID") and not l.startswith("WEIXIN_TOKEN")]

        # Append new entries
        lines.append(f"WEIXIN_ACCOUNT_ID={account_id}")
        lines.append(f"WEIXIN_TOKEN={token}")

        with open(env_path, "w") as f:
            f.write("\n".join(lines))

        print(f"\nCredentials saved to {env_path}")
    else:
        print("\n\nLogin failed or timed out.")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
