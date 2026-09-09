# CBAM Carbon Footprint Formulas

## Iron & Steel and Aluminium Sectors — Reference Sheet

*Compiled for academic/study use — July 2026*

---

## 0. Scope and legal basis

The Carbon Border Adjustment Mechanism (CBAM) charges importers of certain carbon-intensive goods into the EU for the greenhouse gas emissions embedded in those goods. Iron & steel and aluminium are two of the six covered sectors (with cement, fertilisers, hydrogen and electricity). This sheet covers only the emissions-calculation formulas (the "carbon footprint" side) — not customs/reporting procedure.

Legal basis:

- Regulation (EU) 2023/956 — the CBAM framework regulation (definitions, scope, Annex I goods list, Annex II "direct-emissions-only" sectors, certificate formula in Art. 9/31).
- Implementing Regulation (EU) 2023/1773 — transitional-period reporting methodology (Annex III: calculation rules, system boundaries, equations).
- Implementing Regulation (EU) 2025/2547 — definitive-period calculation methodology (applies from 1 Jan 2026 imports).
- Implementing Regulation (EU) 2025/2620 / 2025/2621 — free-allocation adjustment method and default values for the definitive period.
- Underlying monitoring methodology is the same as the EU ETS Monitoring & Reporting Regulation, Commission Implementing Regulation (EU) 2018/2066 (fuel/mass-balance calculation methods, and Annex IV for the aluminium PFC methods).

> **Important:** web access to the official EUR-Lex and European Commission PDF texts was blocked in the research session that produced this sheet, so exact article/equation numbers below could not be re-verified word-for-word against the primary legal text. The formulas themselves are cross-checked across multiple independent technical/consultancy sources describing the same official methodology (see Sources, section 5) and are standard, well-established industry methods (IPCC / EU ETS MRR). Before using this for a real compliance filing, open the regulation links in section 5 yourself and check the live article numbers, since implementing acts get amended.

---

## 1. General CBAM formulas (apply to every sector)

### 1.1 Total embedded emissions of an import

```
Embedded Emissions_total = Σg ( Qg × SEEg )
```

| Variable | Meaning |
|---|---|
| Qg | Quantity of good g imported in the reporting period (tonnes) |
| SEEg | Specific Embedded Emissions of good g (t CO2e per tonne of product) |

### 1.2 Specific Embedded Emissions (SEE) of a good

```
SEEg = SEE(direct,g) + SEE(indirect,g)
```

For iron & steel and aluminium, both goods are listed in Annex II of Regulation (EU) 2023/956, meaning only direct emissions are priced under CBAM:

```
SEEg = SEE(direct,g)      [indirect/electricity term = 0 for steel & aluminium]
```

*Cement and fertilisers are the sectors where indirect (electricity) emissions are also priced. For steel and aluminium, electricity consumption is tracked for reporting/statistics but is currently not charged.*

### 1.3 Direct emissions of a source stream — calculation-based (Standard) method

```
Ei = ADi × EFi × OFi     (fuels / combustion)
Ei = ADi × EFi × CFi     (process materials, non-combustion)
```

| Variable | Meaning |
|---|---|
| ADi | Activity data: quantity of fuel or material i consumed (t, Nm³, or GJ) |
| EFi | Emission factor of fuel/material i (t CO2 per t, per Nm³, or per GJ) |
| OFi | Oxidation factor (fraction of carbon actually oxidised in combustion, ≈0.98–1) |
| CFi | Conversion factor (fraction of carbon converted to CO2 in a process reaction) |

### 1.4 Direct emissions — Mass-balance method (used for multi-input processes, common in steel)

```
E(CO2) = [ Σ(Minput × wC,input) − Σ(Moutput × wC,output) ] × 44/12
```

| Variable | Meaning |
|---|---|
| Minput / Moutput | Mass of each material flowing into / out of the process (t) |
| wC | Carbon content of that material (fraction, t C / t material) |
| 44/12 | Molar mass ratio converting mass of carbon to mass of CO2 |

### 1.5 Specific embedded emissions of an installation's own good

```
SEE(direct,g) = AEEg / ALg
```

| Variable | Meaning |
|---|---|
| AEEg | Attributed direct emissions of good g in the reporting period (t CO2e) — the share of the installation's total measured emissions assigned to g |
| ALg | Activity level: quantity of good g actually produced in the reporting period (t) |

### 1.6 Complex / downstream goods (embedded emissions of precursors carry through)

```
SEE(good) = SEE(own process) + Σp ( SEE(precursor p) × ratio_p )
```

| Variable | Meaning |
|---|---|
| SEE(own process) | Direct emissions from the good's own final production step only (e.g. rolling, drawing, extrusion, casting) |
| SEE(precursor p) | Specific embedded emissions already carried by precursor material p (e.g. crude steel, primary aluminium, alloy) |
| ratio_p | Tonnes of precursor p consumed per tonne of final good produced (accounts for process yield / scrap losses) |

