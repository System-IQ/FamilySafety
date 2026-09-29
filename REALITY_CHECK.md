# Reality Check

## Project Principle

This project must use real implementations and real tests.

## Important Constraints

- Development is phone-only.
- Termux is the primary local development environment.
- GitHub is the source-control repository.
- Admin and Child are the two user-facing applications.
- Backend is infrastructure, not a third user-facing application.

## Reliability

The system must support:
- Offline operation where technically possible
- Persistent local storage
- Resumable synchronization
- Retry with backoff
- Data integrity checks
- Crash recovery
- Health checks
- Safe rollback

## Intelligence

AI/analysis must never overwrite raw device data.

Every derived result should identify:
- Source
- Algorithm
- Version
- Timestamp
- Evidence
- Confidence
- Uncertainty

## Android

No feature is assumed to work on every Android version/device.

Unsupported capabilities must be detected and reported.

Background execution and reboot recovery must use official Android mechanisms.

## Security

No:
- hidden surveillance
- stealth persistence
- bypassing Android security
- unauthorized camera/microphone access
- privilege escalation

Use transparent, consent-based Android APIs and managed-device capabilities.

## Testing

A phase is complete only when:
1. Implementation exists.
2. Build/test succeeds.
3. Failure cases are tested.
4. Results are documented.
5. Git commit is created.
