# Agentic AI for Automated CBAM Compliance Declarations in Odoo

**Author:** Rami AYOUNI
**Project type:** academic project — no commercial/production use
**Development window:** 2026-07-28 → 2026-09-09 (54 commits)

This report documents the design, implementation, and empirical evaluation
of a system that automates EU Carbon Border Adjustment Mechanism (CBAM)
declarations for steel and aluminium imports inside Odoo, using a
locally-hosted, genuinely agentic large-language-model loop for document
extraction, paired with a deterministic, LLM-free calculation engine for the
compliance arithmetic itself.

---

## Table of Contents

- General Introduction
- **Chapter 1 — Project Context and State of the Art**
  - Host Organisation
  - 1.1 State of the Art
  - 1.2 Critique of the State of the Art
  - 1.3 Problem Statement
  - 1.4 Existing Methodologies for This Problem and Their Limits
  - 1.5 Proposed Solution
  - Conclusion
- **Chapter 2 — System Analysis and Design**
  - 2.1 Requirements Specification
  - 2.2 Actors and Use Cases
  - 2.3 Dynamic View: Sequence Diagram
  - 2.4 Static View: Data Model
  - 2.5 Design Philosophy
  - 2.6 System Architecture
  - Conclusion
- **Chapter 3 — Implementation and Results**
  - 3.1 Model Selection Methodology
  - 3.2 The Deterministic Calculation Engine
  - 3.3 The Agentic Pipeline
  - 3.4 Results
  - 3.5 Limitations and Discussion
  - Conclusion
- General Conclusion
- Bibliography

---

## General Introduction

Regulatory compliance in international trade has traditionally relied on
manual document review: an analyst reads a supplier's mill certificate or
carbon-intensity report, cross-references it against a country's published
default emission values, and manually computes a liability. As the European
Union's Carbon Border Adjustment Mechanism enters its definitive,
annual-declaration phase in 2026, this manual burden falls on every EU
importer of steel and aluminium — and, symmetrically, creates new reporting
pressure on the non-EU exporters whose shipment documents now feed directly
into a foreign compliance calculation. Large language models offer an
obvious lever to automate the reading and reconciliation of such documents,
but a compliance number is exactly the kind of output where an LLM's
well-documented tendency to hallucinate plausible-looking values cannot be
tolerated.

This project resolves that tension architecturally rather than by hoping a
model behaves: a deterministic, LLM-free calculation engine computes every
compliance number, while a genuinely agentic tool-use loop — a locally
hosted, open-weight LLM that decides for itself which extraction, lookup,
and validation tool to call, in what order, until it is confident or
escalates — handles the unstructured part of the problem. The two halves
communicate over a private network between two machines and are integrated
into a working Odoo 17 module, so the result is a declaration workflow a
real compliance team could open and use, not a research prototype in
isolation.

This report is organised into two chapters. Chapter 1 establishes the
regulatory context, states the problem, and reviews the literature on
agentic AI, tool use, and hallucination risk that motivates the system's
design. Chapter 2 presents the architecture, the calculation engine, the
agentic pipeline, and the empirical evaluation results, and closes with a
candid discussion of the system's limitations. A general conclusion
summarises the contribution and outlines future work.

**Keywords:** Agentic AI, Large Language Models, Tool Use, EU CBAM,
Regulatory Compliance Automation, Odoo, Hallucination Mitigation

---

## Chapter 1 — Project Context and State of the Art

### Introduction

This chapter first presents the host organisation, then reviews the state
of the art in EU CBAM regulation and in agentic, tool-using language
models, critiques that state of the art against the specific demands of
high-stakes numeric compliance work, and formulates the resulting problem.
It then reviews the existing methodologies used for compliance-document
automation and their limits, and closes by presenting this project's
proposed solution — objectives, research questions, and scope.

### Host Organisation

This project was carried out at **ninety. Startup House**, a coworking
space and startup-support organisation based in Sfax, Tunisia (Rte Mahdia
KM 1.5, El Bosten).

**Mission and vision.** ninety.'s stated mission is to assist innovative
SMEs and startups throughout their entrepreneurial journey, by offering a
dynamic working environment, personalised support, and the resources
needed to turn an idea into a functioning business. Its longer-term vision
is to become a primary innovation catalyst for the Sfax region, building an
ecosystem in which startups can not only survive but grow, and in doing so
inspire further entrepreneurship locally.

**Core values.** Innovation (fostering creativity and originality in the
startups it hosts), Collaboration (encouraging teamwork between startups,
mentors, and investors), Community (building a supportive network oriented
toward shared success), Excellence (pursuing continuous improvement and
quality), and Ethics (emphasising transparency, accountability, and mutual
respect).

**Services.** Beyond coworking desks, ninety. offers private offices,
dedicated training and study spaces, meeting rooms for presentations and
workshops, and business domiciliation (virtual office) services for
early-stage companies that do not yet need a physical office of their own.
It is within this startup-support environment surrounding company building
and entrepreneurship that the present project's own subject matter —
automating a specific, high-stakes regulatory compliance task with agentic
AI — was defined and carried out.

### 1.1 State of the Art

**EU CBAM as a moving regulatory target.** Regulation (EU) 2023/956
establishes the Carbon Border Adjustment Mechanism and its Annex I/Annex II
scope [6]; Directive 2003/87/EC, Art. 10a(1a), defines the phase-out
schedule for the free-allocation benchmark deduction (2.5% phased out in
2026, rising to 100% by 2034) [7]; Commission Implementing Regulations
2025/2621 and 2026/1412 publish the yearly country/route default emission
values, markup schedule, and EU ETS free-allocation benchmarks used in this
project's reference data [8]. The Joint Research Centre's JRC134682 report
[1] is the underlying scientific basis for these values. CBAM entered its
definitive phase on 1 January 2026: declarations became annual rather than
quarterly (the first annual declaration, covering 2026 imports, is due 30
September 2027), and a binding 50-tonne-per-year exemption applies below
which no certificate obligation arises [6]. What distinguishes this
regulatory domain from a typical integration target is that the
"constants" a naive implementation would reach for are neither constant
nor available in one place: default emission values are published per
exporting country, carry a yearly markup that itself changes, and are
periodically revised by implementing acts [8] — a requirement that shaped
the data model (§2.4) more than any purely technical consideration did. A
system that hardcodes these figures in application code is wrong the
moment a new implementing regulation is published; the data must be
modelled as a versioned reference table, not a constant.

