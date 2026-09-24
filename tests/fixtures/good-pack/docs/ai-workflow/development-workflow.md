# Development workflow (fixture)

## Task routes
### R-001 Health and damage change
Start: Assets/Scripts/Game/Health.cs#Health.TakeDamage (C-004)
State owner and scene/assets: Health component in Dev.unity
Invariants: Current never below zero
Protected areas: P-001
Required integration step: keep the Bootstrap reference in Dev.unity intact
Checks: V-002, V-003

### R-002 Scene wiring
Start: Assets/Scenes/Dev.unity (C-002)
State owner and scene/assets: Bootstrap component
Invariants: _player must reference a Health instance
Protected areas: P-002
Required integration step: edit through the editor, never fabricate GUIDs
Checks: V-001

## Increments
### I-001 Dev scene boots with a live Health component
Hard depends on: none
Soft depends on: none
Verification depends on: V-001
Exit check: V-001
Status: not_started
