# Hardworker Tailscale fix (pre-emptive), and a rejected few-shot prompt experiment

## Part 1: pre-emptively fixing hardworker's Tailscale sidecar before it breaks again

At the human partner's request - they're currently away from the physical
hardworker machine, so live two-machine mesh verification (the punch
list's remaining "Add #3") isn't attemptable right now - looked for a
low-cost fix that doesn't need live access to that machine.

**Found one:** `hardworker/docker-compose.yml` still ran the old
Tailscale-sidecar pattern (a `tailscale` service + `TS_AUTHKEY`), even
though `softworker/docker-compose.yml` already dropped that exact pattern
in an earlier session after the Tailscale admin console's key-generation
page started producing auth keys (containing the literal substring
`CNTRL`) that the real control server rejects outright - root cause never
found, flagged to Tailscale support, worked around by using the host's
own already-authenticated native Tailscale client instead of a
per-role sidecar identity. `hardworker/docker-compose.yml` was never
updated to match, so bringing it up as-is would hit the identical wall
the very next time someone tries it on real hardware.

**Fix, mirroring the already-proven softworker/docker-compose.local-dev.yml
pattern exactly:** dropped the `tailscale` service entirely;
`nginx` now joins `network_mode: "service:ollama"` so
`nginx.conf.template`'s `proxy_pass http://127.0.0.1:11434` (kept
byte-for-byte unmodified) still reaches `ollama`'s listener without a
sidecar for both to share; `ollama` publishes `8443:8443` directly to the
host (nginx has no network identity of its own once it borrows ollama's
namespace, so nginx's listener is reachable through the port ollama
owns). Validated with `docker compose config` - clean.

Also updated `hardworker/.env.example` and `softworker/.env.example` to
drop the now-unused `TS_AUTHKEY` (the latter had never been cleaned up
when softworker's own fix was made earlier - a real, if minor, stale-doc
gap), updated `softworker/.env.example`'s `OLLAMA_BASE_URL` placeholder
comment (previously said "cbam-hardworker", hardworker's now-retired
per-role MagicDNS name), and removed `docs/secret-rotation.md`'s now-
inapplicable `TS_AUTHKEY` rotation row.

**Not done, and cannot be done from here:** the actual live two-machine
verification itself still needs someone physically at (or remotely
logged into) the hardworker machine to confirm its own Tailscale client
is installed and authenticated, then bring the stack up for real. This
fix only removes the specific, already-diagnosed obstacle that would
otherwise block that attempt on arrival - it doesn't substitute for the
real test.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 175
passed (no test suite changes - this is infra/config only);
`docker compose -f hardworker/docker-compose.yml config` validates
cleanly.

## Part 2: the few-shot extraction example - tried, found to actively regress accuracy, reverted

Direct continuation, implementing the punch list's last remaining
"Change" item: add a worked few-shot extraction example to
`SYSTEM_PROMPT`, since every prior prompt fix had been "remove a
burden," none "show correct behavior directly."

**What was tried:** a worked example using illustrative numbers (e.g.
`"direct_emissions_actual": 2.340`, quote `"Direct embedded emissions :
2.340 tCO2e/t"`) contrasting a correct extraction against a correctly-
refused fabrication for a genuinely-absent field.

**Result: a real, reproducible regression, not noise.** Two independent
full 20-record runs both landed far below the ~90% baseline (75%/65%/64%
and 75%/65%/57% across the six scored fields, vs. 90%/90%/80%/90%/86%/86%
immediately before this change) - confirmed as a real effect, not
sampling variance, by running it twice and getting consistently similar
(bad) numbers both times.

**Root cause, confirmed with a live trace (`SYNTH-0004`):** the model
correctly extracted the real `direct_emissions_actual=0.775` early in the
conversation, then several turns later, while recovering from an
unrelated tool-call error, said (verbatim): *"I will proceed with the
calculation using the direct emissions actual value of 2.340
tCO2e/tonne of product"* - **2.340 is the example's own illustrative
number**, not anything from this record's real document. The model
confused the system prompt's own worked example with the actual task
data several turns into the conversation and overwrote a value it had
already correctly extracted with a hallucinated one lifted straight from
the example text.

**Decision: reverted, not kept.** A concrete numeric example that shares
the same textual shape as the real extraction target ("Direct embedded
emissions : `<number>` tCO2e/t") is exactly the kind of content this
model can blend with genuine document content over a multi-turn
conversation - the fix intended to demonstrate ideal behavior instead
became a second, more insidious source of fabricated values than the one
`check_consistency`'s new grounding check was just built to catch. This
is a real, informative negative result: showing this class of model a
concrete worked example is a materially riskier prompting technique than
every "remove a burden" fix that came before it, not a smaller version of
the same kind of change. Re-traced `SYNTH-0004` after reverting -
correctly writes `0.775` again, 6/6 fields correct.

**If this is revisited in the future**, any worked example would need to
avoid a plausible-looking, correctly-formatted number in the same shape
as a genuine field value entirely - e.g. an abstract placeholder like
`<some-number>` rather than `2.340`, or a description of the *behavior*
without a fabricated data point to anchor on at all. Not attempted here;
flagged as the concrete lesson for next time, not a fix to try
immediately.

**Verification:** `python -m pytest softworker/tests/ shared/ -q` → 175
passed both before and after this change (the prompt was reverted to its
prior committed state exactly - `git diff` on `main.py` is empty).
