# M7 Source Verification: CBAM Emission Factor Seed Data

This is the permanent, committed record of the primary-source research
behind `shared/data/seed_emission_factors.py`'s seed tables
(`EmissionFactorSeed`, `YearParameterSeed`, `GoodBenchmarkSeed`). It exists
because `source_document` is a `required=True` Odoo field whose whole
purpose is "never invent a value, cite something real" — every quote,
citation, and piece of reasoning below is what those citation strings, and
the inline code comments next to each seeded field, refer back to.

Promoted from Task 6's working report
(`.superpowers/sdd/2026-09-08-project-completion-plan/task-6-report.md`),
which is git-ignored scratch and was never committed — this document is the
real, permanent home for that content. Do not re-point references at the
`.superpowers/` path; it is deliberately excluded from version control
(`.superpowers/sdd/.gitignore`) and will never exist on a fresh clone.

**Overall outcome (updated by Task 9, then Task 11 — see the addenda below
the original findings):** 9 of 10 tracked fields fully verified and seeded
from clean primary text (2 EU ETS benchmarks, the sector-wide 10% 2026
markup rate, 4 of 5 `EmissionFactorSeed.direct_ef` country/route pairings,
the 2026 `reference_certificate_price`, and `cbam_factor_year`); 1 remains
explained-and-blocked with a documented, evidence-based reason (not a
fetch failure — the sources were reachable and readable, but the specific
data point requested does not exist): steel EAF_DRI's `direct_ef` (no
country anywhere in either source has DRI/EAF-route steel data —
structurally absent, not a per-country gap). Task 6's original findings
below (sections "Fields resolved" and "Fields still blocked") are the
unedited historical record; the "Task 9 addendum" section further down
documents what changed since, including one correction (Tunisia's
aluminium data was wrongly reported absent by Task 6); the "Task 11
addendum" documents `cbam_factor_year`'s resolution.

## Method note: how the primary sources were actually reached