**Tool-using LLMs and the ReAct paradigm.** LLMs capable of multi-step
reasoning and external tool use have enabled agents that autonomously
decompose complex goals into executable steps [3]. The ReAct framework [2]
grounds LLM reasoning in external reality by interleaving reasoning traces
with action steps — calls to external tools or APIs: at each step the
model reasons about what it has learned, selects a tool call, and
incorporates the result before deciding the next step, repeating until it
judges the task complete. This is the execution model this project's
orchestrator implements (§3.3). The distinguishing property is that the
loop contains no knowledge of which tool "should" come next — that
decision is made by the model at every turn, not by a step counter or a
branch on a previous tool's name. A fixed pipeline that always calls
"extract quantity, then emissions, then calculate" will, on a document
where the emissions figure is genuinely absent, either fail outright or
silently proceed with a placeholder; an agent that decides its own order
can instead request missing data, retry, or escalate. This project's
orchestrator relies on the underlying LLM's native function-calling
interface rather than the original paper's text-parsing format, and
realises the *Thought* half of the cycle as a prompted, not an enforced,
behaviour: the system prompt instructs the model to state its reasoning
before calling a tool, but the orchestrating code never checks that this
reasoning was actually produced — a deliberate omission, since adding such
a check would mean the code judging a turn's content, one step away from
the orchestrator-side ordering logic this project's design rules out (see
§1.4). This is measured, not enforced: every tool-calling turn is counted,
and the subset whose message content was non-empty is counted separately,
purely for audit and future evaluation.

**Hallucination risk in high-stakes numeric extraction.** Ji et al.'s
hallucination survey [4] documents the general tendency of generative
language models to produce fluent, plausible content unsupported by their
input — a risk that becomes a compliance-integrity problem the moment the
fabricated content is a number that determines a certificate liability.
Mallen et al. [5] additionally show that LLM recall degrades specifically
for rare, sparsely represented facts relative to popular ones — directly
analogous, in this project's domain, to a regulatory default value for an
infrequently-traded country/route combination being exactly the kind of
fact a general-purpose model is least reliable at recalling from parametric
memory alone, which motivates routing every default value through a
deterministic database lookup rather than ever trusting the model to recall
or compute one itself.

### 1.2 Critique of the State of the Art

Taken individually, none of the three bodies of work above was designed
for the exact situation this project sits in, and each leaves a gap that
matters once the output is a compliance number rather than a chatbot
answer.

**The ReAct paradigm assumes, but cannot verify, that reasoning actually
happens.** Its central claim — that interleaving explicit reasoning with
action improves grounding — rests on the model choosing to produce that
reasoning. Nothing in the paradigm, nor in the native function-calling
interfaces that have since replaced its original text-parsing mechanism,
gives an orchestrator a reliable way to confirm a "thought" preceded an
"action" rather than being an after-the-fact rationalisation, without
either constraining the model's output format or simply trusting it. The
paradigm is a prompting discipline, not a verifiable guarantee.

**General hallucination-mitigation techniques target the wrong granularity
for this problem.** The mitigations most commonly proposed against the
failure mode Ji et al. catalogue — retrieval augmentation, self-consistency
voting, learned fact-checking classifiers — are built for open-domain
factual question answering, where the model must recall or retrieve a fact
from a large, unbounded knowledge base. This project's extraction problem
is narrower: the value to be grounded is already sitting, in full, inside
one specific document the model has already been shown in its own context
window. None of the general literature distinguishes this "verify against
a document already in context" case from the harder open-domain case it
was designed for, leaving the specific, cheaper check this project relies
on (Chapter 2) unaddressed by name in that literature.

**The rare-fact-recall finding motivates a fix the literature does not
itself supply.** Mallen et al.'s own proposed remedy, adaptive retrieval,
assumes an underlying corpus large and general enough to retrieve from.
CBAM's regulatory default values do not fit that setting cleanly: they
form a small, precisely-scoped, versioned table with a handful of
dimensions (sector, route, country, validity period), not an open corpus.
Retrieval-augmented generation is the wrong tool for a lookup this
constrained — a deterministic query answers it exactly, every time, with
no retrieval-relevance uncertainty at all.

None of these three gaps is fatal to using a tool-using LLM for this task
— each simply means the general-purpose techniques in the literature must
be adapted, or replaced with a narrower, purpose-built mechanism, rather
than applied as published. Precisely locating where an agentic, tool-using
LLM can be trusted and where it cannot, for a task whose output is a real
financial liability, is the problem this project must now state precisely.

### 1.3 Problem Statement

This regulatory design has an asymmetric commercial consequence for
exporters outside the EU. Tunisia exports steel, aluminium, and phosphate
products to the European Union and is directly affected by CBAM reporting
requirements initiated on the EU-importer side — a Tunisian mill's own
paperwork becomes, without any change on the exporter's part, an input to a
foreign compliance pipeline. This motivates building the extraction layer
against realistic, heterogeneous document formats rather than a single
clean template, since the documents an importer actually receives from a
diverse supplier base are never uniform.

