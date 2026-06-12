# RFP Opportunity Linkage Implementation

## Purpose

This note documents the Week 6 implementation that links the historical
proposal/RFP corpus to CRM opportunity metadata using CGI's new opps1 alias
field.

The previous Week 5 limitation was that retrieved proposal chunks could not be
reliably tied to a CRM opportunity or director. Retrieved examples were
therefore semantic evidence only. The new `Json S-Num` field in
`anonymized_opps_1.xlsx` provides a deterministic bridge from proposal JSON
titles to CRM opportunity rows.

## Data Inputs

Local inputs:

```text
data/csv_files/anonymized_opps_1.xlsx
data/csv_files/anonymized_opps_2.xlsx
data/proposals_responses.json
```

The new opps1 workbook contains `Json S-Num`, which is preserved by the
opportunity cleaner as:

```text
json_s_num
rfp_alias
has_rfp_alias
```

The proposal JSON titles begin with the same S-number, for example:

```text
18. 105668 SY - RFP for Cybersecurity Operations and Services
```

This allows `rfp_alias = 18` to map the proposal corpus entry to the CRM
opportunity row with `json_s_num = 18`.

## Local Artifacts

After replacing the local opps1 workbook, regenerate opportunity outputs:

```bash
python -m src.opportunity_cleaner
```

This command generates:

```text
data/processed/opportunity_df.csv
data/processed/cleaned_opportunity_df.csv
```

The proposal-to-opportunity crosswalk is supported by
`write_rfp_opportunity_linkage()` and can be written from Python after
`cleaned_opportunity_df.csv` exists:

```python
import json
from src.rfp_preprocessor import write_rfp_opportunity_linkage

with open("data/proposals_responses.json", encoding="utf-8") as handle:
    proposals = json.load(handle)

write_rfp_opportunity_linkage(proposals)
```

That writes:

```text
data/processed/rfp_opportunity_linkage.csv
```

The crosswalk artifact has one row per proposal JSON entry and includes:

```text
proposal_id
proposal_title
rfp_alias
json_s_num
opportunity_id
opportunity_owner
opportunity_manager
service_solution
status
status_reason
opportunity_outcome
```

Current local result:

```text
Linked proposal entries: 19
Linked proposal chunks: 1,216
Linked owners: 5
Linked outcomes: open, won, lost
```

## Implementation

### Opportunity Preprocessing

`src/opportunity_cleaner.py` now keeps `json_s_num` as an opps1 supplemental
field. `clean_opportunity_df()` exposes `rfp_alias` and `has_rfp_alias` for
downstream linkage.

This preserves the existing opps2-base merge strategy and does not alter
capacity scoring by itself.

### Proposal Crosswalk

`src/rfp_preprocessor.py` now builds a deterministic proposal-to-opportunity
crosswalk:

```text
proposal title S-number -> cleaned_opportunity_df.rfp_alias
```

Main helpers:

```text
build_rfp_opportunity_linkage()
write_rfp_opportunity_linkage()
```

`preprocess_proposals()` attaches linked CRM metadata to proposal and response
documents before chunking. Each retrieved chunk can therefore carry opportunity
and owner metadata when linkage is available.

### Retrieval Metadata

`src/vector_store.py` now preserves linkage metadata when converting chunks to
dashboard-facing `retrieved_examples`.

Preserved fields include:

```text
rfp_alias
json_s_num
opportunity_id
opportunity_owner
opportunity_manager
service_solution
status
status_reason
opportunity_outcome
```

This applies to both local fallback retrieval and Chroma result normalization,
provided the Chroma index was built after the metadata enrichment change.

### RFP Assignment Logic

`src/rfp_engine.py` now distinguishes:

- corpus-level linkage availability
- retrieved-example linkage availability
- linked won opportunities
- linked non-won opportunities

Director ranking includes a small structured linkage signal when retrieved
examples map to the same director. Won linked examples receive stronger
treatment than open/lost linked examples.

Important caveat:

```text
Open or lost linked opportunities are historical context, not proof of
successful prior delivery.
```

### Streamlit Display

`app/app.py` now shows linked CRM metadata under retrieved supporting examples
when available:

```text
CRM opportunity
Opportunity owner
Outcome
```

The old blanket missing-linkage caveat is still shown when retrieved examples
lack owner/opportunity linkage. When linkage exists, the UI says linked
examples come through CGI's RFP alias and keeps the non-won caveat visible.

## Wording Changes

The RFP page wording changed only where needed to reflect the new conditional
linkage state.

When retrieved examples do not have opportunity/director linkage, the existing
missing-linkage caveat remains:

```text
Retrieved chunks cannot currently be tied reliably to a specific director or
opportunity. Treat them as semantic similarity evidence, not proof of prior
director experience.
```

When retrieved examples do have CRM linkage through the alias, the page now
shows:

```text
Some retrieved examples are linked to CRM opportunities through CGI's RFP alias.
Non-won linked opportunities are historical context, not proof of successful
prior delivery. Linked opportunity owner reflects CRM ownership/context, not
proof of personal delivery experience.
```

Retrieved supporting examples can now display these additional labels when
metadata is available:

```text
CRM opportunity
Opportunity owner
Outcome
```

The recommendation explanation wording can also mention linked evidence. For
won linked examples owned by the recommended director, it may say:

```text
retrieved linked example(s) map to this director and won CRM opportunities
```

For linked examples owned by the director but not classified as won, it may say:

```text
retrieved linked example(s) map to this director, but the linked opportunities
are not classified as won
```

No major page title or section label was changed. The main wording change is
that linkage caveats are now conditional instead of always saying retrieved
examples cannot be tied to directors or opportunities.

## Validation

Commands run:

```bash
python -m src.opportunity_cleaner
python -m pytest
```

Final test result:

```text
157 passed, 1 skipped, 3 warnings
```

Additional smoke check:

```text
preprocess_proposals(data/proposals_responses.json)
generated 1,216 chunks
1,216 chunks had opportunity linkage
```

## Remaining Limitations

The linkage improves proposal-to-CRM traceability, but it is not a final
assignment model.

Remaining caveats:

- Linked `opportunity_owner` means CRM opportunity ownership, not necessarily
  every person who wrote or delivered the proposal.
- Open and lost linked opportunities should not be counted as successful
  historical delivery evidence.
- Recommendation weights are still heuristic and need CGI calibration.
- Existing persisted Chroma indexes must be rebuilt before Azure/Chroma
  retrieval can return the new linkage metadata.

Azure embedding configuration was unavailable in the local shell used for this
implementation, so the persistent Chroma index was not rebuilt there. Rebuild in
an Azure-configured environment with:

```bash
python scripts/build_rfp_chroma_index.py
```
