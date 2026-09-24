# Project context (FIXTURE, not a real project)

## 1. Provenance and coverage
Snapshot: 2026-09-24, source_kind fixture, revision null (no version control), dirty unknown.
Read: Bootstrap.cs, Health.cs, Dev.unity, ProjectVersion.txt.

## 2. Pack profile and tier
Profile standard. Tier small (2 scripts, 1 scene).

## 3. Protected areas
- [P-001] Assets/ThirdParty/** | reason: vendor code
- [P-002] Saves/live/** | reason: live save data

## 4. Intended experience and design conflicts
No design document available. Unknown.

## 5. Stack and version evidence
Declared editor version: see C-001. Running version unknown.

## 6. Entry and startup path
Dev scene (provisional) holds a Bootstrap component: C-002, C-003.

## 7. Subsystem map
Health: state owner of hit points. Files: Health.cs. Caller: Bootstrap. Tests: none present.

## 8. Representative paths
Awake -> Bootstrap.Awake -> Health.Initialize(100). Damage path: Health.TakeDamage clamps at zero (C-004).

## 9. Scene, prefab, and config bindings
Bootstrap._player references a Health instance in Dev.unity (C-002).

## 10. Feature state split
Health clamp: source yes (C-004), wiring partial (C-002), execution: see C-005.

## 11. Claims
- [C-001 | source_verified | ProjectSettings/ProjectVersion.txt | snapshot] Declared editor version is 6000.0.0f1. | deps: none | invalidates: package_or_unity_version_changed | limit: running editor version unknown
- [C-002 | serialized_verified | Assets/Scenes/Dev.unity | snapshot] Dev scene serializes a Bootstrap script reference with _player set. | deps: C-003 | invalidates: serialized_dependency_changed,entry_path_changed | limit: not opened in the editor
- [C-003 | source_verified | Assets/Scripts/Game/Bootstrap.cs#Bootstrap | snapshot] Bootstrap.Awake initializes _player with 100. | deps: none | invalidates: source_changed | limit: Play Mode order not observed
- [C-004 | source_verified | Assets/Scripts/Game/Health.cs#Health.TakeDamage | snapshot] TakeDamage clamps Current at zero. | deps: none | invalidates: source_changed | limit: none
- [C-005 | execution_verified | Assets/Scripts/Game/Health.cs#Health.TakeDamage | snapshot] Clamp behavior observed in an EditMode run, see V-002. | deps: C-004 | invalidates: source_changed,test_environment_changed | limit: EditMode only
- [C-006 | proposed | Assets/Scripts/Game/DamageEvent.cs | snapshot] A DamageEvent type could decouple presentation from Health. | deps: none | limit: not adopted
- [C-007 | unknown | Assets/Scenes/Dev.unity | snapshot] Player build behavior of the Dev scene. | deps: none | limit: no build access

## 12. Detailed findings
### F-001 Bootstrap wiring is not runtime-verified
Class: verification gap | Confidence: medium | Basis: static
Evidence: C-002, C-003
Impact and trigger conditions: a null _player reference would throw in Awake; not observed.
Smallest follow-up and acceptance: V-001 (I-001)

### F-002 No late-subscriber initialization for Health
Class: source-supported risk | Confidence: low | Basis: static
Evidence: C-004
Impact and trigger conditions: UI created after Initialize would miss the current value.
Smallest follow-up and acceptance: V-003

## 12b. Closed findings
- [F-003 | closed | V-002] Health clamp at zero was unverified; closed by the EditMode run

## 13. Overflow finding stubs
F-011 | design conflict | medium | C-007 | reason deferred: needs a design document
F-012 | optional improvement | low | C-006 | reason deferred: over the cap and not blocking

## 14. Available tools and tests
No test assembly present. Shell available. Editor not connected. V-002 was a one-off EditMode run.

## 15. Not inspected
Everything outside the four files listed in section 1. Package cache, other scenes, and the GDD were not available.