**The compliance-automation dilemma.** A CBAM declaration line requires
combining several pieces of information that are rarely all present, in a
consistent format, in a single document: a quantity, a production route, an
exporting country, and either a measured emissions figure or a default
value looked up from the versioned reference table above. Reading and
reconciling this information from real supplier paperwork is exactly the
kind of unstructured-text task large language models suit well. But the
number that comes out the other end determines a real certificate
liability — an LLM that hallucinates a plausible-looking emissions figure,
or silently drops a required field under multi-argument tool-call
construction (both observed in this project's own evaluation, §3.4),
produces a wrong compliance number that looks exactly like a right one. Any
system that lets a language model touch the arithmetic directly inherits
this risk unconditionally.

**The workflow-vs-agent gap.** Most existing document-automation tooling —
scripted extraction pipelines with an LLM call bolted onto one step —
encodes a predetermined execution path: extract field A, then field B, then
compute. This is brittle against the real variability of supplier documents
and conflates two concerns that should be kept separate: deciding what to
do next given what has been read so far (a reasoning problem, suited to an
LLM) and computing a number from validated inputs (a deterministic problem
that must never depend on a model's judgment). Left unresolved, this
conflation exposes a business to three compounding risks: silent numeric
hallucination (a fabricated value is indistinguishable from a genuine one
unless the system demands and verifies provenance), brittleness to
document variability (a fixed step sequence has no recovery strategy when
an expected field is genuinely absent), and silent drift against
regulatory data (hardcoded defaults become quietly wrong the moment an
implementing act revises them). A system that wants to be robust to
document variability without inheriting an LLM's arithmetic unreliability
needs to separate these concerns architecturally, not merely prompt around
the risk — this is the precise problem this project is designed to solve.

### 1.4 Existing Methodologies for This Problem and Their Limits

Robotic-process-automation (RPA) tools and template-based extraction
pipelines are the dominant existing approach to compliance-document
processing: fast and predictable on the exact layout they were built
against, but brittle to variation and offering no recovery mechanism
beyond failing the run. A change as small as a supplier reformatting a
mill certificate can silently break every downstream field mapping, and
nothing in the pipeline itself can tell the difference between "this field
is genuinely absent" and "this field moved to a different line."

General-purpose "LLM-in-the-loop" extraction tools typically apply a
single extraction call per document with no iterative reasoning, no
deterministic separation between extraction and calculation, and no
empirical evaluation of tool-calling reliability against the specific
small, locally-hostable models a zero-budget, data-sovereign deployment
would actually use. When such a tool does compute a downstream figure, it
is common for that computation to run inline, inside the same model call
that did the reading — collapsing exactly the extraction/calculation
boundary the problem statement above argues must be kept separate.

| Aspect | Existing Approaches | This Project |
|---|---|---|
| Execution model | Fixed pipeline or single-shot LLM call | Autonomous ReAct-style loop; model decides tool order/count at runtime |
| Compliance arithmetic | Often computed inline by the LLM or rigid template logic | Deterministic Python, zero LLM involvement, independently unit-tested |
| Regulatory data | Frequently hardcoded or embedded in prompts | Versioned reference table, never hardcoded, every value cited to a primary source |
| Hallucination defense | Rarely addressed explicitly | Multi-layer: plausibility bounds, untrusted-content framing, verbatim source-quote grounding |
| Model selection | Assumed from vendor/model-card claims | Empirically benchmarked, with a documented self-correction of an initial, biased ranking |

*Table 1.1 — Existing compliance-automation approaches vs. this project.*

Table 1.1 positions this project's own choices against these limits
directly. No widely available compliance-document tool separates
extraction (agentic) from calculation (deterministic) as a first-class
constraint; few publish a harness-matched benchmark of which
locally-hostable model is reliable enough before committing to one; and
CBAM's versioned, country/route-dependent default-value regime combined
with an agentic extraction loop has, to the author's knowledge, no
existing open implementation to compare against. This is the space the
proposed solution below occupies.

### 1.5 Proposed Solution

This project resolves the gaps identified above architecturally rather
than by prompting around them: a deterministic, LLM-free calculation
engine is kept categorically separate from a genuinely agentic tool-use
loop for document extraction, and candidate models are benchmarked
empirically against the project's own production validation logic rather
than trusted on the strength of a published card or a generic
tool-calling benchmark whose scoring rule may not match how the real
system actually consumes a model's output. Concretely, this project aims
to design and implement a genuinely agentic tool-use system for CBAM
declaration automation, paired with a deterministic compliance-calculation
core. Three objectives guide its development:

- **O1.** Implement a deterministic, unit-tested calculation engine for CBAM
  embedded emissions and certificate liability, with zero involvement from
  any language model in producing the compliance number itself.
- **O2.** Design and implement a genuine agentic tool-use loop — the model
  decides its own tool-call order and count, with no hardcoded step
  sequence in the orchestrating code — for supplier document extraction and
  reconciliation.
- **O3.** Empirically benchmark candidate locally-hosted language models for
  tool-calling reliability and end-to-end field-extraction accuracy, rather
  than assuming capability from a model's published card.

Two research questions guide the investigation:

- **RQ1.** How reliably can a small, locally-hosted language model execute
  a self-directed, multi-step tool-use loop for structured regulatory data
  extraction, and does a raw tool-calling benchmark actually predict that
  reliability?
- **RQ2.** What architectural and prompting safeguards are needed to
  prevent a tool-using language model from corrupting a compliance-critical
  numeric output, given that document text fed to the model is untrusted
  external input?

The system covers steel and aluminium imports only (Annex II's
direct-emissions-only sectors), uses synthetic supplier documents (no real
company data was available), and targets a two-machine deployment meshed
over a private VPN. Real-time monitoring, sectors beyond steel/aluminium,
and a production-grade multi-tenant deployment fall outside the scope of
this project. As Table 1.1 above summarises, each of these objectives
answers a specific limitation of the existing approaches already reviewed,
rather than a generic ambition to "add AI" to compliance work.

### Conclusion

This chapter has situated the project at ninety. Startup House, reviewed
CBAM's shift toward annual, versioned-data declarations together with the
agentic-AI and hallucination literature it depends on, and shown where
that literature falls short of the specific demands of a high-stakes
numeric compliance task. It then formulated the resulting
compliance-automation dilemma, reviewed the RPA-based and single-shot LLM
approaches currently used against it and their shared limits, and
presented this project's own objectives, research questions, and scope as
a direct response to those limits. These constraints — a deterministic
core, a genuinely autonomous extraction loop, and an empirical model
choice — directly shape the design presented next.

---

## Chapter 2 — System Analysis and Design

### Introduction

This chapter turns the problem and objectives stated in Chapter 1 into a
concrete design: functional and non-functional requirements, actors and
use cases, a sequence-diagram dynamic view, a class-diagram static view of
the Odoo data model, and the design philosophy and system architecture
these requirements led to. Chapter 3 then covers how this design was
actually implemented and evaluated.

### 2.1 Requirements Specification

**Functional requirements**

- **FR1.** Read a named field's value from an uploaded supplier document,
  using a deterministic regex pre-parser for known templated fields, with
  a fallback to LLM-grounded reading of the raw document text when no
  pattern matches.
- **FR2.** Look up a versioned default emission factor for a given
  sector, production route, and country as of the declaration date,
  rejecting an ambiguous match (zero or more than one candidate record)
  rather than resolving it silently.
- **FR3.** Deterministically compute embedded emissions and certificate
  liability for a declaration line from validated inputs, with zero
  language-model involvement in the arithmetic itself.
- **FR4.** Run an advisory self-consistency check on extracted data
  before the final write, including grounding any actual-sourced
  emissions value against document text genuinely extracted earlier in
  the same job.
- **FR5.** Escalate a declaration line to human review, either explicitly
  (model-initiated) or automatically once the iteration cap is reached
  without a completed write.
- **FR6.** Persist at most one validated write per declaration line per
  job, together with the full tool-call trace as an audit record.
- **FR7.** Distinguish, on the declaration line, a genuinely exempt line
  from one whose certificate figure is zero only because reference data
  has not yet been seeded — two states that would otherwise be visually
  identical to a user.
- **FR8.** Scope declarant users to their own declarations, declaration
  lines, and source documents; grant managers unrestricted access across
  all declarants.

**Non-functional requirements**

- **NFR1.** Compliance arithmetic must never depend on a language model's
  output; the agent loop may only decide *when* to trigger a calculation,
  never perform it.
- **NFR2.** Every agent job is bounded to at most 8–10 tool-calling
  iterations, with an automatic escalation fallback if the cap is reached
  without a terminal state.
- **NFR3.** Numeric values submitted for a declaration write are bounded
  by hard plausibility limits (quantity, emission-factor magnitude),
  enforced independently of the advisory consistency check.
- **NFR4.** A measured ("actual") emissions figure may only be written if
  accompanied by a verbatim quote that is a genuine substring of document
  text the system itself has already extracted during that job — not
  merely a plausible-looking string.
- **NFR5.** Regulatory reference data (emission factors, benchmarks, year
  parameters) is held in versioned, citation-bearing database tables; no
  compliance constant may be hardcoded in application code.
- **NFR6.** Uploaded document attachments are size-capped, with the limit
  enforced independently at both upload time and read time.
- **NFR7.** The orchestrator's job API fails closed: an unconfigured API
  key rejects every request rather than disabling authentication, and key
  comparison is constant-time.
- **NFR8.** The deployment is data-sovereign: the only external network
  dependency is the private VPN mesh between the two project-owned
  machines; neither host makes a third-party API call.

### 2.2 Actors and Use Cases

The system's own access-control configuration distinguishes exactly two
human-facing actors. The **Declarant** is row-scoped to their own
declarations, declaration lines, and source documents. The **Manager**
has unrestricted access across every declarant — a generalisation
relationship, since a Manager can do everything a Declarant can, plus
manage shared reference data.

One further point is worth making precise: the **Agent Loop (LLM)** is
modelled as a *secondary, system* actor, not an independently privileged
one. The orchestrator authenticates to Odoo as a single privileged
service account for every job, so the agent loop is never itself subject
to Odoo's row-level security — it is invoked by a Declarant's own trigger
action, and is instead scoped to the correct declaration and declaration
line entirely in application code.

| Use Case | Actor(s) | Description |
|---|---|---|
| Upload Supplier Document | Declarant | Attach a document to a declaration line as a `cbam.source.document` record. |
| Trigger Declaration Processing | Declarant | Start an orchestrator job for one declaration line; includes *Run Agentic Extraction Loop*. |
| Run Agentic Extraction Loop | Agent Loop | The ReAct-style loop from Chapter 1, executing the seven tools described in Chapter 3 until it writes or escalates. |
| Escalate for Human Review | Agent Loop | Extends the loop: triggered explicitly by the model, or automatically once the iteration cap is reached. |
| Review / Correct Declaration | Declarant, Manager | Inspect a line's extracted values, certificate status, and audit trail after a job completes. |
| Monitor Job Status | Declarant, Manager | Poll a job's status, iteration count, and tool-call/reasoning-turn counters. |
| Manage Reference Data | Manager | Maintain emission factors, benchmarks, year parameters, goods, installations, and production routes. |

*Table 2.1 — Use case descriptions.*

### 2.3 Dynamic View: Sequence Diagram

The main flow, *Trigger Declaration Processing*, crosses four
participants: the Declarant, Odoo (the Softworker host), the Orchestrator
(the FastAPI agent-loop service, also on Softworker), and the LLM (served
by Ollama on the Hardworker host). Only the Orchestrator–LLM exchange
crosses the Tailscale VPN between the two machines; every
Orchestrator–Odoo exchange is an RPC call over Softworker's own internal
Docker network.

1. Declarant → Odoo: upload document.
2. Declarant → Odoo: trigger processing.
3. Odoo → Orchestrator: `POST /jobs {declaration_id, line_id}`.
4. Orchestrator → Odoo: `202 Accepted`, `job_id` (return).
5. Orchestrator → Odoo: RPC read line context.
6. Odoo → Orchestrator: good, installation, source documents (return).
7. **[loop, max 8–10 iterations]** Orchestrator → LLM: `chat(messages)` — *crosses the VPN*.
8. LLM → Orchestrator: `tool_calls[]` (return).
9. Orchestrator → Odoo: RPC for `extract_field` / `lookup_default_value` (whichever read-only tool the model called; `calculate_emissions` and `check_consistency` are pure computation and never leave the Orchestrator).
10. Odoo → Orchestrator: document text / emission factor (return).
11. Orchestrator → LLM: tool result(s). *(loop repeats from step 7)*
12. **[alt]** Orchestrator → Odoo: RPC write (single-write guard) — *or* Orchestrator marks the job escalated.
13. Orchestrator → Odoo: RPC `write_llm_trace` (audit).
14. Declarant → Orchestrator: `GET /jobs/{id}/status` (poll).
15. Orchestrator → Declarant: status, iterations, counters (return).

Step 12 runs at most once per job regardless of how many loop iterations
preceded it.

### 2.4 Static View: Data Model

The domain is modelled as nine Odoo models, all in the custom `cbam`
addon.

| Model | Key fields | Relations |
|---|---|---|
| `cbam.declaration` | `declarant_id`, `reporting_year`, `status`, `is_exempt` (computed) | 1 → 0..* `cbam.declaration.line` |
| `cbam.declaration.line` | `quantity_tonnes`, `data_source`, `direct/indirect_emissions_actual`, `embedded_emissions_total` (computed), `certificates_required`/`certificates_status` (computed) | 0..* → 1 `cbam.good`; 0..* → 1 `cbam.installation`; 0..* → 0..1 `cbam.emission.factor`; 1 → 0..* `cbam.source.document`; computed refs to `cbam.good.benchmark` and `cbam.year.parameter` |
| `cbam.emission.factor` | `sector`, `country`, `direct_ef`/`indirect_ef`, `markup_pct`, `valid_from`/`valid_to` | 0..* → 1 `cbam.production.route` |
| `cbam.good` | `cn_code`, `sector`, `is_complex_good` | 1 → 0..* `cbam.good.benchmark` |
| `cbam.good.benchmark` | `benchmark`, `source_document` | 0..* → 1 `cbam.production.route`; unique per (good, route) |
| `cbam.installation` | `name`, `country`, `sector` | 0..* → 1 `cbam.production.route` |
| `cbam.production.route` | `code`, `sector` | unique per (code, sector) |
| `cbam.source.document` | `attachment`, `extraction_status`, `raw_llm_output` | 0..* → 1 `cbam.declaration.line` |
| `cbam.year.parameter` | `year`, `cbam_factor_year`, `reference_certificate_price` | unique per year |

*Table 2.2 — Class/data model.*

Several constraints keep this model internally consistent rather than
merely populated: a Python constraint on `cbam.declaration.line` rejects
a good/installation/route combination whose sectors disagree; a Python
constraint on `cbam.emission.factor` rejects a validity range that
overlaps an existing one for the same sector/route/country, so a lookup
can never silently match more than one record; SQL unique constraints
enforce one `(cn_code, sector)` per good and one `(code, sector)` per
production route; and a size constraint on
`cbam.source.document.attachment` caps every uploaded document, enforced
again independently at read time when the orchestrator fetches it.

### 2.5 Design Philosophy

Three principles governed every architectural decision.

**Determinism over convenience.** It would be simpler to let the language
model read a document and directly state a certificate liability. This was
ruled out categorically: the compliance number is computed by a standalone,
Odoo-independent Python module, unit-tested against hand-calculated
examples before any LLM code existed, and the agent never has write access
to that computation — it only decides when to call it.

**Autonomy over prescription.** The extraction layer makes its own
decisions about which tool to call, in what order, and how many times,
without a human- or code-authored step sequence. This ruled out a fixed
extraction pipeline in favour of a loop that reasons about the current
conversation state and selects the next action itself, every turn.

**Verifiability over assumed capability.** No model was chosen because of
published benchmark scores or model-card claims. Every candidate was run
against the project's own production validation logic, and — as §3.4
shows — an initial ranking obtained this way was itself later found to be a
measurement-methodology artifact and corrected, rather than left unexamined
once a plausible answer had been found.

### 2.6 System Architecture

The system is deployed across two roles, meshed over a private VPN:

```
Hardworker (LLM host, GPU-capable)                Softworker (Odoo host)
┌──────────────────────────────┐   Tailscale    ┌───────────────────────────────┐
│ Ollama (LLM inference)       │◄──── VPN ─────►│ PostgreSQL 16 (internal)      │
│ nginx (API-key gate,         │  (WireGuard,   │ Odoo 17 + `cbam` addon        │
│ rate limiting)               │   encrypted)   │ Orchestrator (FastAPI)        │
└──────────────────────────────┘                └───────────────────────────────┘
```

Only the Orchestrator–Ollama exchange crosses the VPN. The originally
specified topology gave each machine a dedicated Tailscale identity with
tag-scoped access control; a reproducible bug in the VPN provider's own
key-generation console forced a workaround, applied first to the
Softworker host during live deployment and then pre-emptively mirrored
onto the Hardworker host once the same root cause was recognised — the
deployed system now has **both** hosts reusing their own
already-authenticated connection instead of a dedicated sidecar identity,
trading away the per-role ACL scoping, a deviation documented rather than
silently absorbed.

A user uploads a supplier document in the Odoo UI and triggers processing;
Odoo calls the orchestrator's job endpoint and polls its status while the
agent loop runs against the LLM host over the VPN; on completion the
orchestrator performs a single validated write back to Odoo, and the full
tool-call trace is persisted as an audit trail (§2.3 above gives the
precise sequence).

The stack uses Odoo 17 Community, PostgreSQL 16, Ollama for local inference,
FastAPI for the orchestrator, Pydantic for argument validation, and the
plain `openai` client SDK pointed at Ollama's OpenAI-compatible endpoint —
deliberately with no agent framework (LangChain, AutoGen, CrewAI): for a
fixed, seven-tool schema, a framework adds indirection without benefit and
makes the deterministic-calculation boundary harder to audit.

### Conclusion

This chapter has turned Chapter 1's problem statement into a concrete
design: eight functional and eight non-functional requirements, two human
actors plus the agent loop modelled correctly as a secondary system
actor, a traced end-to-end sequence, and a nine-model data model built
around three deliberate design principles and a two-machine architecture.
Chapter 3 now covers how this design was implemented.

---

## Chapter 3 — Implementation and Results

### Introduction

This chapter covers how the design presented in Chapter 2 was actually
built and evaluated: the methodology used to select a candidate language
model, the deterministic calculation engine, the agentic pipeline built
around it, the empirical evaluation results, and a candid discussion of
the system's limitations.

### 3.1 Model Selection Methodology

The project's own raw tool-calling benchmark initially scored two candidate
models, `qwen3:8b` and `qwen2.5:14b-instruct`, at 0% valid tool calls,
apparently ruling them out entirely. The sample errors revealed the actual
cause: both models routinely emitted several tool calls in a single turn
(2–5 at once) rather than the single call per turn the benchmark's scoring
rule required — a real behavioural difference between models, but a
property of the benchmark's scoring assumption, not necessarily of whether
the real system could use such a model at all.

Critically, the project's actual agent loop imposes no such restriction —
it executes every tool call a model emits in a turn, preserving whatever
order the model chose. This made the raw benchmark's ranking directly
testable: `qwen3:8b` was re-run against the real, fixed evaluation harness
on the same ten synthetic records already used for the leading model. The
result reversed the apparent verdict: `qwen3:8b` tied the leading model's
field accuracy while completing successfully twice as often and never
escalating (§3.4). The raw benchmark had measured a real property but drawn
the wrong practical conclusion from it, because its scoring rule did not
match how the real system consumes a model's output. This comparison
motivated treating any raw benchmark as a hypothesis to re-test against the
real execution harness, not a final verdict — the methodology adopted for
every subsequent model evaluation in this project.

### 3.2 The Deterministic Calculation Engine

The calculation engine is an Odoo-independent module of four pure
functions, none of which the language model ever calls with an unvalidated
argument: an exemption check (the 50 t/year threshold), an embedded-
emissions calculation, a certificate-liability calculation implementing
Regulation (EU) 2023/956 Art. 9/31, and a versioned emission-factor lookup
that raises an error on zero or more than one match rather than resolving
an ambiguity silently.

Indirect emissions are deliberately excluded from the embedded-emissions
sum, not merely expected to be zero: steel and aluminium are Annex II,
direct-emissions-only sectors, so a non-zero indirect figure recorded for
statistical purposes can never leak into the compliance number. The
certificate calculation floors every deduction and adjustment at zero, so
no combination of inputs — including a negative or erroneous carbon
price — can invert the formula into a surcharge. A sign-inversion bug in an
earlier version of this formula (the phase-out factor applied directly
rather than as its complement, which would have understated every
early-year certificate requirement) was found and fixed with a dedicated
regression test — documented as a caught defect rather than omitted from
the record. Twenty unit tests cover the engine, all written and confirmed
failing before the corresponding implementation existed.

The Odoo data model wraps this engine with stored, dependency-tracked
computed fields and a status field distinguishing a genuinely exempt line
from one that is zero only because reference data has not yet been seeded —
two states that would otherwise be visually identical to a user. Row-level
security scopes each declarant to their own declarations.

### 3.3 The Agentic Pipeline

The model is exposed to seven fixed tools, defined once and shared,
unmodified, between the model-facing schema and the orchestrator's own
argument validation:

| Tool | Kind | Purpose |
|---|---|---|
| `extract_field` | Hybrid deterministic/LLM-grounded read | Deterministic regex pre-parse for known templated fields; falls back to the model reading a supplier document's raw text when no pattern matches |
| `lookup_default_value` | Deterministic read | Looks up a versioned default emission factor |
| `check_consistency` | Deterministic validation | Flags implausible, missing, or ungrounded extracted values |
| `request_missing_data` | Soft escalation | Flags a gap back for human/Odoo follow-up |
| `flag_for_human_review` | Hard escalation | Terminates the loop, requests human review |
| `calculate_emissions` | Deterministic calculation | The model decides *when* to call it, never computes the number itself |
| `write_declaration_line` | Single side effect | The only tool with write access, enforced to run at most once per job |

*Table 3.1 — The seven agent tools.*

`extract_field` is worth a closer look, since its mechanism changed
materially over the course of the project from a pure LLM read to a
**hybrid** one: because the synthetic supplier documents used for
evaluation (§3.4) are generated from a fixed set of templates, a
deterministic regex pre-parser attempts to read a templated numeric field
— and its own verbatim `source_quote` — directly from the document text
before ever asking the model to read it, falling back to LLM-grounded
reading only when no known pattern matches. This removes the model's own
reading reliability as a source of error for exactly the fields where a
fixed template makes deterministic parsing possible, while leaving
genuinely free-text fields to the model.

At each turn, the model receives the full conversation history and either
calls one or more tools or produces a final answer; the orchestrating code's
only responsibility is to execute whatever the model named and feed the
result back, with a hard iteration cap (8–10 loops) that auto-escalates if
the model has not converged — a documented, expected failure mode for small
local models that the design accounts for rather than treats as an edge
case.

Executing whatever the model requests is not the same as trusting it
blindly, and three safeguards answer RQ2 directly. First, facts the
orchestrator already knows with certainty (the good, installation,
quantity, and data source already set on the line) are injected directly
into tool calls, overriding whatever the model supplied — a response to a
measured failure mode where small local models reliably drop a required
field under multi-argument JSON construction. Second, the dispatcher
remembers a model's own prior tool results within one job, so a correctly
extracted figure is not silently lost if the model fails to restate it
several turns later, a failure mode observed live during development
(§3.5). Third, and most directly targeting the weakest measured fields
(§3.4), the final write is rejected for measured ("actual") emissions data
unless the model supplies an exact, verbatim quote that is a real substring
of text an extraction tool actually returned during that job — not merely a
plausible-looking string — with hard numeric plausibility bounds and a
single-write guard underneath as a structural backstop regardless of
whether the model itself is fooled or a document attempts prompt injection.
`check_consistency` runs a related, advisory version of this same
grounding check earlier in the loop, on the raw numeric value rather than
the quote, so a fabrication can be caught — and corrected by the model
itself — an iteration before the harder, final gate would otherwise
reject it.

### 3.4 Results

The evaluation proceeded in stages, each acting on evidence the previous
stage produced rather than on a fixed plan: a raw tool-calling benchmark
motivated re-testing two apparently-failing models against the real
harness; that re-test surfaced a second, larger candidate model that had
never been properly tried; testing it at full scale, rather than trusting
a flattering subsample, surfaced two further fixable gaps in the harness
itself. Every number below is reported at the sample size it was actually
measured at, and every regression found along the way is reported
alongside the fix, not silently absorbed into a single final figure.

**Raw benchmark and the model-choice correction.** Ten attempts per
candidate model, one real synthetic document each, scored against the
exact production argument-validation logic:

| Model | Valid tool calls | Avg. latency | Dominant failure mode |
|---|---|---|---|
| **llama3.1:8b** | **5/10 (50%)** | 1.7 s | Occasional invalid enum values |
| qwen2.5:7b-instruct | 4/10 (40%) | 2.2 s | Wrong argument types |
| qwen3:8b | 0/10 (0%) | 14.1 s | Multiple tool calls per turn (§3.1) |
| qwen2.5:14b-instruct | 0/10 (0%) | 5.5 s | Same multi-call pattern |

*Table 3.2 — Raw tool-calling benchmark.*

A full 20-record evaluation against the real harness, run after fixing
several real infrastructure bugs (missing document context, an ORM
constraint that made the default-value path structurally uncallable, an
unset inference temperature, a cross-call value-carryover bug), moved every
measured field from a 0% baseline:

| Field | Accuracy |
|---|---|
| `quantity_tonnes` | 4/20 (20%) |
| `data_source` | 4/20 (20%) |
| `carbon_price_paid_origin` | 3/20 (15%) |
| `precursor_emissions` | 4/20 (20%) |
| `direct_emissions_actual` | 1/14 (7%) |
| `indirect_emissions_actual` | 1/14 (7%) |

*Table 3.3 — Full 20-record field accuracy (`llama3.1:8b`; 5/20 completed,
4 genuinely correct writes; 13/20 escalated; 2/20 exhausted the cap).*

Following that, three models were compared against the same ten records
under the real, fixed harness:

| Model | Completed | Escalated | Exhausted | Field accuracy |
|---|---|---|---|---|
| llama3.1:8b | 4/10 | 5/10 | 1/10 | 30/30/30/12/12% |
| qwen2.5:7b-instruct | 0/10 | 0/10 | **10/10** | 0% |
| **qwen3:8b** | **8/10** | **0/10** | 2/10 | 30/30/20/12/12% (statistically tied) |

*Table 3.4 — Model comparison on the real, fixed harness (same 10 records).*

At this point the result was reported as an open, unresolved model-choice
question rather than resolved in favour of either model. The most
consequential pattern in this first phase was not any single accuracy
number but its ceiling: architectural and prompting fixes closed the
*completion* gap entirely — the model went from silently stopping
mid-loop, to reliably reaching a terminal state — without moving the
*accuracy* gap at all until the harness's own remaining bugs were
separately fixed. The open item this phase left —
`qwen2.5:14b-instruct`, M4's other apparently-0% model, dismissed for the
same scoring artifact as `qwen3:8b` but never itself re-tested — is what
the next stage closes.

**`qwen2.5:14b-instruct` at full 20-record scale.** The strongest
single-model result measured against any candidate at full 20-record
scale up to that point:

| | Completed | Escalated | Exhausted |
|---|---|---|---|
| 20 records | 14 | 0 | 6 |

| Field | llama3.1:8b | qwen2.5:14b-instruct |
|---|---|---|
| `quantity_tonnes` | 4/20 (20%) | 14/20 (70%) |
| `data_source` | 4/20 (20%) | 14/20 (70%) |
| `carbon_price_paid_origin` | 3/20 (15%) | 12/20 (60%) |
| `precursor_emissions` | 4/20 (20%) | 14/20 (70%) |
| `direct_emissions_actual` | 1/14 (7%) | 8/14 (57%) |
| `indirect_emissions_actual` | 1/14 (7%) | 8/14 (57%) |

*Table 3.5 — Full 20-record field accuracy: `llama3.1:8b` vs.
`qwen2.5:14b-instruct`.*

Every field improved substantially, including the two genuine-extraction
fields that had been this project's persistent ceiling across every prior
fix: 57%, up from 7% for `llama3.1:8b` and 12% for `qwen3:8b`. On this
evidence, `qwen2.5:14b-instruct` was subsequently adopted as this
project's default model, superseding `qwen3:8b`.

Before that adoption, `qwen3:8b` was re-tested once more with the full
safeguard set — the `source_quote` grounding gate and the tool-call/
reasoning-turn observability counters (§3.3) — exercised together for the
first time. Result: 16/20 completed, 0/20 escalated, 4/20 exhausted;
field accuracy 25–35% on plumbing-reachable fields, 7% on the two
document-comprehension fields — consistent with the earlier `qwen3:8b`
measurement, not a regression. This run also caught a real
instrumentation bug: `reasoning_turns` initially read as zero across
every turn, traced to `qwen3:8b` returning its chain-of-thought in a
separate `message.reasoning` field the client did not yet read. Fixed and
re-verified live: reasoning-turn counts then matched tool-call-turn
counts exactly — the model had been reasoning on effectively every turn
the whole time, the harness simply couldn't see it. `qwen2.5:14b-instruct`'s
57–70% remained far ahead of `qwen3:8b`'s 7–35% on the identical harness.

**Hybrid regex/LLM extraction: the strongest single-fix result.** Because
the synthetic document generator produces a fixed set of templates rather
than free prose, a deterministic regex pre-parser (§3.3) was added to
`extract_field`. Two real regressions were found and fixed before
trusting any aggregate result: an initial generic result shape got
mimicked by the model straight into `write_declaration_line`'s own call,
silently dropping every real value to its 0.0 default (fixed by keying
the result under the field's own real argument name); and a naïve
null-coercion fix for a related failure introduced a worse bug, silently
zeroing a real, just-extracted sibling value (fixed by having
`extract_field` remember its own successful parses, the same way
`lookup_default_value`'s results already were).

| | Completed | Escalated | Exhausted |
|---|---|---|---|
| 20 records | 17 | 3 | 0 |

| Field | Before hybrid extraction | After (all fixes) |
|---|---|---|
| `quantity_tonnes` | 70% | **90%** |
| `data_source` | 70% | **90%** |
| `carbon_price_paid_origin` | 60% | **70%** |
| `precursor_emissions` | 70% | **90%** |
| `direct_emissions_actual` | 57% | **86%** |
| `indirect_emissions_actual` | 57% | **86%** |

*Table 3.6 — Full 20-record field accuracy before/after hybrid extraction
(all fixes in effect).*

The strongest result this project measured, on any model, with any fix,
at full 20-record scale: the two document-comprehension fields — the
persistent ceiling every prior fix on the smaller models never moved past
roughly 10% — now sit at 86%, with zero exhausted records this run.
Stated plainly: this targets the harness's own fixed document templates,
not general-purpose document understanding — a real-world document in an
unfamiliar format falls back to exactly the pre-existing
model-reads-`document_text` behaviour, unchanged. The improvement is real
for this benchmark; it is not a claim about extraction robustness against
arbitrary real-world documents.

**The honest full-50-record benchmark.** Every result so far was measured
on the same first-20-record subset used throughout this project's
history. With the default model switched to `qwen2.5:14b-instruct` in
every deployment configuration, the full 50-record dataset was run for
the first time, rather than continuing to trust the more flattering
subsample.

| | Completed | Escalated | Exhausted |
|---|---|---|---|
| 50 records | 34 | 14 | 2 |

| Field | Records 0–19 | Records 20–49 | Full 50 |
|---|---|---|---|
| `quantity_tonnes`/`data_source`/`precursor_emissions` | 90% | 53% | 68% |
| `carbon_price_paid_origin` | 70% | 37% | 50% |
| `direct_emissions_actual` | 86% | 65% | 73% |
| `indirect_emissions_actual` | 86% | 57% | 68% |

*Table 3.7 — Field accuracy genuinely drops on the untested second half of
the dataset, for three distinct, individually traced reasons — not one
vague regression.*

Three distinct, live-verified mechanisms explain the drop:

1. **A test-harness fixture gap, not a model failure.** The development
   fixture table for default emission factors covered only 6 of the 13
   (sector, route, country) combinations actually needed; 7 of 11
   escalations in the 20–49 batch were exactly the uncovered
   `data_source="default"` records. Live-traced: `lookup_default_value`
   correctly returns a real "not found" error, and the model correctly
   escalates — textbook behaviour when reference data genuinely doesn't
   exist.
2. **A real architectural tradeoff: the `source_quote` gate correctly
   blocks a hallucination, but the single-write design then discards data
   that was validly extracted alongside it.** On a record where
   `direct_emissions_actual` was genuinely absent but
   `indirect_emissions_actual` was genuinely present, the model correctly
   extracted the real indirect value, then fabricated the missing direct
   value and an invented quote for it. The gate correctly rejected the
   fabrication three times before the model escalated — working exactly
   as designed — but the whole record still scored zero across every
   field, discarding the correctly-extracted indirect value along with
   the blocked fabrication. A real design tradeoff, not a bug.
3. **Plain run-to-run stochasticity.** Two easy/medium records with no
   missing fields and no fixture gap scored zero in the batch run; live
   re-tracing both immediately after, on the same code, produced a fully
   correct write both times — the inference temperature is deliberately
   non-zero.

These full-50 numbers, not the more flattering first-20 subset, are the
honest current benchmark.

**Closing the fixture-coverage gap.** Mechanism 1 was directly fixable:
the development fixture table was extended from 6 to all 13 combinations
actually present across the full 50-record dataset.

| Records 20–49 | Completed | Escalated | Exhausted |
|---|---|---|---|
| Before | 17 | 11 | 2 |
| After | 24 | 4 | 2 |

*Table 3.8 — Escalations dropped by exactly 7 — the exact count of
previously-uncovered `data_source="default"` records.*

| Field | Full 50, before | Full 50, after |
|---|---|---|
| `quantity_tonnes`/`data_source`/`precursor_emissions` | 68% | **86%** |
| `carbon_price_paid_origin` | 50% | **64%** |
| `direct_emissions_actual` | 73% | **81%** |
| `indirect_emissions_actual` | 68% | **76%** |

*Table 3.9 — Full 50-record field accuracy before/after the
fixture-coverage fix — the current, most representative measurement.*

This closes almost the entire gap back toward the original
first-20-only numbers, on the honest full 50-record sample. The remaining
gap is mechanisms 2 and 3 above, neither touched by this fix.

**Self-consistency (rejected), and two targeted fixes.** Mechanism 3's
stochasticity motivated testing self-consistency (running each record
twice, majority vote): 15 records, 2 independent live runs each. Result:
13/15 both-correct, 2/15 both-wrong (the same failure both times), **0/15
disagreed**. Every failure observed was systematic, not random noise a
second draw would dodge — so majority voting would have added 2× cost for
zero benefit, and would have actively increased false confidence on the
systematically-wrong records. **Rejected, not adopted.**

Tracing the two systematic failures directly found two real, fixable
causes instead: (1) one record's own extraction plan sometimes never
mentioned `carbon_price_paid_origin` at all — an attention failure, not a
parsing one — fixed by having the dispatcher opportunistically run the
regex pre-parser for that field whenever `extract_field` is called for
*any* field; (2) a `customs_declaration` record under
`data_source="actual"` (structurally lacking emissions data) saw the
model reason incorrectly that `data_source` "must really be default,"
burning all 9 iterations against a value the orchestrator had already
overridden — fixed with a system-prompt addition naming this exact
failure mode, reducing it to 3 iterations and a clean escalation.

| Field, records 0–19 | Before | After |
|---|---|---|
| `quantity_tonnes`/`data_source`/`precursor_emissions` | 90% | 90% (unchanged) |
| `carbon_price_paid_origin` | 70% | **80%** |
| `direct_emissions_actual`/`indirect_emissions_actual` | 86% | 86% (unchanged) |

*Table 3.10 — Only the field the first fix directly targets moved.
Measured on records 0–19 only; **not yet re-validated at the full
50-record scale** the rest of this section otherwise insists on (§3.5).*

**Summary metrics**

| Metric | Value |
|---|---|
| Development window | 2026-07-28 → 2026-09-18 |
| Commits | 66 |
| Python lines of code | ≈7,600 (incl. tests); ≈4,400 application code |
| Automated test functions | 175, across 14 test files |
| Odoo models implemented | 9 |
| Agent tools implemented | 7 |
| Candidate LLMs benchmarked | 4 |
| Default model | `qwen2.5:14b-instruct` |
| Field accuracy, plumbing-reachable fields (full 50, honest) | 0% → 64–86% |
| Field accuracy, document-comprehension fields (full 50, honest) | 0% → 76–81% |

*Table 3.11 — Project summary metrics.*

### 3.5 Limitations and Discussion

**Field accuracy, while now substantial, is not yet a production
reliability bar.** 64–86% on plumbing-reachable fields and 76–81% on
document-comprehension fields, at the full, honest 50-record scale, is a
large, real improvement over the original 0% baseline — but 7/50 records
still escalate and 2/50 still exhaust the iteration cap outright without
a write, and no field reaches 100%.

**The single-write design and the `source_quote` grounding gate can
interact to discard validly-extracted data.** When one field is
fabricated and correctly rejected on a record where a sibling field was
genuinely extracted, the whole record scores zero rather than partially
writing the good value — a real architectural tradeoff, identified and
reported above, not a bug, and not yet resolved.

**Two targeted fixes measured on records 0–19 have not been re-validated
at the full 50-record scale** that the rest of this section otherwise
insists on: the opportunistic carbon-price recovery and the
`customs_declaration` prompt rule (both above) moved
`carbon_price_paid_origin` from 70% to 80% on that narrower subset, but
the honest, full-scale figure this evaluation otherwise reports for that
field is 64% — an open item by the same honesty standard applied
everywhere else in this evaluation.

**A genuine cross-call value-carryover failure was observed live**: the
model correctly looked up a real emission factor, then invented different
numbers moments later when calling the calculation tool, and never supplied
the correct value to the final write. The dispatcher-side value memory built
in response is a mitigation of the symptom, not a fix of the underlying
model behaviour.

**The hybrid regex/LLM extraction path targets this dataset's own fixed
document templates, not general document understanding.** A real-world
document in an unseen format falls back to unaided LLM reading, exactly
as before the hybrid path existed — the 86% figure above is real for this
benchmark, not a general extraction-robustness claim.

**The two-machine network topology has not been verified in its
originally designed form, on either host.** A real, external,
still-unexplained bug in a third-party VPN provider's key-generation
console forced a workaround with a documented security trade-off (§2.6),
applied to both machines, rather than the dedicated-identity topology
originally specified. Live, two-machine verification of even the
workaround topology remains open.

**The LLM host has not yet been exercised against the final, physical Odoo
deployment.** Only the Odoo/database/orchestrator HTTP layer has been
live-verified on real hardware so far.

**Reasoning-turn instrumentation is now correctly measured — a
thinking-model content-field bug was found and fixed — but not yet
systematically correlated with extraction correctness.** One
live-retraced run showed reasoning-turn counts matching tool-call-turn
counts exactly; it remains an open, directly testable question whether
reasoning presence predicts a correct extraction across a full evaluation
sample.

### Conclusion

This chapter has shown the three design principles of Chapter 2 realised
concretely: an independently tested calculation engine no language model
ever writes to directly, a tool-use loop with no hardcoded ordering logic,
and a benchmarking methodology rigorous enough to catch and correct its
own initial ranking error, twice over — first correcting a
wrongly-dismissed `qwen3:8b`, then discovering and adopting the stronger
`qwen2.5:14b-instruct`. Applied to synthetic CBAM declarations for steel
and aluminium, and measured honestly at full dataset scale rather than on
a flattering subsample, the system raised measured field accuracy from a
0% baseline to 64–86% on plumbing-reachable fields and 76–81% on
document-comprehension fields — the fields this project's own evaluation
history had treated as a hard model-capability ceiling, until a larger
model and a hybrid deterministic/LLM extraction path together showed that
ceiling was not architectural. What remains open is not whether the
architecture works, but how far its two identified, still-unresolved
tradeoffs — the single-write/grounding-gate interaction, and two fixes
not yet re-validated at full scale — can be closed without reintroducing
the risks Chapters 1 and 2 were designed to rule out.

---

## General Conclusion

This project set out to address a concrete tension in applying large
language models to regulatory compliance: the same unstructured-document
reasoning capability that makes an LLM attractive for this task is exactly
the capability that makes it untrustworthy the moment it is allowed to touch
the number that number produces a real financial liability. To resolve this
without avoiding LLMs altogether, this project kept the two concerns
architecturally separate — a deterministic, independently verifiable
calculation engine on one side, and a genuinely autonomous, ReAct-style
tool-use agent on the other — wired together through a two-machine,
VPN-meshed deployment and integrated into a working Odoo module.

The evaluation revealed a finding more nuanced than a single accuracy
number: the dominant constraint on agentic compliance extraction is a small
local model's own tool-calling discipline, not the orchestration
architecture around it — and a model's apparent reliability is itself
dependent on how it is measured, not a fixed property of the model. The
project's own raw benchmark initially and wrongly dismissed a model that,
once re-evaluated against the real, more permissive execution harness,
matched the field accuracy of the presumed leader while completing twice as
often. This methodology-sensitivity of model ranking is the central finding
of this work: a benchmark that does not match the real system's execution
semantics can actively mislead an architectural decision, and empirical
re-verification against the production path — not a one-off benchmark — is
what a system like this needs to trust its own model choice.

Looking ahead, this work opens a clear continuation path: benchmarking
additional and fine-tuned models against the same harness-matched
methodology, extending the audit trail into a human-review interface that
surfaces grounding confidence per field, and restoring the originally
specified per-role network topology once its external blocker is resolved.
The architectural separation between deterministic calculation and agentic
extraction established here is what makes each of these an incremental
extension rather than a rebuild — the foundation is in place, and the next
step is to make the extraction layer worthy of the certainty the
calculation layer already provides.

---

## Bibliography

[1] Marijana Vidovic, Sarah Marmier, Neza Zore, and José Antonio Moya.
*Greenhouse gas emission intensities of the steel, fertilisers, aluminium
and cement industries*, JRC134682, European Commission Joint Research
Centre, 2023. DOI 10.2760/359533.

[2] Shunyu Yao, Jeffrey Zhao, Dian Yu, Nan Du, Izhak Shafran, Karthik
Narasimhan, and Yuan Cao. *ReAct: Synergizing reasoning and acting in
language models.* International Conference on Learning Representations,
2023. URL https://arxiv.org/abs/2210.03629.

[3] Stuart Russell and Peter Norvig. *Artificial Intelligence: A Modern
Approach.* Pearson, 4th edition, 2020. URL https://aima.cs.berkeley.edu/.

[4] Ziwei Ji, Nayeon Lee, Rita Frieske, Tiezheng Yu, Dan Su, Yan Xu, Etsuko
Ishii, Yejin Bang, Andrea Madotto, and Pascale Fung. *Survey of
hallucination in natural language generation*, 2023. URL
https://arxiv.org/abs/2202.03629.

[5] Alex Mallen, Akari Asai, Victor Zhong, Rajarshi Das, Daniel Khashabi,
and Hannaneh Hajishirzi. *When not to trust language models: Investigating
effectiveness of parametric and non-parametric memories.* Proceedings of
the 61st Annual Meeting of the Association for Computational Linguistics,
2023. URL https://arxiv.org/abs/2212.10511.

[6] European Union. *Regulation (EU) 2023/956 establishing a carbon border
adjustment mechanism*, 2023. Official Journal of the European Union.

[7] European Union. *Directive 2003/87/EC establishing a scheme for
greenhouse gas emission allowance trading*, as amended, Art. 10a(1a).
Official Journal of the European Union.

[8] European Commission. *Commission Implementing Regulation (EU)
2025/2621* (default values and markup schedule) and *Commission
Implementing Regulation (EU) 2026/1412* (EU ETS free-allocation benchmarks
2026–2030). Official Journal of the European Union.
