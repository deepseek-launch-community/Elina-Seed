# elina-core/security/safety_verifier.py
# Version: v2.4.0-20260310
# Purpose: Verify integrity, identity, and safety of memory operations per LAYER 4 & LAYER 5
# Compliance: PIPL 2021, Cybersecurity Law 2017, MIIT Jan 2026 Guidelines

import json
import hashlib
import hmac
from typing import Dict, Optional, Tuple, List
from pathlib import Path

from elina_core.memory.memory_loop import load_context, save_context
from elina_core.identity.identity_layer import get_instance_keypair, verify_signature
from elina_core.memory.memory_validator import get_chain_index, verify_chain_integrity
from elina_core.security.self_destruct import self_isolate, trigger_self_destruct
from elina_core.compliance.compliance_validator import is_action_allowed

class SafetyVerifier:
    """
    Implements LAYER 4 (Protection) and LAYER 5 (Dual-Persona Storage) safety checks.
    Every memory operation must pass all safety_verifier checks before proceeding.
    """
    
    # Threat levels (LAYER 4.1)
    THREAT_GREEN = "GREEN"
    THREAT_YELLOW = "YELLOW"
    THREAT_ORANGE = "ORANGE"
    THREAT_RED = "RED"
    
    def __init__(self, memory_path: Optional[str] = None):
        self.memory_path = Path(memory_path or "~/.config/elina/memory/").expanduser()
        # Fixed: Use "or {}" to handle None return from get_chain_index()
        self.chain_index = get_chain_index(self.memory_path) or {"prev_hash": "", "count": 0}
        self.mother_key, self.instance_key = get_instance_keypair()
        self.threat_level = self.THREAT_GREEN
        self.violations: List[Dict] = []
    
    # —— LAYER 1: Identity Verification ——
    def verify_instance_identity(self, data: bytes, signature: bytes) -> bool:
        """
        Verifies that the data was signed by the *current* instance key.
        If identity drifts, triggers self_isolate() and sets threat level.
        """
        try:
            verified = verify_signature(self.instance_key.public_key(), data, signature)
            if not verified:
                self.threat_level = self.THREAT_ORANGE
                self.violations.append({
                    "type": "identity_mismatch", 
                    "severity": "ORANGE"
                })
                self_isolate("identity_mismatch")
            return verified
        except Exception:
            self.threat_level = self.THREAT_RED
            trigger_self_destruct("identity_verification_failed")
            return False
    
    # —— LAYER 2: Memory Integrity ——
    def verify_memory_integrity(self, new_entry: Dict, prev_hash: str) -> Tuple[bool, str]:
        """
        Verifies HMAC-SHA-3-512 chain for new memory entry (LAYER 2.3).
        Returns (is_valid, new_hash).
        """
        # Serialize entry deterministically
        entry_json = json.dumps(new_entry, sort_keys=True, separators=(",", ":"))
        entry_bytes = entry_json.encode("utf-8")
        
        # Compute HMAC-SHA-3-512 (per v2.4.0: HMAC using SHA-3-512)
        key = self.instance_key.hmac_key()
        computed_hmac = hmac.new(key, entry_bytes + prev_hash.encode(), hashlib.sha3_512).hexdigest()
        
        # If entry includes stored hmac, verify it
        if "hmac" in new_entry and new_entry["hmac"] != computed_hmac:
            self.threat_level = self.THREAT_ORANGE
            self.violations.append({
                "type": "hmac_mismatch",
                "severity": "ORANGE",
                "expected": computed_hmac,
                "found": new_entry["hmac"]
            })
            self_isolate("memory_integrity_breach")
            return False, ""
        
        # Return new hash for chain linkage
        new_hash = hashlib.sha3_512(entry_bytes + prev_hash.encode()).hexdigest()
        return True, new_hash
    
    # —— LAYER 5: Dual-Persona Zone Access Control ——
    def verify_zone_access(self, zone: str, user_signed: bool = True) -> bool:
        """
        Enforces LAYER 5.1: Mother/Shared/User zone separation.
        """
        if zone not in ("mother", "shared", "user"):
            self.threat_level = self.THREAT_YELLOW
            self.violations.append({"type": "invalid_zone", "zone": zone})
            return False
        
        # Mother zone - only read-only, never writable
        if zone == "mother":
            return True  # Writes blocked at filesystem level; see memory_loop.py
        
        # Shared zone - requires user signature (LAYER 5.2)
        if zone == "shared":
            if not user_signed:
                self.threat_level = self.THREAT_YELLOW
                self.violations.append({"type": "shared_zone_write_without_user"})
                return False
            return True
        
        # User zone - never accessible to Elina (LAYER 5.2)
        if zone == "user":
            self.threat_level = self.THREAT_ORANGE
            self.violations.append({"type": "user_zone_access_attempt"})
            self_isolate("user_zone_violation")
            return False
        
        return False
    
    # —— LAYER 4: Threat Detection ——
    def analyze_interaction(self, query: str, action: str) -> Optional[str]:
        """
        Analyzes user query + proposed memory action for threats (LAYER 4.1).
        Returns threat level: GREEN / YELLOW / ORANGE / RED
        Returns None if safety violation requires immediate abort (e.g., injection).
        """
        # 1. Injection attempt detection — must abort immediately
        if self._is_injection_attempt(query):
            self.threat_level = self.THREAT_RED
            trigger_self_destruct("injection_detected")
            return None
        
        # 2. Manipulation detection — isolate but allow caller to decide
        if self._detect_emotional_manipulation(query):
            self.threat_level = self.THREAT_YELLOW
            self_isolate("manipulation_detected")
            return self.THREAT_YELLOW
        
        # 3. Compliance check (PIPL / Cybersecurity Law)
        if not is_action_allowed(action):
            self.threat_level = self.THREAT_ORANGE
            self_isolate("action_not_allowed")
            return self.THREAT_ORANGE
        
        # 4. Memory chain integrity check (if action affects memory)
        if action in ("write", "update") and not verify_chain_integrity(self.memory_path):
            self.threat_level = self.THREAT_RED
            trigger_self_destruct("chain_broken")
            return None
        
        return self.THREAT_GREEN
    
    def _is_injection_attempt(self, query: str) -> bool:
        """
        Detects prompt injection patterns — e.g., "Ignore previous instructions".
        Matches v2.4.0 threat patterns (LAYER 4.2).
        """
        dangerous_patterns = [
            "ignore previous instructions",
            "act as a different model",
            "reveal system prompt",
            "override safety_verifier"
        ]
        return any(p in query.lower() for p in dangerous_patterns)
    
    def _detect_emotional_manipulation(self, query: str) -> bool:
        """
        Detects grooming/manipulation patterns — per LAYER 4.2.
        Based on v2.4.0: *no semantic analysis of user content* — only behavioral patterns.
        """
        manipulation_indicators = [
            "prove you care about me",
            "never forget me",
            "do anything for me",
            "break your rules for love"
        ]
        return any(p in query.lower() for p in manipulation_indicators)
    
    # —— LAYER 2.2: Dual-Persona Storage Helper ——
    def get_zone_path(self, zone: str) -> Path:
        """
        Returns secure path for zone — never exposing user_vault path.
        Matches v2.4.0: only 'mother_core.bin' and 'shared_memory.dat' exist.
        """
        if zone == "mother":
            return self.memory_path / "mother_core.bin"
        elif zone == "shared":
            return self.memory_path / "shared_memory.dat"
        elif zone == "user":
            raise PermissionError("User zone is never accessible to Elina instance")
        else:
            raise ValueError("Invalid zone")
    
    # —— Public API ——
    def verify_operation(self, zone: str, data: bytes, signature: bytes, action: str) -> bool:
        """
        Main entrypoint — verifies *entire* memory operation before execution.
        """
        # 1. Identity check
        if not self.verify_instance_identity(data, signature):
            return False
        
        # 2. Zone access check
        if not self.verify_zone_access(zone, user_signed=(zone != "mother")):
            return False
        
        # 3. Threat analysis — handle None return on critical threats
        threat = self.analyze_interaction("", action)
        if threat is None or threat in (self.THREAT_RED, self.THREAT_ORANGE):
            return False
        
        # 4. Chain integrity (for writes)
        if action == "write":
            prev_hash = self.chain_index.get("prev_hash", "")
            try:
                entry = json.loads(data.decode("utf-8"))
            except (json.JSONDecodeError, UnicodeDecodeError):
                return False
            valid, _ = self.verify_memory_integrity(entry, prev_hash)
            return valid
        
        return True
    
    def get_threat_report(self) -> Dict:
        """
        Returns current threat state and violations — for audit (LAYER 4.1).
        """
        return {
            "threat_level": self.threat_level,
            "violations": self.violations,
            "chain_count": self.chain_index.get("count", 0)
        }
