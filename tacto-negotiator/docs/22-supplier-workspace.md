# Harvey supplier workspace

Open `/workspace` on the existing lab host and sign in with the same team password.
The experiment lab links to it in its sidebar. This is a human-facing, read-only view;
it does not start sessions, call a model, send supplier messages or promote policy.

## Included

- Overview with simulated cost reduction, supplier/session counts, marked-running
  sessions, historical failures and overdue uploads, and recent activity.
- Searchable supplier directory, separated by environment and arena identity.
- Supplier pages with selectable historical negotiations, polling conversations,
  first/latest supplier sheets versus final selected terms, complete outcome cost,
  recorded must-have status, version-scoped memory, recorded configuration and
  source-backed feedback suggestions. Missing records are explicitly labeled.
- The UI checks uploads every five seconds while visible. It does not establish a
  direct streaming connection to the Arena. Current tracked runners primarily attach
  conversations after attempt completion; per-message streaming requires runner telemetry. Source timestamps and overdue uploads
  remain visible; loss of the lab connection retains the last view and shows an error.
- Authentication is the existing read cookie or bearer token. All supplier content
  is rendered as text. Logout clears rendered supplier evidence; late requests
  cannot repopulate it. Existing CSP applies to the new static assets.

## Metric definitions

Savings are `c_open - c_deal`, using the latest recorded session for each arena/case
in the selected environment. Eligibility requires an original completed and ended
session, a deal, satisfied must-haves, a selected supplier, finite recorded costs,
and positive opening cost. Cost increases remain negative. The coverage count and
baseline description accompany the metric. A newer failure does not cause fallback
to an older success. This is a latest-case snapshot, not a sum over experiments or
realized business savings. In RFQs, opening cost can represent another supplier.

Canonical arena/session records deduplicate campaigns, tracked runs and imported
history in that priority order. A case score or cost is attributed only to the
selected supplier. Conversation participation alone never earns the case outcome.

## Evidence boundaries and remaining work

Supplier memory shows observations for the selected case, arena, environment and
known data version. It is a human history view, potentially including observations
from later sessions. Matching supplied facts retain their original dates, validity
and sources. Neither implies that the runtime consumed those records. Unknown data
versions do not match one another. Up to 100 facts and 100 observations are shown
with total counts; the full existing lab memory view remains available.

The approach tab shows saved configuration, not a claim about the currently deployed
agent. Next steps are descriptive saved feedback or explicit review guidance, not
an invented agent plan. Editing policies, pausing agents, approved-lesson management,
per-decision retrieval traces and detailed requirement thresholds need additional
runtime/API contracts and are not controls in this release. Campaigns only upload
available outcome evidence; this interface cannot invent in-progress conversations.

## Verification

Run the repository's full pytest suite and Ruff before publishing. The deployment
workflow checks both `test_lab_server.py` and `test_lab_workspace.py`. New regressions
cover eligibility/negative savings, repeated-case accounting, latest failures,
authentication, immutable originals, losing suppliers, memory isolation and campaign
versus import deduplication. Browser verification covers login, search, all four tabs,
negotiation switching, retained disclosures on refresh, mobile overflow and logout.