A prior session's attempt failed for infrastructure reasons: EUR-Lex
`WebFetch` returned empty content, the JRC134682 PDF's text layer came back
garbled, and `WebSearch` queries turned up contradicting secondary-source
figures. This session had `pdftotext` (poppler/xpdf 4.06) available in the
Git Bash environment. `WebFetch` on the EUR-Lex PDFs directly mostly hit a
*different* failure mode this time (`maxContentLength size of 10485760
exceeded` — the official PDFs run 0.5–41 MB, over `WebFetch`'s 10 MB cap).
Working around that with `curl` (direct download, no size cap) followed by
local `pdftotext -raw` extraction produced clean, readable text for every
document fetched this way. `pdftotext -raw` (preserving PDF content-stream
order) gave correctly-ordered table rows; `pdftotext -layout` on the same
files reproduced the same garbled/misaligned-table failure the prior
session hit — confirming the *rendering mode*, not file size or
unusability, was the actual point of failure last time.

Three primary sources were fetched and read in full this way:

1. **Commission Implementing Regulation (EU) 2025/2621** of 16 December
   2025 (the CBAM default-value regulation), via `curl` on
   `https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202502621`
   (41,252,987 bytes) → `pdftotext -raw` → 135,102 lines of clean text.
   Confirmed directly from the extracted text: `"COMMISSION IMPLEMENTING
   REGULATION (EU) 2025/2621 of 16 December 2025 ... as regards the
   establishment of default values"`, `ELI:
   http://data.europa.eu/eli/reg_impl/2025/2621/oj`.
2. **JRC134682** ("Greenhouse gas emission intensities of the steel
   fertilisers, aluminium and cement industries in the EU and its main
   trading partners"). The official JRC repository copy
   (`https://publications.jrc.ec.europa.eu/repository/handle/JRC134682`) is
   access-restricted from outside the Commission network ("This document is
   only visible at the Commission level"). A third-party mirror
   (`https://api.pks.rs/storage/assets/JRC134682_01.pdf`, a Serbian
   government trade-information site) was fetched via `curl` (6.1 MB) and
   confirmed genuine from its own extracted text: `"EUR 31653 EN / Vidovic,
   D., Marmier, A., Zore, L., Moya, J. / 2023 / ... / JRC TECHNICAL REPORT /
   ISSN 1831-9424 / PDF ISBN 978-92-68-07370-4 / doi:10.2760/359533 /
   JRC134682"` — matching the DOI and JRC number exactly. `pdftotext -raw` →
   7,429 lines of clean text.
3. **Commission Implementing Regulation (EU) 2026/1412** of 26 June 2026
   (revised EU ETS free-allocation benchmark values), via `curl` (543.7 KB)
   → `pdftotext -raw`. Extracted text confirms the number independently:
   `"COMMISSION IMPLEMENTING REGULATION (EU) 2026/1412 of 26 June 2026
   determining revised benchmark values for free allocation of emission
   allowances for the period from 2026 to 2030 pursuant to Article 10a(2)
   of Directive 2003/87/EC"`, `ELI:
   http://data.europa.eu/eli/reg_impl/2026/1412/oj`.

Two further sources were fetched for the `cbam_factor_year` and
`reference_certificate_price` fields specifically (see those sections
below): Directive 2003/87/EC (consolidated text), and the European
Commission's official CBAM certificate-price page.

---

## Fields resolved (real, cited data — seeded)

### 1. `GoodBenchmarkSeed` — steel CN 7208 benchmark (`benchmark=1.248`)

Commission Implementing Regulation (EU) 2026/1412, Annex "BENCHMARKS",
Section 1 ("Product benchmarks without collection of data on electricity
consumption"). Exact extracted table row (columns: product name; average
value of the 10% most efficient installations in 2021/2022, t CO2eq/t;
benchmark value, allowances/t, for 2026-2030):

```
Hot metal 1,360 1,248
```

**`benchmark=1.248`**, cited as `"Commission Implementing Regulation (EU)
2026/1412, Annex 'BENCHMARKS', Section 1, 'Hot metal' row, benchmark value
(allowances/t) for 2026-2030"`. "Hot metal" is the standard EU ETS proxy
benchmark for primary/integrated steelmaking — there is no separate
benchmark for downstream-rolled products like CN 7208 hot-rolled coil under
the EU ETS system boundaries, matching the brief's own framing
("hot-rolled coil / hot metal benchmark"). Cross-check: an independent
secondary source (cbamguide.com) stated "hot metal falls to 1.248 tCO2e per
tonne" — consistent with the number read directly from the regulation, not
the basis for it.

### 2. `GoodBenchmarkSeed` — aluminium CN 7601 benchmark (`benchmark=1.423`)

Same Annex, same section, "Aluminium" row:

```
Aluminium 1,489 1,423
```

**`benchmark=1.423`**, cited as `"Commission Implementing Regulation (EU)
2026/1412, Annex 'BENCHMARKS', Section 1, 'Aluminium' row, benchmark value
(allowances/t) for 2026-2030"`. This resolves an earlier flagged
uncertainty ("aluminium may be on generic heat/fuel benchmarks rather than
a dedicated product benchmark") — the regulation's own Annex lists a
dedicated "Aluminium" product benchmark, distinct from the Section 3 "Heat
benchmark" (31.2 allowances/TJ) and "Fuel benchmark" (28.1 allowances/TJ)
fallbacks. Cross-check: the same secondary source independently stated
"primary aluminium to 1.423 tCO₂e per tonne" — consistent, not the source.

### 3. `markup_pct` on all 5 `EmissionFactorSeed` records (`markup_pct=0.10`)

Commission Implementing Regulation (EU) 2025/2621, Annex I. Every country's
per-sector table is headed with the applicable markup schedule. Exact
extracted text, repeated identically across every one of the ~170 country
blocks checked (grep count: 48+ occurrences of each), and again in Annex
IV's "Highest default value" fallback table:

```
Iron and steel 10% mark-up 20% mark-up 30% mark-up
Aluminium 10% mark-up 20% mark-up 30% mark-up
```

The three percentages are headers for the "2026 / 2027 / 2028 and onwards"
columns respectively (confirmed against the column headers directly above:
`"2026 Default Value (including mark-up) / 2027 Default Value (including
mark-up) / 2028 and onwards Default Value (including mark-up)"`). This is
sector-wide (steel or aluminium), not country- or route-specific — it
applies to every steel/aluminium good regardless of which country or
production route it comes from.

**`markup_pct=0.10`** on all 5 `EmissionFactorSeed` records (steel
BF-BOF/FR, steel EAF_scrap/FR, steel EAF_DRI/TR, aluminium
primary_electrolysis/NO, aluminium secondary_recycled/TN), matching the
codebase's existing fraction convention (`0.10` = 10%, confirmed against
`machineB/tests/test_calc_engine.py` and `test_tools.py` usage).

---

## Fields still blocked, with evidence (not a fetch failure)

### 4. `direct_ef` for steel BF-BOF/FR and steel EAF_scrap/FR

**SUPERSEDED by the Task 9 addendum below** - the France pairings were
replaced with Türkiye (BF-BOF) and Azerbaijan (EAF_scrap), which do have
real published data. The France-has-no-data finding below is still
historically accurate; it's just no longer the fixture's active state.

**Finding: France is not a country either primary source has data for.**
`grep -n '^France$'` against the full 135,102-line extracted IR 2025/2621
text returned zero matches. A broader search of the whole document for the
literal string `France` returned exactly one hit, and it is unrelated:
`"Harold F., Reetz, Jr. (2016). Fertilizers and their Efficient Use, First
edition, IFA, Paris, France,"` — a bibliography entry, not a country data
row. The same check against JRC134682's 7,429-line extracted text found the
identical result: the only occurrence of "France" is that same "Paris,
France" citation.

This makes sense once the regulations' own scope is read: CBAM default
values exist to determine the embedded emissions of goods *imported into
the EU from third countries*. France is an EU member state; no French
export to the EU is ever a CBAM-covered import, so no CBAM default value
for France exists to find, in this regulation or any other. JRC134682's own
steel scope (section 2.1) lists "16 countries... jointly accounting for
more than 90% of total imports of iron and steel products to the EU" — by
definition non-EU exporters — and France is not, and cannot be, among them.

**Not filled in.** Filling in a number under `country="FR"` from any source
would misrepresent both the source (which has no France entry) and the
real-world scenario (no CBAM declaration will ever need a French default
value).

### 5. `direct_ef` for steel EAF_DRI/TR

**Finding: the DRI/EAF route classification is defined in the regulation's
legend but never actually used for any country, including Turkey.** IR
2025/2621's Annex I (and its copy in Annex IV) define the route indicators:

```
(C) Carbon Steel based on BF/BOF
(D) Carbon Steel based on DRI/EAF
(E) Carbon Steel based on Scrap/EAF
(F) Low alloy Steel based on BF/BOF
(G) Low alloy Steel based on DRI/EAF
(H) Low alloy Steel based on scrap/EAF
(J) High alloy Steel (based on EAF)
(K) primary Aluminium
(L) secondary Aluminium
```

Turkiye's own CN 7208 entry, found within Türkiye's specific country block
(line 108504 onward of the extracted text):

```
7208 Flat-rolled products of iron or non-alloy steel, of a width >= 600 mm,
hot-rolled, not clad, plated or coated
2,428 N/A 2,428 2,670 2,913 3,156 (C)
```

— tagged `(C)` BF/BOF, not `(D)` DRI/EAF. Checking whether Turkiye has
*any* steel CN code tagged `(D)` within its block (lines 108155–109700,
covering its full cement/fertiliser/steel/aluminium sections) found none.
Checking whether *any country in the entire document* has a data row
tagged `(D)` (`grep -cF "(D)"` across all 135,102 lines) returned exactly
**2** — both of them the legend definitions themselves (once in Annex I's
intro, once in Annex IV's), never attached to a single actual default
value. `(G)` (low-alloy DRI/EAF) and `(J)` (high-alloy EAF) show the same
pattern (2 occurrences each, both legend-only). By contrast `(E)` (scrap)
and `(F)`/`(H)` (low-alloy variants) do appear hundreds of times as real
data tags — so this isn't a general extraction problem; specifically the
DRI/EAF-tagged route is absent from every actual default-value row in this
regulation.

JRC134682 was checked as a second, independent source for the same
question. Its own Step 2 methodology text states plainly (section 2.2):
*"Step 3: Determine the specific GHG emission intensity per the CN product
codes covered by the CBAM regulation for each country under the scope, as
well as the production route-based embedded emissions per the CN codes for
the countries out of the scope (referred to as weighted average)."* —
meaning route-decomposed (BF-BOF / EAF-scrap / EAF-DRI) figures exist only
for the generic "weighted average" bucket covering countries *outside* the
named 16-country scope; Türkiye, being one of the 16 named countries
(found in its own country-group table, "Country Switzerland Taiwan Türkiye
Ukraine United Kingdom"), gets one blended per-CN-code value reflecting its
actual production mix, not a labelled "EAF_DRI-route" figure.

**Not filled in.** No clean, route-specific "Turkey, DRI/EAF" figure exists
in either source to quote.

### 6. `direct_ef` for aluminium primary_electrolysis/NO

**SUPERSEDED by the Task 9 addendum below** - the Norway pairing was
replaced with Bahrain, which does have real published data. The
Norway-is-out-of-scope finding below is still historically accurate; it's
just no longer the fixture's active state.

**Finding: Norway is outside CBAM's scope entirely, not merely missing
data.** IR 2025/2621's Annex I has no Norway entry for aluminium (`grep -n
'^Norway$'` returned zero matches; Norway does appear as a named country
for *fertilisers*, e.g. ammonia/urea, at lines 6964+, but not for steel or
aluminium). JRC134682 states the reason directly (section 4.1):

> "Norway and Iceland form part of the EU ETS and are therefore not
> affected by the CBAM. However, they are included in this study due to
> the relevance of their primary aluminium production."

and again later (section 4, discussing scope): *"Norway and Switzerland are
excluded from the scope of the CBAM."* This is a legal/scope fact, not a
data gap: because Norway (as an EEA/EU-ETS participant) already prices
carbon the same way EU producers do, its exports are not CBAM-covered
imports, so no CBAM default value for Norway needs to (or does) exist.

For completeness: JRC134682's own Annex 2 *does* list a Norway row for CN
7601 (found in the country-group table "Country United Arab Emirates
United Kingdom United States Iceland Norway"):

```
7601 Unwrought aluminium 1.95 8.07 10.02 1.95 4.96 6.91 2.34 5.97 8.31 1.76
0.00 1.76 1.84 0.13 1.97
```

(Norway's columns, last of five: Direct 1.84, Indirect 0.13, Total 1.97
tCO2e/t.) This number was **not used** — it is a country-blended value
(JRC134682's own methodology, quoted above, only decomposes by route for
out-of-scope countries; Norway is a *named* country here) from a report
whose own text says Norway isn't in CBAM's scope in the first place.
Labelling it "primary_electrolysis route, Norway" would misrepresent both
what the number is and whether it's needed at all.

**Not filled in.**

### 7. `direct_ef` for aluminium secondary_recycled/TN

**SUPERSEDED by the Task 9 addendum below** - the "Tunisia is absent"
finding below turned out to be wrong (a `grep '^Tunisia$'` anchoring
artifact, not a real data gap); Tunisia does have real published
`secondary_recycled` data and the country pairing was kept, just corrected.
See the Task 9 addendum's "Correction: Tunisia's aluminium data was not
actually absent" section for the real, resolved value.

**Finding: Tunisia is absent from both sources' aluminium tables, and its
regulatory fallback doesn't match the requested route.** JRC134682's
section 4.1 states its aluminium scope is "15 countries with a share of at
least 1% of total imports" to the EU; enumerating every country-group table
found in its Annex 2 (Bahrain, Canada, China, Egypt, India, Kazakhstan,
Mozambique, Russian Federation, South Africa, Türkiye, UAE, UK, US,
Iceland, Norway, Switzerland, plus EU and "Weighted average" aggregates)
confirms Tunisia is not among them — consistent with Table 13 ("CO2
equivalent PFC emission intensity per country"), which also omits Tunisia.
IR 2025/2621's Annex I likewise has no Tunisia entry for steel or aluminium
(`grep` found Tunisia only in the fertiliser and cement sections, and in
Annex II/III's electricity-grid emission-factor tables — used for
*indirect* emissions, which this project's own Global Constraint already
fixes at `0.0` for steel/aluminium and does not need sourced).

IR 2025/2621's Annex I states its own fallback rule explicitly (lines
109–110 of the extracted text): *"Where a country or territory is not
explicitly listed, the default value for the respective good from the
table 'Other Countries and Territories' needs to be selected."* That table
was located (it begins at line 129,794 of the extracted text) and its CN
7601 row read:

```
7601 Unwrought aluminium 2,203 N/A 2,203 2,423 2,643 2,863 (K)
```

— tagged `(K)` primary Aluminium, not `(L)` secondary. Using this figure
under `route="secondary_recycled"` would misattribute a primary-aluminium
fallback value as a secondary/recycled one, which the source itself does
not support.

**Not filled in.**

### 8. `cbam_factor_year` for 2026

**Finding: a real, quotable number exists, but it conflicts in direction
with this codebase's pre-existing convention for the same field, and
resolving that is a formula question, not a data lookup.**

Fetched Directive 2003/87/EC (consolidated text `02003L0087--EN--
01.03.2024`, via `curl` + `pdftotext -raw`, since Regulation (EU) 2023/956's
own Article 31 (also fetched and read in full) only *authorises* an
implementing act to define this value — it doesn't state a number itself —
and that implementing act, Commission Implementing Regulation (EU)
2025/2620 (also fetched), in turn defines the "CBAM factor" only as "the
CBAM factor referred to in Article 10a of Directive 2003/87/EC", tracing
the actual number back one level further). Article 10a(1a) of the
Directive states, in full:

> "1a. Subject to the application of Regulation (EU) 2023/956, no free
> allocation shall be given in relation to the production of goods listed
> in Annex I to that Regulation. By way of derogation from the first
> subparagraph of this paragraph, for the first years of application of
> Regulation (EU) 2023/956, the production of goods listed in Annex I to
> that Regulation shall benefit from free allocation in reduced amounts. A
> factor reducing the free allocation for the production of those goods
> shall be applied (CBAM factor). The CBAM factor shall be equal to 100 %
> for the period between the entry into force of that Regulation and the
> end of 2025 and, subject to the application of provisions referred to in
> Article 36(2), point (b), of that Regulation, shall be equal to 97,5 % in
> 2026, 95 % in 2027, 90 % in 2028, 77,5 % in 2029, 51,5 % in 2030, 39 % in
> 2031, 26,5 % in 2032 and 14 % in 2033. From 2034, no CBAM factor shall
> apply."

So the Directive's own "CBAM factor" for 2026 is **97.5%** — the fraction
of free allocation still *retained* (declining toward 0% by 2034, as free
allocation is phased out).

This codebase's existing, already-committed convention for the same field
name is the opposite number and the opposite direction:
`shared/data/dev_fixtures.py` uses `"cbam_factor_year": 0.025` for 2026;
`docs/PROGRESS.md`'s M2 section documents it as `"phase-out factor (2.5%
2026 -> 100% 2034)"`; the M4 live-infra plan does the same. Tracing this
through the actual formula in
`machineB/addons/cbam/utils/calc_engine.py`:

```python
benchmark_deduction = benchmark * cbam_factor_year * quantity_tonnes
n = max(embedded_emissions_total - benchmark_deduction, 0.0)
```

— plugging in `cbam_factor_year=0.025` for 2026 makes `benchmark_deduction`
tiny, so `n` (certificates owed) comes out close to the *full* embedded
emissions from year one of the mechanism. Plugging in the Directive's own
`0.975` instead would make the deduction large in 2026 (matching that
domestic EU producers still keep 97.5% of their free allocation that year)
and shrink it toward zero by 2034 — matching the "gradual transition" the
regulations themselves describe (Recital 1 of IR 2025/2620: *"To ensure a
gradual transition from the current system of free allowances in the EU
ETS to the CBAM, the CBAM is to be progressively phased in, while free
allowances in sectors covered by the CBAM are to be phased out."*).

Whether the codebase's pre-existing `0.025`-for-2026 convention is itself a
bug (inverted relative to the Directive), or is deliberately defined as
some other derived quantity not directly equal to the Directive's "CBAM
factor", is a formula-direction question outside a data-only task's scope
("only changes data, never the mechanism") — `calc_engine.py` and the
dataclass shapes must not be touched to resolve it. Filling in `0.975`
would contradict every existing fixture, doc comment, and (by implication)
the M4 plan's worked example without anyone having reviewed whether that's
correct; filling in `0.025` would just be re-asserting the same unverified
number a prior session already flagged as "not verified word-for-word
against the primary text" — except now it actually has been checked, and
appears to disagree with the primary text's stated direction.

**Not filled in.** Escalated to the human partner: does `cbam_factor_year`
in `calc_engine.py`'s formula mean the Directive's literal "CBAM factor"
(0.975 for 2026), or something else that happens to share the name?

### 9. `reference_certificate_price` for 2026

**Finding: real, published numbers exist for 2 of 2026's 4 quarters, but
the field's per-year granularity doesn't match how 2026 pricing actually
works.** Fetched the European Commission's official page directly
(`https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en`,
via `curl`, HTML parsed with a small local script since the page is a
modern JS-templated site with heavy boilerplate). The actual "Page
contents" body states:

> "The Commission will calculate the price of CBAM certificates as the
> weighted average of the auction clearing prices of the auctioned EU ETS
> allowances. In 2026, the Commission will calculate and publish four
> quarterly prices, one for each calendar quarter. From 2027 onwards, the
> Commission will calculate and publish weekly prices."

followed by the actual published table:

```
CBAM Certificate price
Quarter of application | Date of publication | Price (€)
Q1 2026 | 7 April 2026   | 75,36
Q2 2026 | 6 July 2026    | 75,28
Q3 2026 | 5 October 2026 | (blank)
Q4 2026 | 4 January 2027 | (blank)
```

As of the research session's date (2026-09-08), Q3 2026 (due 5 October
2026) and Q4 2026 (due 4 January 2027) are genuinely not published yet —
not a fetch failure, they don't exist yet.

`cbam.year.parameter` (per `docs/PROGRESS.md`'s M3 section) holds one
`reference_certificate_price` per year, unique-constrained on `year`. That
one-value-per-year shape cannot represent a mechanism that is explicitly
quarterly for 2026 (and still incomplete for the year) without either (a)
picking one of the two known quarters, (b) averaging them, or (c) waiting
until all four are published — all modelling decisions, not a data lookup.

**Not filled in.** Escalated: should `cbam.year.parameter` for 2026 use
Q1's price, an average of the two published quarters (75.32), a running
value updated as each quarter publishes, or should this model become
quarterly rather than annual for 2026 specifically?

---

## Task 9 addendum (2026-09-08, same day): fixture redesign with real, populated country/route combinations

The human partner reviewed the "Fields still blocked" section above and
decided: redo the fixture design with countries/routes that actually have
real data, rather than continuing to chase France/Norway/Tunisia/Turkey-
EAF_DRI specifically. This addendum records that follow-up work. It
supersedes fields 4, 6, and 7 above (the France and Norway pairings, and
one of the two findings for Tunisia); fields 5 (steel EAF_DRI/TR), 8
(`cbam_factor_year`), and Tunisia's steel-side absence are unchanged and
re-confirmed below.

### Method note: re-fetch, not re-use

The regulation PDF was re-downloaded fresh for this task (not re-used from
a prior session's cache) via the same method as before: `curl` on
`https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202502621`,
then `pdftotext -raw` for extraction. The result was **byte-identical** to
Task 6's copy (41,252,987 bytes downloaded, 135,102 lines extracted) -
confirming this is the same regulation text, not a revised edition, and
ruling out "the source changed since Task 6" as an explanation for any
discrepancy found below.

### Correction: Tunisia's aluminium data was not actually absent

Task 6 stated "Tunisia is absent from both sources' aluminium tables" (see
field 7 above). Re-reading Tunisia's own country block in full for this
task found that statement was wrong. Tunisia has a real country block in
IR 2025/2621's Annex I - extracted-text lines 107001 (first `Tunisia`
page-header occurrence, immediately after "Trinidad and Tobago"'s last
row) through 107583 (the line before "Türkiye"'s block begins at 107584).
Within that block, at line 107460:

```
7601 Unwrought aluminium 0,360 N/A 0,360 0,396 0,432 0,468 (L)
```

- direct default value **0.360** t CO2e/t, indirect N/A, route tag `(L)` =
  "secondary Aluminium" (per the Annex I/IV legend: `"(L) secondary
  Aluminium"`) - matching the `secondary_recycled` route this project
  needs exactly, for the exact country (Tunisia) the original fixture
  guessed at. No substitution needed after all.

**Known gap (see `docs/PROGRESS.md`'s M7 section for the full writeup):**
`GoodBenchmarkSeed` has no route dimension, so the CN 7601 benchmark used
for certificate calculations (1.423, PRIMARY/electrolytic aluminium per its
own source citation) gets applied uniformly to this `secondary_recycled`
record too - even though secondary/recycled aluminium's real emissions
intensity is far lower than primary. Running this record through
`calc_engine.py` at Q=100t computes exactly zero certificates required, for
the same structural reason as the steel EAF_scrap/AZ record above.
Documented inline in `shared/data/seed_emission_factors.py`'s
`GoodBenchmarkSeed` comments; not a bug in this record's `direct_ef` value
itself, and a real fix needs a route dimension added to `GoodBenchmarkSeed`
(out of scope for this plan).

A plausible explanation for the earlier miss: an anchored `grep -n
'^Tunisia$'` search (the same style used to correctly find zero matches for
`^France$` and `^Norway$`) can fail to match a "clean-looking" country
header line if that line's raw bytes carry the same non-ASCII/mis-encoded
character seen on "Türkiye" (rendered as `T�rkiye` by `pdftotext -raw` in
this shell's locale) - `grep -n "Tunisia"` (substring, unanchored) finds
all 11 occurrences of Tunisia's own repeated page header without issue.
This session hit the identical anchored-regex failure while re-verifying
Algeria's block (`grep -n '^Algeria$'` returned nothing; `grep -n
"Algeria"` found it immediately) - same failure mode, different country.

Cross-check: Tunisia's block was also searched for any CN 72xx (steel)
row - none exist. Task 6's other finding about Tunisia (no steel data)
stands; only the aluminium/secondary_recycled finding was wrong.

### Field 4 (steel BF-BOF) resolved: Türkiye replaces France

France is confirmed (unchanged from Task 6, field 4 above) to have no data
in either source - still out of CBAM's scope as an EU member. Rather than
leave `steel/BF-BOF` unfillable, this task looked for a real, non-EU
country IR 2025/2621 does publish CN 7208 BF-BOF data for, and Turkiye
(already in scope for the withdrawn EAF_DRI/TR pairing) turned out to have
exactly that. Türkiye's own country block (extracted-text lines
107584-110671, bounded by the next country header, "Turkmenistan", at
110672), CN 7208 row (line 108507, within the block confirmed by finding
the "Türkiye" page-header at line 108467 immediately preceding it):

```
7208 Flat-rolled products of iron or non-alloy steel, of a width >= 600 mm,
hot-rolled, not clad, plated or coated
2,428 N/A 2,428 2,670 2,913 3,156 (C)
```

- direct default value **2.428** t CO2e/t, indirect N/A, route tag `(C)` =
  "Carbon Steel based on BF/BOF" - matching the `BF-BOF` route exactly.
  (The three markup-inclusive columns, 2.670/2.913/3.156, are 2,428 x
  1.10/1.20/1.30 - internally consistent with the 10%/20%/30% markup
  schedule already verified in field 3 above, a useful sanity check that
  this is a real regulation row and not a transcription error.)

`EmissionFactorSeed(sector="steel", route="BF-BOF", country="TR",
direct_ef=2.428, ...)`.

### Field 4 (steel EAF_scrap) resolved: Azerbaijan replaces France

Same France-is-out-of-scope reasoning as above. Searched broadly for any
country with a CN 7208 row tagged `(E)` ("Carbon Steel based on
Scrap/EAF") - Azerbaijan's own country block (extracted-text lines
10075-13719, bounded by the next country header, "Bahrain", at 13720)
has one, at line 11012:

```
7208 Flat-rolled products of iron or non-alloy steel, of a width >= 600 mm,
hot-rolled, not clad, plated or coated
0,140 N/A 0,140 0,154 0,168 0,182 (E)
```

- direct default value **0.140** t CO2e/t, indirect N/A, route tag `(E)` =
  "Carbon Steel based on Scrap/EAF" - matching the `EAF_scrap` route
  exactly, and the same CN code (7208) used for the BF-BOF/TR record
  above, so the two steel records are a clean apples-to-apples comparison
  of the same product under two different production routes.

`EmissionFactorSeed(sector="steel", route="EAF_scrap", country="AZ",
direct_ef=0.140, ...)`.

**Known gap (see `docs/PROGRESS.md`'s M7 section for the full writeup):**
`GoodBenchmarkSeed` has no route dimension, so the CN 7208 benchmark used
for certificate calculations (1.248, hot-metal BF-BOF per its own source
citation) gets applied uniformly to this `EAF_scrap` record too. Running
this record through `calc_engine.py` at Q=100t computes exactly zero
certificates required - the benchmark deduction, sized for BF-BOF, exceeds
this route's real embedded emissions. Documented inline in
`shared/data/seed_emission_factors.py`'s `GoodBenchmarkSeed` comments; not
a bug in this record's `direct_ef` value itself.

### Field 6 (aluminium primary_electrolysis) resolved: Bahrain replaces Norway

Norway is confirmed (unchanged from Task 6, field 6 above) to be legally
out of CBAM's scope as an EU-ETS member. Bahrain - one of JRC134682's own
named 15-country aluminium scope (section 4.1) and a real-world major
primary-aluminium exporter (Aluminium Bahrain/Alba is one of the world's
largest single-site aluminium smelters) - has a CN 7601 row tagged `(K)`
in its own country block (extracted-text lines 13720-13903, bounded by the
next country header, "Belarus", at 13904):

```
7601 Unwrought aluminium 1,870 N/A 1,870 2,057 2,244 2,431 (K)
```

- direct default value **1.870** t CO2e/t, indirect N/A, route tag `(K)` =
  "primary Aluminium" - matching the `primary_electrolysis` route exactly.

`EmissionFactorSeed(sector="aluminium", route="primary_electrolysis",
country="BH", direct_ef=1.870, ...)`.

Note for anyone re-verifying this: the `(K)`-tagged CN 7601 value is not
uniform across countries (Bahrain's 1.870 differs from, e.g., Türkiye's,
Azerbaijan's, Angola's, and Algeria's, which all independently show 1.700
for the same CN code) - so this is genuinely country-specific data, not a
single global default repeated under every country heading (a possibility
worth ruling out given how often the same numbers recur across different
countries' `(K)`/`(L)` rows).

### Field 5 (steel EAF_DRI) re-confirmed still blocked - not a per-country gap

Re-ran the same exhaustive check Task 6 did, against this task's own
freshly re-fetched (byte-identical) copy of the PDF:

```
$ grep -acF "(D)" ir20252621.txt
2
$ grep -anF "(D)" ir20252621.txt
118:(D) Carbon Steel based on DRI/EAF
133074:(D) Carbon Steel based on DRI/EAF
```

Both occurrences are the legend definitions (Annex I's intro at line 118,
Annex IV's copy at line 133074) - never attached to a single real data row,
for Turkiye or any of the ~170 other countries in the Annex. This
re-confirms Task 6's finding was correct and current: there is no country
anywhere in this regulation with DRI/EAF-route steel data, so - unlike the
France/Norway/Tunisia cases - there is no substitute country to swap in.
`EmissionFactorSeed(sector="steel", route="EAF_DRI", country="TR",
direct_ef=None, ...)` stays a documented placeholder.

### Field 9 (`reference_certificate_price`) resolved: average of published 2026 quarters

Re-fetched the Commission's official price page
(`https://taxation-customs.ec.europa.eu/carbon-border-adjustment-mechanism/price-cbam-certificates_en`)
directly via `curl` for this task (not re-used from Task 6's session) and
read the raw HTML table cells directly (not just the rendered/summarized
text), to rule out a stale cache or a paraphrase:

```
<td ... data-ecl-table-header="Quarter of application">Q1 2026</td>
<td ... data-ecl-table-header="Date of publication">7 April 2026</td>
<td ... data-ecl-table-header="Price (€)">75,36</td>
...
<td ... data-ecl-table-header="Quarter of application">Q2 2026</td>
<td ... data-ecl-table-header="Date of publication">6 July 2026</td>
<td ... data-ecl-table-header="Price (€)">75,28</td>
...
<td ... data-ecl-table-header="Quarter of application">Q3 2026</td>
<td ... data-ecl-table-header="Date of publication">5 October 2026</td>
<td ... data-ecl-table-header="Price (€)">&nbsp;</td>
...
<td ... data-ecl-table-header="Quarter of application">Q4 2026</td>
<td ... data-ecl-table-header="Date of publication">4 January 2027</td>
<td ... data-ecl-table-header="Price (€)">&nbsp;</td>
```

As of this task's session date (2026-09-08), Q3 2026 (due 5 October 2026)
and Q4 2026 (due 4 January 2027) are still genuinely unpublished (empty
`&nbsp;` cells in the source, not a fetch failure) - identical to what
Task 6 found. Only Q1 and Q2 2026 are published, unchanged: **75.36** and
**75.28**.

**Resolution:** rather than leave this blocked pending a modelling
decision, `reference_certificate_price` is now set to the average of the
2 published 2026 quarters: `(75.36 + 75.28) / 2 = 75.32`. The
`source_document` citation on the `YearParameterSeed` record states this
plainly and names the exact quarters and values averaged (`"Average of
2026 Q1 (EUR 75.36, published 7 April 2026) and Q2 (EUR 75.28, published
6 July 2026) CBAM certificate prices, the only 2026 quarters published as
of 2026-09-08..."`) so a future reader sees the approximation, not a bare
number that looks like a single official annual figure. If Q3 and/or Q4
publish later, this average should be recomputed to include them.

### Field 8 (`cbam_factor_year`) - unchanged, out of this task's scope

Task 9's brief explicitly scoped this task to country/route data lookups
(Step 1) and the pricing average (Step 4) - `cbam_factor_year`'s
formula-direction question (see field 8 above) was not part of this
task's Step 1-8 checklist, and resolving it would require judgment about
`calc_engine.py`'s intended formula, which this task's global constraint
explicitly forbids touching (`calc_engine.py` must show zero changes).
Still escalated to the human partner, unchanged from Task 6's finding.

**Note found while working on this task (not acted on - out of scope):**
`git log` shows commit `db50c1f` ("Fix inverted cbam_factor_year direction
in certificate calculation") already on this branch before Task 9 started
- it changed `calc_engine.py`'s formula to `benchmark_deduction = benchmark
* (1 - cbam_factor_year) * quantity_tonnes`, which makes the codebase's
pre-existing `cbam_factor_year=0.025`-for-2026 convention (`shared/data/
dev_fixtures.py`) directionally correct (a low value in early years now
produces a large deduction, matching the Directive's described gradual
phase-in) - the bug was in the formula, not the data. This strongly
suggests `cbam_factor_year` for `YEAR_PARAMETER_SEEDS` should be **0.025**
for 2026 (the complement of the Directive's literal 97.5%), but Task 9's
checklist never included resolving this field, so it was left as `None`
rather than filled in unilaterally. Flagging for whoever picks this up.

### Task 9 outcome summary

Of the 6 fields this task targeted (5 `EmissionFactorSeed.direct_ef`
records + `reference_certificate_price`), **5 were resolved** with real,
cited data (steel BF-BOF/Türkiye, steel EAF_scrap/Azerbaijan, aluminium
primary_electrolysis/Bahrain, aluminium secondary_recycled/Tunisia, and
the 2026 `reference_certificate_price` average). **1 remains genuinely
blocked**: steel EAF_DRI, because no country in either primary source has
DRI/EAF-route steel data at all - not a per-country gap that a different
country could fill. `cbam_factor_year` remains separately blocked,
unchanged and out of this task's scope.

---

## Recommendation for the human partner

The three primary sources (IR 2025/2621, JRC134682, IR 2026/1412) are
genuinely usable — the blockers that remain are not "try again with a
different tool", they're substantive findings:

1. Three of the five original example country/route pairings (France ×2,
   Norway, Tunisia) don't have CBAM default values because of how CBAM's
   own scope works (EU member states and EEA/EU-ETS countries are
   excluded; Tunisia's trade volume falls under a fallback bucket tagged
   with the wrong route). The cleanest fix is likely to swap these example
   records for countries IR 2025/2621 actually lists under the needed
   route (e.g., any DRI/EAF-tagged country for steel — though no such
   country exists in the regulation at all — and any `(L)`-tagged country
   for secondary aluminium), rather than continuing to chase data for
   country/route combinations that structurally don't exist.
2. `cbam_factor_year`'s sign/direction needs a decision from whoever
   understands `calc_engine.py`'s intended formula best.
3. `reference_certificate_price` needs a decision on how a genuinely
   quarterly (and still-incomplete) 2026 figure maps onto a
   one-value-per-year model.

**Status update (Task 9, see the addendum above):** recommendation 1 is
now acted on - the human partner made exactly that call, and Task 9 found
real IR 2025/2621 data for 4 of the 5 pairings this recommendation named
(France x2, Norway; Tunisia turned out to need no swap at all, just a
corrected re-read). The one genuine structural gap the recommendation
flagged - "no DRI/EAF-tagged country exists in the regulation at all" -
was re-confirmed exactly as stated, so steel EAF_DRI remains unfilled.
Recommendation 3 is also now acted on: `reference_certificate_price` is
filled in as the average of the two published 2026 quarters (see the
addendum's Field 9 section) rather than left for a modelling decision.

**Status update (Task 11):** Recommendation 2 (`cbam_factor_year`) is now
also acted on - see the "Task 11 addendum" section below. All three
original recommendations are resolved; only steel EAF_DRI's `direct_ef`
remains genuinely blocked (structurally absent from the source, not a
decision to make).

## Task 11 addendum: `cbam_factor_year` resolved

Task 9's addendum (Field 8 section, above) already surfaced the piece that
closes this gap: commit `db50c1f` ("Fix inverted cbam_factor_year direction
in certificate calculation"), already on this branch before Task 9 ran,
changed `calc_engine.py`'s formula from `benchmark * cbam_factor_year *
quantity_tonnes` to `benchmark * (1 - cbam_factor_year) * quantity_tonnes`.
That fix makes this codebase's pre-existing `cbam_factor_year=0.025`-for-
2026 convention (`shared/data/dev_fixtures.py`) directionally correct again
- it's the complement of the Directive's own "CBAM factor" (the fraction of
free allocation *retained*), and a low early-year value now correctly
produces a *large* certificate deduction, matching the gradual free-
allocation phase-in Directive 2003/87/EC and IR 2025/2620 both describe.

Re-confirmed for this task (not a fresh investigation - re-checking
already-found material per the task brief):

- **Primary-source citation** (unchanged from Task 9's find, re-quoted from
  Directive 2003/87/EC Art. 10a(1a), consolidated text
  `02003L0087--EN--01.03.2024`): *"...shall be equal to 97,5 % in 2026, 95 %
  in 2027, 90 % in 2028, 77,5 % in 2029, 51,5 % in 2030, 39 % in 2031, 26,5 %
  in 2032 and 14 % in 2033. From 2034, no CBAM factor shall apply."* -
  97.5% for 2026, confirmed exact.
- **Independent re-confirmation:** a fresh `WebSearch` for this task
  (`Article 10a(1a) Directive 2003/87/EC CBAM factor "97,5 %" 2026`)
  returned the same figure and full percentage sequence from independent
  secondary sources (e.g. cbamguide.com's free-allocation phase-out page),
  consistent with the primary text quoted above and with Task 9's original
  fetch.
- **Current formula, re-checked directly in `calc_engine.py`** (read-only -
  this task does not touch that file): line 136 reads
  `benchmark_deduction = benchmark * (1 - cbam_factor_year) * quantity_tonnes`,
  confirming commit `db50c1f`'s fix is still in place and `0.025` is the
  directionally-correct value for the `cbam_factor_year` field's actual
  usage.

**Resolution:** `YEAR_PARAMETER_SEEDS`'s 2026 record now sets
`cbam_factor_year=0.025` (the complement of the Directive's literal 97.5%
figure, matching `calc_engine.py`'s `(1 - cbam_factor_year)` formula and
every other pre-existing convention in the codebase - `dev_fixtures.py`,
`docs/PROGRESS.md`'s M2 section, the M4 plan). The record's
`source_document` now cites both fields' sources directly rather than
carrying "unresolved"/"BLOCKED" language.

This closes the last field in scope for this plan: **9 of 10** tracked M7
fields are now real, cited values. The 10th (steel EAF_DRI's `direct_ef`)
stays genuinely blocked - not a decision to make, but a structural absence
in the only primary sources CBAM defines default values from (re-confirmed
independently by both Task 6 and Task 9: the "(D)" DRI/EAF route indicator
is defined in IR 2025/2621's legend but attached to zero data rows for any
country in the entire regulation).
