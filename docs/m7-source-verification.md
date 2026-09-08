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

**Overall outcome:** 3 of 9 fields fully verified and seeded from clean
primary text; 6 explained-and-blocked with documented, evidence-based
reasons (not fetch failures — the sources were reachable and readable,
but the specific data point requested does not exist, or filling it in
requires a judgment call outside a data-only task's scope).

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
