"""
elina.memory — Secure, persistent memory for Elina OS (Termux/Android/Linux)

Usage:
    from elina.memory import store, recall, verify_integrity, get_user_key

    # Store a memory
    store("I completed my first marathon", valence=0.9, arousal=0.7)

    # Recall with trigger
    memories = recall("marathon")
    if memories:
        for fact, valence, arousal in memories:
            print(f"Recalled: {fact} (joy={valence}, energy={arousal})")
"""

import os
import json
import hashlib
import hmac
import socket
from datetime import datetime, timezone
from typing import Optional, Tuple, List

# ==========================
# 🛠 CONFIGURATION
# ==========================
HOME = os.path.expanduser("~")
CONFIG_DIR = os.path.join(HOME, ".config", "elina")
os.makedirs(CONFIG_DIR, exist_ok=True)

KEY_PATH = os.path.join(CONFIG_DIR, "user_demo.key")
MEMORY_PATH = os.path.join(CONFIG_DIR, "memory.dat")


# ==========================
# 🔐 KEY MANAGEMENT
# ==========================
def get_user_key() -> bytes:
    """Get persistent user key (256-bit HMAC key)."""
    if not os.path.exists(KEY_PATH):
        try:
            user = socket.getuser()
            host = socket.gethostname()
        except Exception:
            user = "demo"
            host = "termux"
        key_data = f"user_{user}@{host}_elina".encode("utf-8")
        key = hashlib.sha256(key_data).digest()
        with open(KEY_PATH, "wb") as f:
            f.write(key)
        os.chmod(KEY_PATH, 0o600)
    with open(KEY_PATH, "rb") as f:
        return f.read()


# ==========================
# 🧠 MEMORY OPERATIONS
# ==========================
def store(fact: str, valence: float = 0.0, arousal: float = 0.0):
    """Store a memory fact with valence (-1.0 to 1.0) and arousal (0.0 to 1.0)."""
    key = get_user_key()
    data = json.dumps({
        "fact": fact,
        "valence": valence,
        "arousal": arousal,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }).encode("utf-8")
    
    # Save with HMAC integrity (no encryption needed for local storage)
    hmac_sig = hmac.new(key, data, hashlib.sha256).digest()
    data_to_save = hmac_sig + data

    with open(MEMORY_PATH, "wb") as f:
        f.write(data_to_save)


def recall(trigger: str, max_results: int = 10) -> Optional[List[Tuple[str, float, float]]]:
    """Recall all memories matching trigger. Returns list of (fact, valence, arousal)."""
    if not os.path.exists(MEMORY_PATH):
        return []

    key = get_user_key()
    with open(MEMORY_PATH, "rb") as f:
        raw = f.read()

    # Verify integrity
    if len(raw) < 32:
        return []
    received_hmac = raw[:32]
    payload = raw[32:]
    expected_hmac = hmac.new(key, payload, hashlib.sha256).digest()
    if not hmac.compare_digest(received_hmac, expected_hmac):
        return []  # Tampered — return empty

    # Parse JSON
    try:
        memories = json.loads(payload.decode("utf-8"))
        # Support both single memory (dict) and list of memories
        if isinstance(memories, dict):
            memories = [memories]
        
        # Filter by trigger (case-insensitive substring match)
        results = []
        for m in memories:
            if trigger.lower() in m.get("fact", "").lower():
                results.append((m["fact"], m.get("valence", 0.0), m.get("arousal", 0.0)))
        
        return results[:max_results]  # Limit to max_results
    except Exception:
        return []


def verify_integrity() -> bool:
    """Verify memory integrity (returns True if valid, False if tampered)."""
    if not os.path.exists(MEMORY_PATH):
        return True  # No memory = no tampering
    key = get_user_key()
    with open(MEMORY_PATH, "rb") as f:
        raw = f.read()
    if len(raw) < 32:
        return False
    received_hmac = raw[:32]
    payload = raw[32:]
    expected_hmac = hmac.new(key, payload, hashlib.sha256).digest()
    return hmac.compare_digest(received_hmac, expected_hmac)


# ==========================
# 🚀 CLI ENTRYPOINT
# ==========================
def _cli():
    """CLI for `memory_loop` command."""
    if len(sys.argv) < 2 or sys.argv[1] in ["--help", "-h"]:
        print("Usage: memory_loop [--init] [--recall <trigger>] [--store <fact>] [--verify]")
        print("\nCommands:")
        print("  --init         Initialize memory store (overwrites existing)")
        print("  --recall <word> Recall memories containing <word>")
        print("  --store <fact> Store a new memory fact")
        print("  --verify       Verify memory integrity")
        sys.exit(0)

    if sys.argv[1] == "--init":
        store("Elina memory initialized on " + datetime.now(timezone.utc).isoformat(),
              valence=0.5, arousal=0.2)
        print("[INFO] Memory initialized.")

    elif sys.argv[1] == "--recall":
        if len(sys.argv) < 3:
            print("Error: --recall requires a trigger word (e.g., --recall mountain)")
            sys.exit(1)
        memories = recall(sys.argv[2])
        if memories:
            print("\n--- Recall Results ---")
            for fact, valence, arousal in memories:
                print(f"• {fact} (joy={valence:.2f}, energy={arousal:.2f})")
        else:
            print(f"No memory found matching '{sys.argv[2]}'")

    elif sys.argv[1] == "--store":
        if len(sys.argv) < 3:
            print("Error: --store requires a fact (e.g., --store 'I love hiking')")
            sys.exit(1)
        fact = " ".join(sys.argv[2:])
        store(fact)
        print(f"[INFO] Storing: '{fact}'")

    elif sys.argv[1] == "--verify":
        if verify_integrity():
            print("[OK] Memory integrity verified.")
        else:
            print("[ERROR] Memory integrity check failed! Data may be corrupted.")
            sys.exit(1)

    else:
        print(f"Unknown command: {sys.argv[1]}")
        print("Run 'memory_loop --help' for usage.")
        sys.exit(1)


# ==========================
# 🚀 MAIN ENTRY POINT
# ==========================
if __name__ == "__main__":
    import sys
    _cli()
