# Spec: Optional `source` Field & Supersession Key for Memory Records

**Status**: Draft for discussion  
**Related**: #47, #1121  
**Version**: 0.2 (added supersession)

---

## 1. Purpose

Add two optional, backward‑compatible fields to Elina memory records:

- `source` – to enable **corroboration** (distinguishing independent sources from repetition)
- `key` – to enable **supersession** (distinguishing current values from stale ones)

These mechanisms are orthogonal:
- **Corroboration** decides credibility: *can we trust this fact?*
- **Supersession** decides freshness: *which value is current?*

A fact can be well‑corroborated and stale. The two mechanisms work together but do not overlap.

---

## 2. Field Definitions

| Field    | Type          | Optional? | Description |
|----------|---------------|-----------|-------------|
| `source` | string or null| Yes       | Attributable origin id: `<channel>:<principal>` |
| `key`    | string or null| Yes       | `(subject, relation)` identifier, e.g. `"billing-api::auth-method"` |

- If a field is absent: the record behaves as it does today (no gate for that mechanism).
- If present: the corresponding gate applies.

---

## 3. Channel Taxonomy (Fixed)

| Channel  | Meaning                                          |
|----------|--------------------------------------------------|
| `user`   | Direct input from a human user                   |
| `tool`   | Output from an external tool or function         |
| `model`  | Inference from another model                     |
| `file`   | Imported from a file or external dataset         |
| `web`    | Retrieved from a web source                      |
| `custom:`| Experimental or external sources (escape hatch)  |

---

## 4. Corroboration Gate (Credibility)

A fact is considered **durable** (eligible for long‑term promotion) if it has been asserted by **≥ 2 distinct sources**.

- Distinctness is determined by the `principal` part of the source string, after entity resolution.
- Repetition from the same source does not count toward the threshold.

### Entity Resolution (Recommendation)

Before counting distinct sources, normalize source ids to collapse variants (prevents sybil‑like amplification):

| Original                      | Resolved to   |
|-------------------------------|---------------|
| `wikipedia.org`               | `wikipedia`   |
| `Wikipedia`                   | `wikipedia`   |
| `https://en.wikipedia.org/...`| `wikipedia`   |

---

## 5. Supersession (Freshness)

**Purpose.** Decides which value is current for a given `(subject, relation)`. Supersession is deterministic bookkeeping: no similarity threshold, no model call.

**Rule.** When a record is written with a `key`, the newest write for that key becomes current; every prior active record sharing the same key is retired (status: `superseded`) — kept as history, never deleted.

**Motivation.** Cosine similarity can't reliably distinguish a contradicted value from its replacement — we measured AUROC ≈ 0.61, near chance. A similarity store serves the stale value ~42% of the time; a `(subject, relation)` key drives that to 0%.

**Compose with Corroboration.** A superseding value still needs **≥ 2 distinct sources** to be durable. Until then it is **current‑but‑tentative**, and the last durable value is retained as fallback. A single‑source “update” cannot silently erase a well‑attested fact.

**Bi‑temporal guard.** Use event‑time (`valid_from` / `timestamp`) to order, not ingest‑time: a back‑filled record with an earlier `valid_from` does not supersede a genuinely newer same‑key value (the stale‑on‑arrival record is the one retired).

---

## 6. Test Scenarios

### Corroboration

| Scenario                                                              | Expected Behavior                               |
|-----------------------------------------------------------------------|-------------------------------------------------|
| Fact from one source, repeated 3 times                                | Not durable (1 distinct source)                 |
| Fact from `user` and `tool`                                           | Durable (2 distinct sources)                    |
| Same fact from `web` and `file`                                       | Durable (2 distinct sources)                    |
| Sybil: `wikipedia.org` + `Wikipedia` + `en.wikipedia.org`             | Counts as 1 source after entity resolution      |

### Supersession

| Scenario                                                                 | Expected Behavior                                           |
|--------------------------------------------------------------------------|-------------------------------------------------------------|
| Newer trusted write on same key                                          | Old retired, new current                                    |
| Single‑source update on same key                                         | Current‑but‑tentative; old durable value kept as fallback   |
| Back‑filled record with older timestamp                                  | Does NOT supersede a newer same‑key value                   |
| No key                                                                   | Unchanged behavior                                          |

---

## 7. Backward Compatibility

- `source` and `key` are optional and default to `None`.
- Existing records without either field retain their current behavior.
- The `store()` function will accept optional `source` and `key` parameters, both defaulting to `None`.

---

## 8. Next Steps

- Finalize gate semantics (distinct‑source counting, entity resolution, key behavior).
- Once spec stabilizes, implement in `memory_loop.py` with optional `source` and `key` parameters.
- Validate against the runnable reference (https://github.com/DanceNitra/agora/blob/main/mnemo/probes/supersession_replication.py).
