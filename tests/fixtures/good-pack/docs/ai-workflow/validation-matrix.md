# Validation matrix (fixture)

### V-001 Bootstrap initializes Health in the Dev scene
Covers: R-002, F-001
Mode: PlayMode
Preconditions and environment: editor connected, isolated save slot
Runner or exact manual input path: open Dev.unity, enter Play Mode
Expected observable result: Health.Current equals 100 after Awake
Status: not_run
Observed result and evidence location: none yet
Remaining limit or next action: needs an editor connection

### V-002 Health clamps at zero
Covers: R-001
Mode: EditMode
Preconditions and environment: fixture EditMode run
Runner or exact manual input path: call TakeDamage(1000) on a Health initialized to 100
Expected observable result: Current equals 0
Status: passed
Observed result and evidence location: Current was 0; illustrative fixture log at tests/fixtures/README.md
Remaining limit or next action: none

### V-003 Late subscriber receives current value
Covers: R-001, F-002
Mode: static
Preconditions and environment: source access
Runner or exact manual input path: read Health.cs for an initial-value notification path
Expected observable result: a late subscriber can read the current value
Status: not_run
Observed result and evidence location: none yet
Remaining limit or next action: schedule with the next Health change
