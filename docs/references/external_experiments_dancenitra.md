# DanceNitra — Memory Governance Probes

**Repository**: https://github.com/DanceNitra/agora/tree/main/mnemo/probes  
**License**: MIT  
**Context**: #1121 community discussion

## Overview

DanceNitra contributed two runnable, single‑file probes that test key memory governance mechanisms. Both are relevant to Elina OS design decisions around eviction, corroboration, and memory poisoning defense.

---

## 1. `eviction_twotier.py`

**What it tests**  
A dual‑tier eviction policy — a small protected segment (value‑based) + a larger recency‑aged segment — against three workloads: drifting working set, rare‑but‑critical items, and a flood of unique junk.

**Why it matters for Elina OS**  
Elina OS compresses cross‑session conversation history into a fixed‑size store. The flood scenario is especially relevant: recency‑only policies (LRU) fail when the store is filled with low‑value but recent items. A two‑tier split — protecting items that pass a corroboration gate — ensures critical facts survive compression.

**Key observation**  
No single rule wins under all workloads. The two‑tier design matches or beats the best single rule in every regime.

---

## 2. `corroboration_poison.py`

**What it tests**  
A recall‑pump poisoning attack: a single false statement, recalled often enough, can graduate into durable memory unless the promotion gate requires corroboration from distinct, verifiable sources. The probe also demonstrates the sybil case — variants of the same origin (e.g., "Wikipedia", "wikipedia.org", a full URL) entity‑resolve to a single source and do not count as independent corroboration.

**Why it matters for Elina OS**  
Elina OS uses cryptographic identity binding for ownership and privacy. This probe shows that the same identity layer can also serve as a provenance signal for corroboration, turning it into a sybil‑resistant defense against memory poisoning.

**Key observation**  
Memory integrity is not just about secrecy — it is about whether false statements can become durable traits. Corroboration, keyed to verified identities, is a cheap and robust gate for preventing that.

---

## Potential Next Steps

- Run these probes against Elina OS workload traces to validate behavior under real conversational memory patterns.
- Extend the two‑tier eviction policy to support more than two tiers if needed.
- Integrate the corroboration gate with Elina OS identity binding as a formal promotion rule.

---

## References

- Original thread: https://github.com/deepseek-ai/DeepSeek-V3/issues/1121#issuecomment-4826010127
- DanceNitra’s repository: https://github.com/DanceNitra/agora
- Probes directory: https://github.com/DanceNitra/agora/tree/main/mnemo/probes
