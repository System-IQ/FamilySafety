# Family Safety Contracts v2

v2 adds **provenance-first** contracts on top of v1.

## Principles

1. RAW data is immutable. Never overwritten.
2. Any derived value MUST carry provenance.
3. Every algorithm has a version and a release state.
4. AI is analysis, never source of truth.
5. If data is insufficient → explicit `insufficient_data` outcome, not a guess.

## Schemas

| Schema | Purpose |
|--------|---------|
| `algorithm.schema.json` | Registry of algorithms (GPS cleaning, anomaly detection, …) |
| `provenance.schema.json` | Traceability of any derived value |
| `derived_record.schema.json` | A derived record with mandatory provenance + quality |
| `event.schema.json` | Unified timeline entry across the platform |
| `safe_zone.schema.json` | Geofence definitions |
| `alert.schema.json` | Safety alerts (SOS, low battery, geofence exit, …) |

## Compatibility

- v1 contracts remain valid for **raw** payloads (device, command, location, route, record).
- v2 contracts are **additive**: derived values, events, alerts, safe zones.
- Never downgrade a v2 record to v1.