*This is the mechanism by which emissions accumulate down the value chain: a finished steel bar "inherits" the footprint of the crude steel, which inherits the footprint of the pig iron/DRI, which inherits the footprint of sintered ore, etc.*

---

## 2. Iron & Steel sector

Steel production is split into aggregated goods categories (system boundaries defined in Annex I): sintered/pelletised ore, pig iron, ferro-manganese, ferro-chrome, ferro-nickel, DRI (direct reduced iron), crude steel, and downstream finished products (bars, rebar, wire rod, plates, coils, tubes, etc.). Only direct emissions count (section 1.2).

### 2.1 Sinter/pellet plant

```
E = Σ(AD(coke breeze, fuel gas) × EF × OF) + E(carbonate calcination, mass balance)
```

*Process emissions come mainly from combustion of coke breeze/fuel gas plus calcination of limestone/dolomite flux, calculated with the mass-balance formula (1.4).*

### 2.2 Blast furnace — pig iron

```
E = Σ(AD(coke, PCI coal, other reductants) × EF × OF) + E(ore reduction, mass balance)
```

*Applies formula 1.3 to purchased/combusted fuels and formula 1.4 (carbon in coke/coal/ore vs. carbon out in hot metal + blast-furnace gas + slag) for the reduction chemistry.*

### 2.3 Basic Oxygen Furnace (BOF) — crude steel from hot metal + scrap

```
E(CO2) = [ (M_hotmetal×wC,hm + M_scrap×wC,scrap + M_flux×wC,flux) − M_steel×wC,steel ] × 44/12
```

*Pure mass-balance process: carbon-rich hot metal (~4.3% C) is decarburised to steel (~0.05–1% C); the carbon difference leaves as BOF gas/CO2.*

### 2.4 Electric Arc Furnace (EAF) — crude steel from scrap/DRI

```
E(CO2) = [ Σ(Mcarbon inputs × wC) − M_steel×wC,steel ] × 44/12  +  Σ(AD_nat.gas/electrode × EF × OF)
```

*Main direct-emission sources: graphite electrode consumption, injected carbon/natural gas for foaming slag, and carbon in scrap/DRI vs. carbon in steel output. Electricity used to melt the charge is an indirect emission and — per section 1.2 — is not priced for steel.*

### 2.5 Direct Reduced Iron (DRI)

```
E = AD(natural gas or syngas) × EF × OF   (combustion + reduction reaction, gas-based route)
```

### 2.6 Downstream finished steel products

```
SEE(finished product) = SEE(crude steel) × ratio(crude steel/product) + SEE(own process, e.g. rolling)
```

*ratio(crude steel/product) is the yield factor: tonnes of crude steel needed per tonne of finished product, which is >1 because of scale/trim losses.*

---

## 3. Aluminium sector

Aluminium is also Annex II (direct emissions only), but unlike steel it additionally involves perfluorocarbon (PFC) gases (CF4, C2F6) from the electrolysis process, which must be converted to CO2-equivalent using GWP factors.

### 3.1 Primary aluminium — CO2 from anode consumption

**(a) Simple/default method**

```
E(CO2) = EF_technology × Production(Al)
```

*EF_technology is a default factor (t CO2 / t Al) that depends on the cell technology: prebake, Søderberg vertical-stud (VSS) or horizontal-stud (HSS).*

**(b) Mass-balance / net carbon consumption method (more accurate, plant-specific)**

```
E(CO2) = Production(Al) × NCC × 44/12
```

| Variable | Meaning |
|---|---|
| Production(Al) | Tonnes of primary aluminium produced in the period |
| NCC | Net Carbon Consumption: net mass of anode carbon actually oxidised to CO2 per tonne of Al produced (t C / t Al), i.e. gross anode consumption minus recovered butts/ash and non-oxidised carbon |

### 3.2 Primary aluminium — PFC emissions (CF4 and C2F6 from anode effects)

**Tier 2 — Slope method**

```
E(CF4)  [kg/t Al] = S(CF4) × AEM
E(C2F6) [kg/t Al] = E(CF4) × F(C2F6/CF4)
```

| Variable | Meaning |
|---|---|
| S(CF4) | Slope coefficient, measured per smelter/technology — (kg CF4 / t Al) per (anode-effect-minute / cell-day) |
| AEM | Anode Effect Minutes per cell-day = frequency of anode effects × average duration (minutes/cell-day) |
| F(C2F6/CF4) | Technology-specific mass ratio of C2F6 to CF4 generated (typically ~0.1 for center-worked prebake cells) |

**Tier 3 — Overvoltage method**

```
E(CF4) [kg/t Al] = K × AEO / CE
```

| Variable | Meaning |
|---|---|
| K | Overvoltage coefficient, technology-specific (kg CF4 / t Al per mV of anode-effect overvoltage) |
| AEO | Anode Effect Overvoltage — average excess cell voltage during anode effects × frequency (mV/cell-day) |
| CE | Current efficiency of the cell (fraction, typically ~0.90–0.96) |

