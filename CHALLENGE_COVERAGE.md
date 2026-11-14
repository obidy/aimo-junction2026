# Challenge coverage — Trusted Trade Agents

## Core: implemented prototype paths

| Challenge requirement | Where it is implemented | What to show |
| --- | --- | --- |
| Structured product lookup | `GET /products`, catalogue-wide names, claims, labels, origins, sales units | External client searches the supplied catalogue |
| Fixed price and availability | `POST /offers`; calls the supplied price/availability endpoints only for a shortlist | Candidate prices, basket costs, dates, cut-offs, blocked options and explicit unknown stock |
| Inquiry to commitment | Server-stored offer → exact proposal → autonomous authorisation or human decision → fresh validation → local mock order and receipt | Show `POST /orders` and its COMMITTED_MOCK receipt; retries return the same receipt. No supplier submission. |
| Autonomous decisions within authority | `AUTO_AUTHORISED`, recorded automatically when an eligible basket is within the configured per-proposal spending limit | A smaller milk request authorises and commits through the reference client without a human click |
| Human approval beyond authority | `PENDING`, separate reviewer credential, exact basket fingerprint, immutable snapshot and decision event | A larger milk request, reviewed in the dashboard |
| Open interface | OpenAPI 3.1 contract and JSON Schema request/response models; generated `/openapi.json` | Another client can call the gateway without the dashboard |
| External purchasing agent | Deterministic reference client and optional LLM function-tool client | Run the client in a separate process; reviewer token is unavailable to it |
| Synthetic scope | Supplied product JSON and mock price/availability API; no webshop or order-submission call | Explain the production boundary |

The prototype handles **single-product basket alternatives**, not a mixed menu
or multi-line order optimisation problem. Litres/kilograms require recorded unit
conversions; sales-unit requests work without guessing physical quantity.

## Insight: what is covered and what remains optional

| Topic | Current implementation | Limit |
| --- | --- | --- |
| Trust protocol | Authenticated gateway, HTTPS upstream, typed data, timestamp/validity/source evidence, exact snapshot fingerprint | Catalogue origin and labels are claims; no independently verified credentials or supplier digital signatures. A fingerprint is not proof of truth. |
| Guardrails | Server-side price, quantity, delivery/cut-off, sales-block, spend, recorded claims/origin and role checks | One configured buyer and local credentials; no SSO or cumulative budget accounting |
| Response logic | Cheapest eligible full-quantity single-SKU basket, exclusions and reasons; unknown stock is disclosed and orderable under mentor rules | No partial-basket splitting, recipe substitutions or good/better/best scoring |
| Audit trail | Saved price/stock evidence, selected basket, selection reason, fingerprint, time, actor and approval decision | Local SQLite; not an externally anchored tamper-proof log |
| Delivery comparison | Requested/available dates and cut-offs are checked | Reliability CSV is not yet integrated |
| Sustainability | Existing catalogue label codes are exposed | No verified certificate interpretation, carbon ranking or carbon-footprint dataset integration |

The recipe, last-minute event, proactive selling, allergen-safe substitution and
standing-order scenarios in the brief are inspiration, not additional core
requirements. Do not claim them as working features. A lactose-free claim is not
evidence that milk allergens are absent. Missing information must not be treated
as compliance.

## Suggested judging demo

1. **External agent:** Give the optional LLM client the 1000-litre milk request,
   or use the deterministic client for a model-free fallback. Show its policy,
   search, offer and proposal tool calls.
2. **Comparison:** Show why the lowest nominal price was excluded if its cut-off
   is passed, and why stock-marker values mean unknown/orderable rather than
   confirmed inventory.
3. **Human control:** A EUR 1770 product subtotal exceeds EUR 1200 authority.
   Review and approve the exact saved proposal using a separate reviewer token.
4. **Autonomy:** Repeat with 100 litres, assuming current eligible prices remain
   below the configured limit. Show AUTO_AUTHORISED and the audit event without
   a human click.
5. **Boundary:** Attempt approval using an agent token; it receives HTTP 403.
   Commit the approved mock order, download its receipt and retry the same proposal to show the same receipt ID. Point out no supplier order is sent.

Use current responses rather than hard-coded result claims. Offers and
proposals have local 30-minute review windows, not stock reservations. Mock
cut-offs stay fixed over the event, so a candidate can legitimately become
blocked. Live provider/model integration still needs to be tested with your own
credentials. The automated suite uses synthetic fixtures and a mocked model.


## Mock order boundary

Version 0.3 adds an explicit local commitment endpoint to make core task two
visible end to end. The mentors do not require a supplier submission; the
simulated receipt is clearly labelled MOCK_ONLY/COMMITTED_MOCK. A pending
proposal cannot be committed by the agent, fresh validation failures stop the
commitment, and a unique proposal-to-order record prevents duplicate retries.
This is not evidence of production integration or real delivery acceptance.


## Recipe planning extension

POST /recipe-plans accepts a meal request, target portions, delivery date and
buyer-controlled autonomy. A Responses web-search model finds a cited recipe;
structured extraction and catalogue-only semantic matching feed deterministic
scaling, whole-pack calculation, live mock pricing/availability and combined
spend decisions. One reviewer decision covers the entire recipe and basket.
Unresolved required ingredients block partial commitment. Changes require a new
plan and refreshed review. Receipts remain MOCK_ONLY, with no upstream submission.
See README for required separate model credentials and prototype limitations.
