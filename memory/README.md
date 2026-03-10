# Elina OS Memory Store

Secure, persistent memory for your Elina OS session.

## 📁 Files
- `user_demo.key` — HMAC key (owner-only: `0600`)
- `memory.dat` — Memory store with integrity protection

## 🚀 Commands
- `memory_loop --store "..."` — Add a memory
- `memory_loop --recall "..."` — Search memories
- `memory_loop --init` — Reset memory store

## 🔒 Security
- All operations use HMAC-SHA256 for tamper detection
- Keys are derived from `user@host` — no personal data stored
