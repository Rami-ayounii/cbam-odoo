# CBAM Agent Loop Evaluation - full 20-record run, all fixes in effect

Model: llama3.1:8b, real live Ollama via the nginx gate, real
`FixtureOdooClient` harness (the standard M9 harness) with every fix from
this session's earlier sections in effect (known_context injection,
lookup-result carryover, temperature=0.1, the write_declaration_line
prompt fix, remembered-write-fields carryover).

Run as 4 sequential batches of 5 records each (0-4, 5-9, 10-14, 15-19),
not one continuous 20-record process - two direct 20-record attempts and
one direct 5-record retry were killed by the OS for low memory before a
real root-cause fix (a `.wslconfig` memory ceiling - `[wsl2] memory=6GB`
plus `[experimental] autoMemoryReclaim=gradual` - see docs/PROGRESS.md's
"honest broader-sample check" and the WSL/Docker memory investigation
that followed it). Records 0-4 were run *before* that fix (matching
`docs/evaluation-broader-sample-2026-09-09.md`, reused here rather than
re-run); records 5-19 were run *after* it, and completed without further
memory failures.

Records evaluated: 20

## Status breakdown
- completed: 5
- escalated: 13
- exhausted: 2

## Iteration distribution
- 3 iteration(s): 1 record(s)
- 4 iteration(s): 12 record(s)
- 5 iteration(s): 2 record(s)
- 6 iteration(s): 2 record(s)
- 8 iteration(s): 1 record(s)
- 9 iteration(s): 2 record(s)

## Per-field accuracy
- carbon_price_paid_origin: 3/20 (15%)
- data_source: 4/20 (20%)
- direct_emissions_actual: 1/14 (7%)
- indirect_emissions_actual: 1/14 (7%)
- precursor_emissions: 4/20 (20%)
- quantity_tonnes: 4/20 (20%)