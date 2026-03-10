#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
memory_loop.py — Secure, persistent memory for Elina OS
Supports: Linux, Termux (Android), macOS, Windows (WSL)

Usage:
    python memory_loop.py                    # Run demo (add demo_init entry)
    python memory_loop.py --store "..."      # Store a new memory
    python memory_loop.py --recall "..."     # Recall memories matching keyword
    python memory_loop.py --init             # Initialize fresh memory store
    python memory_loop.py --help             # Show help

Examples:
    python memory_loop.py --store "I hiked to Chimgan mountains yesterday"
    python memory_loop.py --recall "mountain"
"""

import os
import sys
import getpass
import hashlib
import hmac
import json
import socket
from datetime import datetime, timezone

# ==========================
# 🛠 CONFIGURATION & PATHS
# ==========================
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".config", "elina")
os.makedirs(CONFIG_DIR, exist_ok=True)

KEY_PATH = os.path.join(CONFIG_DIR, "user_demo.key")
MEMORY_PATH = os.path.join(CONFIG_DIR, "memory.dat")


# ==========================
# 🔐 KEY MANAGEMENT
# ==========================
def get_user_key():
    """Retrieve or generate a persistent user key."""
    if os.path.exists(KEY_PATH):
        try:
            with open(KEY_PATH, "rb") as f:
                key = f.read().strip()
                if key and len(key) > 0:
                    return key
        except IOError as e:
            print(f"[WARN] Failed to read key file: {e}. Regenerating...", file=sys.stderr)

    # Generate new key
    try:
        user = getpass.getuser()
        host = socket.gethostname()
    except Exception:
        user = "demo"
        host = "termux"

    key_data = f"user_{user}@{host}_demo_elina".encode("utf-8")
    key = hashlib.sha256(key_data).digest()

    # Save key
    try:
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        os.chmod(KEY_PATH, 0o600)
        print(f"[INFO] New key generated & saved to {KEY_PATH}")
    except IOError as e:
        print(f"[ERROR] Cannot write key file ({KEY_PATH}): {e}", file=sys.stderr)
        return key  # In-memory fallback

    return key


def verify_integrity(key, data: bytes) -> bool:
    """Verify HMAC-SHA256 integrity of data using the user key."""
    if len(data) < 32:
        return False

    received_hmac = data[:32]
    payload = data[32:]

    expected_hmac = hmac.new(key, payload, hashlib.sha256).digest()
    return hmac.compare_digest(received_hmac, expected_hmac)


# ==========================
# 🧠 MEMORY OPERATIONS
# ==========================
def load_memory(key):
    """Load memory from disk, verifying integrity."""
    if not os.path.exists(MEMORY_PATH):
        return {}

    try:
        with open(MEMORY_PATH, "rb") as f:
            raw = f.read()
        if verify_integrity(key, raw):
            payload = raw[32:]
            try:
                memory = json.loads(payload.decode("utf-8"))
                print(f"✅ Verified & loaded {len(memory)} memory entries")
                return memory
            except (UnicodeDecodeError, json.JSONDecodeError):
                print("⚠️  Memory file corrupted — resetting")
                return {}
        else:
            print("⚠️  Integrity check failed — resetting memory")
            return {}
    except Exception as e:
        print(f"[WARN] Failed to load memory: {e}. Starting fresh.")
        return {}


def save_memory(key, memory):
    """Save memory to disk with integrity protection."""
    payload = json.dumps(memory, indent=2).encode("utf-8")
    hmac_sig = hmac.new(key, payload, hashlib.sha256).digest()
    data_to_save = hmac_sig + payload

    try:
        with open(MEMORY_PATH, "wb") as f:
            f.write(data_to_save)
        print(f"✅ Saved {len(memory)} memory entries to {MEMORY_PATH}")
        return True
    except IOError as e:
        print(f"[ERROR] Failed to save memory: {e}", file=sys.stderr)
        return False


# ==========================
# 🚀 MAIN CLI LOGIC
# ==========================
def memory_loop():
    """Main memory loop with CLI support."""
    print("=== Elina OS Memory Loop (Demo) ===")
    print(f"Config dir: {CONFIG_DIR}")
    print(f"Key file:   {KEY_PATH}")

    # Get or generate key
    key = get_user_key()
    print(f"✅ Key loaded (length: {len(key)} bytes)")

    # Load existing memory
    memory = load_memory(key)

    # Parse CLI arguments
    if len(sys.argv) > 1:
        cmd = sys.argv[1]

        if cmd == "--store":
            if len(sys.argv) < 3:
                print("Error: --store requires a fact (e.g., --store 'I love hiking')")
                sys.exit(1)
            fact = " ".join(sys.argv[2:])
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": fact
            }
            memory[f"fact_{len(memory)}"] = entry
            print(f"[INFO] Storing: '{fact}'")
            save_memory(key, memory)

        elif cmd == "--recall":
            trigger = sys.argv[2] if len(sys.argv) > 2 else ""
            if not trigger:
                print("Error: --recall requires a trigger word (e.g., --recall mountain)")
                sys.exit(1)
            # Search all entries for trigger
            matches = []
            for k, v in memory.items():
                note = v.get("note", "")
                if trigger.lower() in note.lower():
                    matches.append((k, v))
            if matches:
                print("\n--- Recall Results ---")
                for k, v in matches:
                    print(f"• {v['note']}")
            else:
                print(f"No memory found matching '{trigger}'")

        elif cmd == "--init":
            memory = {}
            entry = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "note": "Memory store initialized"
            }
            memory["init"] = entry
            save_memory(key, memory)

        elif cmd in ["--help", "-h"]:
            print("Usage: python memory_loop.py [COMMAND] [ARGUMENTS]")
            print("\nCommands:")
            print("  --store <fact>    Store a new memory fact")
            print("  --recall <word>   Recall memories containing <word>")
            print("  --init            Initialize a fresh memory store")
            print("  --help, -h        Show this help message")
            sys.exit(0)

        else:
            print(f"[WARN] Unknown command: {cmd}. Running demo mode.")

    else:
        # Default: Add demo_init entry (only if no args)
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "note": "Memory loop initialized successfully on Termux/Linux/Android"
        }
        memory["demo_init"] = entry
        save_memory(key, memory)

    # Print summary (skip if in recall mode — results printed above)
    if "--recall" not in sys.argv:
        print("\n--- Memory Summary ---")
        if memory:
            for k, v in memory.items():
                print(f"• {k}: {v.get('note', '')}")
        else:
            print("No memories stored yet.")

    # Termux hint
    if "termux" in sys.platform.lower() or os.path.exists("/data/data/com.termux"):
        print("\n💡 Tip for Termux users:")
        print("   Run `termux-setup-storage` to grant storage permissions.")
        print("   Keys are saved to: ~/.config/elina/")


# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    try:
        memory_loop()
    except KeyboardInterrupt:
        print("\n[INFO] Interrupted by user.")
        sys.exit(0)
    except Exception as e:
        print(f"[ERROR] Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)
