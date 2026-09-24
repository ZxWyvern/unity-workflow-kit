# 09 — Conditional Contracts

Generate only contracts that match systems actually present or explicitly requested. Do not create empty specialized documents.

## Narrative / cutscene / audio / procedural animation

Capture:

- beat/event ID;
- design authority;
- player task;
- entry state;
- exact trigger;
- authoritative owner;
- retrigger policy;
- timeline origin/offsets;
- asset references or pending slots;
- input/camera ownership;
- audio priority;
- start/rest/final state;
- completion acknowledgement;
- pause/skip/interruption;
- teardown;
- restore policy;
- fallback;
- observable acceptance.

A delay timer does not prove gameplay completion. Feel/pacing must be judged in runtime when those qualities matter.

## Networking

Capture:

- authority owner;
- participants;
- request identity;
- validation boundary;
- replicated state;
- ordering/duplicate/stale handling;
- disconnect/reconnect;
- scene/session transition;
- test topology and latency conditions;
- acceptance.

## Editor tooling / package consumer path

Capture:

- entry point;
- valid selection/input;
- supported versions;
- assets/settings touched;
- Undo/dirty behavior;
- cancellation/failure;
- domain reload/re-entry;
- preview vs commit;
- sample verification;
- acceptance.

## Performance

Capture:

- measured problem;
- workload;
- target hardware;
- editor vs player;
- capture method;
- baseline;
- intervention;
- correctness constraints;
- comparable post-change measurement;
- residual limits.

Never invent FPS, memory, timings, GC, or profiler values.
