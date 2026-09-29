# Device Contract v1

## Purpose

Defines the canonical representation of a registered Family Safety device.

## Required Fields

- device_id
- device_name
- platform
- android_version
- app_version
- management_state
- connection_state
- battery
- last_seen
- location_capability
- created_at
- updated_at

## Field Rules

### device_id
- Type: string
- Required: yes
- Must be unique
- Must not contain secrets

### device_name
- Type: string
- Required: yes
- Human-readable device label

### platform
- Type: string
- Required: yes
- v1 supported value: android

### android_version
- Type: string
- Required: yes

### app_version
- Type: string
- Required: yes

### management_state
- Type: enum
- Required: yes
- Allowed:
  - unmanaged
  - managed
  - device_owner
  - unsupported

### connection_state
- Type: enum
- Required: yes
- Allowed:
  - online
  - weak
  - intermittent
  - offline

### battery
- Type: object
- Required: yes
- Required fields:
  - level_percent
  - charging
  - timestamp
- level_percent must be an integer from 0 to 100

### last_seen
- Type: timestamp
- Required: yes
- Format: UTC ISO 8601

### location_capability
- Type: object
- Required: yes
- Required fields:
  - supported
  - permission_state
  - background_supported
- permission_state allowed values:
  - granted
  - denied
  - restricted
  - not_determined

### created_at
- Type: timestamp
- Required: yes
- Format: UTC ISO 8601

### updated_at
- Type: timestamp
- Required: yes
- Format: UTC ISO 8601

## Invariants

1. device_id must remain stable for the lifetime of the registered device record.
2. Raw device information must not be overwritten by AI-derived information.
3. Unsupported Android capabilities must be explicitly reported.
4. Timestamps are stored in UTC.
5. Every update must be traceable through an audit record.
6. Secrets and authentication tokens must never be stored in this contract.

## Versioning

Contract version: v1

Breaking changes require a new contract version.

Non-breaking additions must remain backward compatible.

## Security

This contract does not contain passwords, access tokens, private keys, or other authentication secrets.
