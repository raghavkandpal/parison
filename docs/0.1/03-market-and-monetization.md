# Parison market and monetization research

## Conclusion

There is observable supply for data comparison and validation, but no evidence yet of unmet demand for Parison. The presence of existing products establishes a category; it does not establish a market gap, willingness to pay or a large addressable market.

Start globally with developers who can install a local Python tool. India can be a convenient discovery market, not an imposed product limitation. Avoid industry-specific branding and do not infer demand from the founder's employer.

## Segment hypotheses

| Segment | Trigger | Potential benefit | Main obstacle |
| --- | --- | --- | --- |
| Individual data engineers | Refactor or parser rewrite | Less repeated comparison code and easier investigation | Free tools and generated scripts are often adequate |
| Small data teams | Repeated release validation | Consistent recipes and evidence across engineers | Another configuration format and tool to maintain |
| Independent migration consultants | Multiple client engagements | Portable, local evidence without central uploads | Episodic demand and varied client environments |
| Analytics engineers | SQL/dbt change | Paired-output evidence beyond selected checks | Strong incumbent workflow and warehouse access needs |
| Enterprise platform teams | Standardizing many comparisons | Policy and centralized run metadata | Procurement, support and security burden too large initially |

Prioritize the first two for usefulness testing. Consultants may be a good paid-desktop hypothesis, but repeated projects and buying behavior must be established independently.

## Public commercial signals

Datafold's pricing path redirected toward contact rather than providing a usable numerical price in the fetched page. No price is quoted here. JuxtAPPose's public pricing text describes a free tier and a single-payment perpetual Standard license; numerical prices were not exposed in the fetched text and require direct verification. Great Expectations lists a free Developer option and Team/Enterprise upgrades without numerical amounts in the accessible page. [Datafold pricing path](https://www.datafold.com/pricing/), [JuxtAPPose pricing](https://www.juxtappose.com/pricing), [GX pricing](https://greatexpectations.io/pricing/).

These signals suggest multiple viable packaging models exist in the category; they do not indicate which model suits Parison. Do not invent competitor seat prices or use the absence of a fetched price to claim a vendor is expensive.

## Market sizing method

Do not use total data-engineer employment or the entire data-quality-software market as Parison's TAM. Relevant buyers need recurring paired-output validation, an adoption-compatible environment and a reason to prefer Parison over substitutes.

An eventual bottom-up model should be: reachable qualifying teams × observed purchase conversion × realized annual revenue per team. Keep active individual users, purchasing accounts and seats separate. Collect evidence for each multiplier before publishing a market-size claim.

For perspective only: 100 paying users at USD 10/month would produce USD 1,000 monthly gross revenue; 100 team accounts at USD 49/month would produce USD 4,900. Neither scenario is a forecast. Conversion, retention, acquisition and support costs may make either unattainable.

## Packaging experiments

**Implemented foundation:** a free local runner and portable report under the MIT License. The CLI, result schema and correctness tests are inspectable; trust and adoption matter more than restricting basic comparison.

**Potential paid local workbench:** saved investigation views, local run history, batch organization and convenient recipe editing. Test an annual license rather than assuming a perpetual license funds ongoing support. Free evidence must remain useful; do not make reproducibility or accurate comparisons a premium feature.

**Potential paid team control plane:** shared recipe versions, reviewer annotations and metadata history. Data execution stays on customer-controlled runners. Even metadata can be sensitive; this is a separate security architecture, not a free extension of local mode.

**Supported deployment:** only after recurring demand. A solo founder should not promise 24/7 production coverage or implement bespoke connectors for every customer.

## Price and cost experiment

Illustrative experiments: USD 79/year for a local workbench, or USD 49/team/month for a small metadata service. These are test offers, not recommendations supported by measured willingness to pay. Regional discounts and taxes would need separate consideration.

At a hypothetical USD 49/team/month, allocate USD 5 infrastructure, USD 2 billing and USD 20 support labor: contribution is USD 22, or 44.9%, before development, acquisition, tax and general overhead. If support rises to USD 60, contribution becomes negative USD 18. Labor is explicitly a cost even if the founder does not initially pay themselves.

Local execution reduces hosted compute costs, but not packaging, security updates, documentation or troubleshooting. Avoid per-row billing initially: it can discourage full comparisons and creates an awkward incentive to sample. Dataset size can instead define tested support envelopes, not artificial correctness limits.

## Distribution

Publish a synthetic “refactor went wrong” demo, an installable CLI and a report that can be opened without an account. Write practical articles about ambiguous keys, decimal changes and equal totals hiding row differences. Reach independent engineers through relevant communities and explicit opt-in demonstrations; do not scrape contacts or message people without authorization.

Use Git-managed recipes and straightforward shell integration as the first distribution surface. A marketplace integration is useful only after developers repeatedly run the tool. Package downloads and repository stars are weak signals; a second unassisted comparison and sustained CI use are stronger.

## Discovery questions

Ask 12–15 independent engineers about their last real comparison: what changed, file sizes/formats, setup time, investigation steps, current library, data-transfer restrictions and recurrence. Ask them to demonstrate a sanitized or synthetic equivalent, not upload confidential data.

Recruit 5–8 for a task-based comparison against their current method. Measure correct diagnosis and total effort before asking whether they like the interface. Then offer a concrete paid prototype or collect a clear reason not to buy. Free signups are not purchasing evidence.

## Survival criteria

Proceed commercially only if there is repeated use, measurable workflow improvement and a paid capability users actually need. Keep it an open-source side project if it is useful but does not support a business. Stop or contribute upstream if differentiation remains a thin wrapper that users can reproduce more cheaply.