**Converting PFC mass to CO2-equivalent**

```
CO2e(PFC) = [ E(CF4)×Production(Al) ] × GWP(CF4)  +  [ E(C2F6)×Production(Al) ] × GWP(C2F6)
```

| Variable | Meaning |
|---|---|
| GWP(CF4) | 100-yr Global Warming Potential of CF4 = 6,630 (IPCC AR5) |
| GWP(C2F6) | 100-yr Global Warming Potential of C2F6 = 11,100 (IPCC AR5) |

*Total direct SEE of primary aluminium = [E(CO2) from 3.1 + CO2e(PFC) from 3.2] ÷ Production(Al).*

### 3.3 Secondary (recycled) aluminium

```
E(CO2) = Σ(AD(remelt furnace fuel) × EF × OF)
```

*No electrolysis and no anode ⇒ no PFCs and no anode-CO2 term. Emissions come only from combustion in the remelting/holding furnace, which is why recycled aluminium's footprint is typically far lower per tonne than primary aluminium (order of magnitude difference — treat exact benchmark numbers as indicative defaults published by the Commission, not fixed constants).*

### 3.4 Downstream aluminium products (alloys, extrusions, rolled/cast products)

```
SEE(product) = SEE(primary or secondary Al input) × ratio(input/product) + SEE(own process, e.g. casting/extrusion/rolling)
```

---

## 4. From footprint to CBAM certificates (context)

Once SEE is known, the number of CBAM certificates an importer must surrender follows Regulation (EU) 2023/956, Art. 9 and 31:

```
N       = [ SEEg − (Benchmarkg × CBAMFactor_year) ] × Qg
N_final = N × (1 − Carbon Price Adjustment)
```

| Variable | Meaning |
|---|---|
| Benchmarkg | EU ETS free-allocation benchmark for good g (t CO2e/t) — reflects what an efficient EU producer would emit |
| CBAMFactor_year | Phase-out factor of free allocation: 2.5% (2026) → 5% (2027) → 10% (2028) → … → 100% (2034) |
| Carbon Price Adjustment | Deduction for a verified carbon price already effectively paid in the country of production |

*This section is included for context only — the core request was the emissions/footprint formulas in sections 1–3, which feed directly into this certificate calculation.*

**Correction (added post-implementation, do not "fix" `calc_engine.py` to match the formula above):**
`softworker/addons/cbam/utils/calc_engine.py`'s actual implementation deducts
`benchmark × (1 - CBAMFactor_year)`, not `benchmark × CBAMFactor_year` as
written above. The benchmark deduction represents the free allocation an
installation still *retains* for the year — the complement of the phase-out
figure — not the phase-out figure itself; using `CBAMFactor_year` directly
inverts the deduction's direction. A sign-inversion bug matching this exact
formula was found and fixed on the `worktree-project-completion` branch
(commit `db50c1f`). See `calc_engine.py`'s own docstring for the
authoritative version and derivation.

---

## 5. Sources

**Primary legal texts** (open these directly to check current article/equation numbering — they could not be fetched live in the research session):

- Regulation (EU) 2023/956 (CBAM framework): https://eur-lex.europa.eu/eli/reg/2023/956/oj
- Implementing Regulation (EU) 2023/1773 (transitional-period methodology, Annex III): https://eur-lex.europa.eu/eli/reg_impl/2023/1773/oj
- Implementing Regulation (EU) 2025/2547 (definitive-period calculation methodology): search EUR-Lex CELEX 32025R2547
- Implementing Regulation (EU) 2025/2620 (free-allocation adjustment) / 2025/2621 (default values): search EUR-Lex CELEX 32025R2620 / 32025R2621
- EU ETS Monitoring & Reporting Regulation (EU) 2018/2066, Annex IV (fuel/mass-balance and aluminium PFC methods): https://www.legislation.gov.uk/eur/2018/2066/annex/IV
- IPCC Good Practice Guidance — PFC Emissions from Primary Aluminium Production: https://www.ipcc-nggip.iges.or.jp/public/gp/bgp/3_3_PFC_Primary_Aluminium_Production.pdf

**Secondary sources** used to cross-check and phrase the formulas (consultancy/industry explainers of the same official methodology):

- European Commission, Taxation and Customs Union — CBAM Guidance for installation operators: taxation-customs.ec.europa.eu
- CBAM Guide — Embedded Emissions Step-by-Step Calculation Guide 2026: cbamguide.com/compliance/embedded-emissions
- GTG Consulting — Mass Balance Method in CBAM (steel): gtgcons.com
- CarbonChain Help Center — Preparing CBAM data for Crude Steel, DRI, Pig Iron, Sinter: learn.carbonchain.io
- Decerna — CBAM Aluminium Calculator (primary vs secondary): decerna.co.uk
- International Aluminium Institute — Aluminium Sector Greenhouse Gas Protocol: ghgprotocol.org
- carboneer — CBAM definitive period: key regulatory updates and scope extension: carboneer.earth
