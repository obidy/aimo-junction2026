# Trusted Trade Agents — local purchasing API

## Recipe requests (v0.4)

Use **Plan a meal** to enter a request such as “Spaghetti bolognese for 200 people”.
Enter **200** in the portions field (this is the authoritative scaling count), choose
a delivery date and select review-first or automatic mode. The agent searches
the web for a published recipe, extracts its source yield and ingredients,
scales the quantities in Python and matches ingredients to catalogue products.
Fixed mock prices and availability produce ONE combined basket.

### Configure recipe AI in the SERVER PowerShell terminal

Stop the gateway with Ctrl+C. Keep AIMO_API_KEY set to the working Valio mock key.
Add a separate model-provider key and a Responses model that supports both web
search and structured outputs:

```powershell
$env:LLM_API_KEY = "YOUR_ACTUAL_MODEL_PROVIDER_KEY"
$env:LLM_MODEL = "YOUR_RESPONSES_WEB_SEARCH_CAPABLE_MODEL"
python aimo_api.py
```

The Valio API key authenticates supplier lookups; it cannot run the recipe model.
Keep model credentials on the server. No key is sent to the browser.
The default provider URL is https://api.openai.com/v1. If you already use a
Chat Completions-only LLM_BASE_URL/model, set RECIPE_BASE_URL and RECIPE_MODEL
separately to a provider/model supporting Responses + web_search + JSON schema.
The app reports configuration errors and never substitutes a canned recipe.
This feature makes provider calls when requested; provider usage charges may apply.

Reconnect using the current reviewer token, then **Plan a meal**. Review the
source link, scaled quantities, selected products, pack counts and combined total.
**Approve whole recipe & mock-order** creates a local mock receipt after fresh
validation. Nothing is submitted to Valio. Recent meal plans are saved in the
same SQLite database and remain accessible from this dialog.

### Autonomy and external agents

Review-first is the default. A reviewer may choose automatic mode for a request.
For agent-token requests, the buyer must explicitly configure this in the server:

```powershell
$env:AIMO_RECIPE_AUTONOMY = "automatic"
```

The configured AIMO_APPROVAL_LIMIT applies to the **combined product subtotal
INCLUDING tax**, never to each ingredient separately. Automatic mock commitment
requires all required ingredients resolved, eligible current offers, no flagged
recipe/match uncertainty and a subtotal within that limit. Free-text preferences
force review; they are not a certified allergy or nutrition rule engine.
Server AIMO_REQUIRED_CLAIMS and AIMO_REQUIRED_ORIGIN still apply to every product.
A restaurant can review or edit ingredient quantities; a cafeteria can delegate
the recipe choice within this authority.

External-agent example (separate PowerShell terminal, actual running agent token):

```powershell
$env:AIMO_AGENT_TOKEN = "ACTUAL_TOKEN_FROM_RUNNING_SERVER"
python recipe_client.py "Spaghetti bolognese for 200 people" --portions 200 --date 2026-11-16
# Add --automatic only when the buyer has enabled recipe autonomy on the server.
```

Structured endpoints: GET /recipe-capabilities; POST/GET /recipe-plans;
GET /recipe-plans/{id}; POST /recipe-plans/{id}/approve-and-commit (reviewer);
POST /recipe-plans/{id}/commit (already authorised);
POST /recipe-plans/{id}/rebuild (reviewer-supplied total quantities).
The generated OpenAPI contract documents request and response schemas.
Decision requests require the exact saved fingerprint. Rebuild makes a new plan,
preserving the old evidence. Quotes expire after 30 minutes. Commitment refreshes
prices/stock, rejects commercial changes and is idempotent for the plan.

### Honest limits and corrections

Missing yield, quantities such as “to taste”, unverified piece counts, unsuitable
matches or unavailable products block the WHOLE basket. Reviewers can supply
explicit total KG/L quantities in the ingredient cards and rebuild. Catalogue ST
means a packaging unit and does not prove one individual onion or egg. No weight
is guessed from a name or from gross shipping weight. Optional ingredients are
listed but excluded explicitly. Kitchen inventory is not connected, so all
required ingredients are assumed needed.

The agent uses a sourced recipe but its extraction and matching remain model
judgements; URLs are checked against returned search sources, not independently
certified. The cheapest eligible SKU is selected among up to five model-matched
options from the first 20 lexical/convertible catalogue candidates per ingredient.
This is not a global basket optimiser. Delivery charges/deposits are excluded.
No nutrition/school-meal compliance is asserted.

Offline tests use synthetic provider/search responses and mocked supplier calls.
A real model-provider request has not been tested without your configured key.
Run `python -m unittest test_api test_recipe_agent` for the regression checks.


## Reviewer dashboard (new)

Open **http://127.0.0.1:8000/** after starting `python aimo_api.py`.
Paste the actual **AIMO_REVIEWER_TOKEN** from the server terminal into the
Reviewer token field, then click **Open review workspace**.

The dashboard provides a proposal queue, basket amounts, spending threshold,
unknown-stock notice, comparison alternatives and decision history. Select a
proposal, click **Approve spending** or **Reject**, review the confirmation and
submit. Rejection requires a reason. Decisions use the exact saved fingerprint;
the browser does not calculate or submit its own price or spending limit.

Use **New comparison** to choose a product query, quantity, unit and delivery date, compare options
and save an eligible basket without using Swagger. The existing agent client
continues to work. Alternatives are the original stored comparison, not newly
fetched prices. Legacy proposals without linked comparisons say so explicitly.

Tokens stay in tab memory and are cleared on disconnect/reload. No tokens are
stored in browser local/session storage. Connecting with an agent token gives
read access but does not enable approval/rejection. HTTP 403 is also enforced by
the backend. The dashboard refreshes the queue once a minute while visible and
provides a manual Refresh button. An expired pending proposal cannot be approved.

### Upgrade from the earlier API ZIP

Stop the server with Ctrl+C. Extract this ZIP into the **same project folder**,
replacing its code files and adding the entire `static` folder. Do not delete
`purchase_proposals.sqlite3` or the product catalogue. No database is included in
the ZIP, so your saved proposals and history remain intact. The backend adds a
small comparison-link table automatically; no manual database migration is
needed.

Restart with `python aimo_api.py` in the terminal where AIMO_API_KEY is set.
Generated local tokens change on restart; use the newly printed reviewer token.
The dashboard and API use the same local database.

A working Python HTTP gateway around the milk purchasing flow. It searches the
supplied static catalogue, queries the supplied price and availability APIs,
calculates single-product baskets across the catalogue and saves an order draft, automatically authorised within policy or pending human approval above the limit. It never submits
supplier orders, connects to the production webshop or requires webshop credentials.

## Windows quick start

1. Extract this ZIP into a folder containing
   `valio_aimo_junction26_product_data.json`. All `.py` files should be beside it.
   Keep your existing `milk_compare.py`; this package uses `aimo_core.py` instead.
2. Open PowerShell in that folder and install dependencies:

```powershell
python -m pip install -r requirements.txt
```

3. Set the **Valio mock API key**, then start the server:

```powershell
$env:AIMO_API_KEY = "YOUR_VALIO_MOCK_API_KEY"
python aimo_api.py
```

The server prints two generated local tokens:

- `AIMO_AGENT_TOKEN`: search, compare, create/read proposals.
- `AIMO_REVIEWER_TOKEN`: those operations plus approve/reject.

These are different from the Valio API key. Keep the reviewer token away from the
agent. The generated tokens change when you restart the server. To use stable
tokens, set distinct values in those two environment variables before starting.

Open **http://127.0.0.1:8000/docs** to use the interactive API documentation.
The machine-readable contract is **http://127.0.0.1:8000/openapi.json**.
The ZIP also includes a generated `gateway_openapi.json` contract.

If your catalogue is elsewhere, set its path before starting:

```powershell
$env:AIMO_CATALOG = "C:\Users\torre\Downloads\juncttion2026\valio_aimo_junction26_product_data.json"
```

## Run the separate purchasing client

Keep the server terminal running. Open a **second PowerShell window**, navigate
to the same folder and copy the agent token printed by the server:

```powershell
$env:AIMO_AGENT_TOKEN = "COPY_THE_GENERATED_AGENT_TOKEN"
python agent_client.py --date 2026-11-16 --litres 1000
```

The deterministic reference client:

1. Searches for plain lactose-free milk.
2. Checks prices and availability for the shortlist.
3. Chooses the lowest tax-inclusive product subtotal among baskets passing checks.
4. Saves a proposal and prints its ID, spending state and full fingerprint.

This client is deterministic. The optional `llm_agent.py` below adds a separate
natural-language LLM tool client using the same documented gateway operations. Repeated client runs create new proposals; the local mock commitment is idempotent per proposal. Replaying a commitment
returns its existing receipt rather than creating another order.

## Review and approve in the API docs

1. Open `/docs`, click **Authorize**, paste the **reviewer token only**, and
   click Authorize. Do not prepend `Bearer`; the UI handles it.
2. Expand `GET /proposals/{pid}`, select **Try it out**, enter the proposal ID,
   and execute. Read the basket, reasons, unknown-stock warning and expiry.
3. Copy the complete 64-character `fingerprint` from the response.
4. Expand `POST /proposals/{pid}/approve`, enter the ID and use:

```json
{
  "fingerprint": "COPY_THE_FULL_64_CHARACTER_FINGERPRINT",
  "note": "Budget approved for this basket"
}
```

5. Execute. The response should show `spending_status: APPROVED` and an approval
   event. `order_submitted` remains false.

For rejection use `/proposals/{pid}/reject` with the same fingerprint and a
non-empty explanation in `note`. Agent tokens receive HTTP 403 on both routes.
The fingerprint binds the decision to the exact saved basket/evidence. It is not
a digital signature or protection from an administrator editing the database.

## API endpoints

| Method | Path | Purpose | Credential |
| --- | --- | --- | --- |
| GET | `/health` | Local server health | None |
| GET | `/policy` | Read configured buyer rules | Agent or reviewer |
| GET | `/products?q=milk&plain_milk=true` | Search static product information | Agent or reviewer |
| POST | `/offers` | Check product baskets against requirements, price, availability and policy | Agent or reviewer |
| POST | `/proposals` | Save one basket from a server-stored offer | Agent or reviewer |
| GET | `/proposals` | List this buyer's saved proposals | Agent or reviewer |
| GET | `/proposals/{pid}` | Inspect basket and event history | Agent or reviewer |
| POST | `/proposals/{pid}/approve` | Approve spending for exact fingerprint | Reviewer only |
| POST | `/proposals/{pid}/reject` | Reject with reason | Reviewer only |

Example `/offers` request:

```json
{
  "delivery_date": "2026-11-16",
  "litres": "1000",
  "product_ids": ["464201", "464073"]
}
```

Example `/proposals` request (use an actual offer ID):

```json
{
  "offer_id": "O-COPY_FROM_OFFER_RESPONSE",
  "sku": "464201"
}
```

Money and computed quantities are JSON **strings** to preserve decimal precision.
Amounts are EUR. `net` excludes tax; `gross` includes tax. The server evaluates
the spending threshold against `gross`, excluding delivery charges and deposits.
Agents cannot supply prices, a customer ID or approval limits in these requests.
Extra request fields are rejected. Missing catalogue litre/kilogram conversions are not
guessed from the product name or comparison price.

## Server configuration

| Variable | Default / purpose |
| --- | --- |
| `AIMO_API_KEY` | Required Valio mock backend key; server only |
| `AIMO_AGENT_TOKEN` | Generated on `python aimo_api.py` startup if absent |
| `AIMO_REVIEWER_TOKEN` | Separate generated reviewer token |
| `AIMO_REVIEWER_NAME` | `local-reviewer`; recorded as the decision actor |
| `AIMO_CUSTOMER` | `123`; one configured buyer per server |
| `AIMO_APPROVAL_LIMIT` | `1200`; EUR product subtotal including tax |
| `AIMO_CATALOG` | Product JSON beside the scripts |
| `AIMO_DB` | `purchase_proposals.sqlite3` beside the scripts |

SQLite stores offers, immutable proposal snapshots and decision events. Existing
CLI proposals in the same database remain readable. Old snapshots are not
rewritten to apply new rules. Proposals and offers have local 30-minute review
windows; these are not supplier reservations or price locks.

The upstream API client paces requests to one per second in this process. On
HTTP 429 it waits at least 30 seconds (longer when Retry-After requests it), then
retries up to three attempts total. Avoid multiple independent server instances
or stress-test scripts, which do not share this in-memory cooldown.

## Mentor rules applied

- Stock amounts >=999999: orderable with stock quantity **unknown**, not unlimited
  or guaranteed physical stock.
- Empty availability schedules: unavailable.
- Product/schedule sales blocks: blocked.
- Lot size 0.01: interpreted as one whole sales unit.
- Closing time: checked against its related available date; an expired cutoff
  still blocks the candidate. Fixed weekend mock dates are not silently moved.
- The challenge ends at a saved proposal for approval. There is no order API.

## Tests and limits

```powershell
python -m unittest -v test_api
```

Thirty-one integration tests use local fixtures, not live upstream calls. They cover
search/auth/schema, policy/price injection, unknown-stock baskets, approvals,
reviewer-only permissions, duplicate decisions, changed fingerprints, rejection,
blocked stock, expiry, policy changes, buyer scoping, dashboard assets, session
roles, original-comparison linkage, general quantities, automatic authority,
required claims/origin, variable-weight rejection and a mocked LLM tool loop.

This is a local prototype bound to 127.0.0.1, with one buyer and a shared reviewer
credential. It does not verify an employee's identity, implement SSO, provide
multi-tenant administration, or make stock/delivery guarantees. The spending
limit is demo configuration rather than an authenticated policy administration
service. Approval is a spending decision, not permission to bypass product or
delivery restrictions. The catalogue and all upstream data are challenge-only
synthetic data. No credentials or datasets are included in this package.


## Core challenge coverage and new request types

See `CHALLENGE_COVERAGE.md` for the requirement mapping and a focused demo plan.

The gateway now accepts `quantity`, `unit` (`L`, `KG`, `SALES_UNIT`), a `query`,
`required_claims` and `required_origin`. The legacy `litres` request field still
works. Do not supply both `litres` and `quantity`. For non-milk queries set
`plain_milk` to false (or omit it when a query/product ID list is present).

For example, compare macaroni in kilograms:

```json
{
  "query": "macaroni",
  "quantity": "100",
  "unit": "KG",
  "delivery_date": "2026-11-16",
  "plain_milk": false,
  "required_origin": "fi"
}
```

Or request two complete sales units of matching catalogue products:

```powershell
python agent_client.py --date 2026-11-16 --query macaroni --quantity 2 --unit SALES_UNIT
```

`KG` uses explicit net weight and the catalogue packaging hierarchy. Variable
weight or missing conversions remain unresolved. `SALES_UNIT` requires no litre
or kilogram conversion; inspect each returned unit/pack definition before using
it. Search is a lexical catalogue shortlist, not a guarantee that all matching
products are interchangeable. Narrow requests and inspect alternatives.

Required claim codes must be explicitly present in the product's nutritional
claims. Missing claims block the candidate. These are not a comprehensive food
safety or allergen certification system. Origin requirements use the catalogue's
countryOfOrigin field. The model must ask for clarification when requirements
cannot be expressed or verified; it must not invent claims from a product name.

Optional server-enforced product requirements:

```powershell
$env:AIMO_REQUIRED_CLAIMS = "FREE_FROM_LACTOSE"
$env:AIMO_REQUIRED_ORIGIN = "fi"
```

These apply to all requests for this buyer and cannot be loosened by an agent.
Leave unset for a general-purpose buyer. To clear a requirement in PowerShell:
`Remove-Item Env:AIMO_REQUIRED_CLAIMS` (and similarly for origin). Restart after
changing configuration.

A saved eligible basket at or below the spending limit gets
`AUTO_AUTHORISED` and an automatic-authority audit event. Above the limit it gets
`PENDING`; only the reviewer token can approve/reject it. The limit is **per
proposal**, not a daily aggregate budget. The mentor guidance allows stopping at a human-approved draft. This version
also supports a clearly labelled local mock commitment and receipt so the full
inquiry-to-commitment interaction is demonstrable. No upstream order endpoint
exists and this service never uses the production webshop.

Download that exact draft with `GET /proposals/{pid}/order-draft`, or the
**Download structured order draft** button in the dashboard. The JSON includes
its lines, recorded spending state, fingerprint, source evidence and unknown
stock disclosure. It remains explicit that delivery charges/deposits are omitted
and no order has been sent. The current review-window expiry is included.

## Optional LLM purchasing agent

This is separate from the gateway. The gateway works without a model or model
key. The LLM client uses the Chat Completions function-tool protocol and obtains
its offer/request schemas from the gateway's OpenAPI contract. Official protocol
reference: https://developers.openai.com/api/docs/guides/function-calling

In the **client terminal**, set your actual agent token, a model-provider API key
and a model identifier supporting Chat Completions function tools:

```powershell
$env:AIMO_AGENT_TOKEN = "YOUR_ACTUAL_LOCAL_AGENT_TOKEN"
$env:LLM_API_KEY = "YOUR_MODEL_PROVIDER_API_KEY"
$env:LLM_MODEL = "YOUR_TOOL_CAPABLE_MODEL_ID"
python llm_agent.py "I need 1000 litres of plain lactose-free milk by Monday. Find the cheapest eligible option and create a proposal."
```

`LLM_BASE_URL` defaults to `https://api.openai.com/v1`. Set it to another
compatible provider if desired. Compatibility depends on that provider/model;
only the protocol loop with a mocked provider is tested here. No live model call
has been made during development. Use your own model credentials; the Valio
challenge key cannot authenticate to a model provider.

The LLM sees the user request and synthetic gateway tool results, not either
service credential. It has five tools: read policy, search products, compare
offers, create a proposal and place a local mock order. It refuses to run with a reviewer credential and
has no approve/reject or arbitrary-HTTP tool. It creates at most one proposal, can commit that proposal when authorised, and
limits tool rounds. Exact claims, quantity arithmetic, stock/delivery checks,
prices, role checks and spending authority are enforced by server code. Natural
language interpretation itself remains model behaviour and needs a live demo
check with your chosen model. Clarification is preferable to silently weakening
requirements.

A reliable model-free demo of the two authority branches is:

```powershell
python agent_client.py --date 2026-11-16 --litres 100
python agent_client.py --date 2026-11-16 --litres 1000
```

With the currently observed prices and EUR 1200 limit, 100 litres should be
within authority and 1000 litres should need approval. Actual eligibility still
depends on the mock cut-off and delivery responses. No dates are silently shifted.


## Complete inquiry → commitment flow (version 0.3)

The three core tasks now have concrete endpoints:

| Task | Operations |
| --- | --- |
| Product/price/availability lookup | `GET /products`, `POST /offers` |
| Fixed-price inquiry to commitment | `POST /proposals`, `POST /orders`, `GET /orders/{id}` |
| Permissions and human approval | `GET /policy`, automatic authority evaluation, reviewer-only approve/reject |

`POST /orders` commits a **LOCAL MOCK ORDER**, not a supplier order. It rechecks
current price, quantity conversion, dietary/origin requirements, availability,
cut-off, delivery date, expiry and spending authority. An unapproved pending
proposal cannot be committed. Any commercial change returns HTTP 409 and requires
a new proposal/authority decision. Stock-marker values remain explicitly unknown
but orderable under the mentor's mock rules. Delivery fees and deposits are not
part of this simulated product subtotal.

The request is only:

```json
{"proposal_id": "P-YOUR_ACTUAL_PROPOSAL_ID"}
```

The receipt contains an `M-...` ID, `status: COMMITTED_MOCK`, the approved
fingerprint, fresh validation evidence and `upstream_order_submitted: false`.
Exactly one receipt can be stored per proposal. Retrying the same commitment
returns HTTP 200 with the same receipt; initial creation returns HTTP 201.
Receipt creation and the commitment audit event are one database transaction.
`GET /orders` lists saved receipts for the configured buyer.

### From the dashboard

Review a pending proposal and approve it. The action bar then offers
**Commit mock order**. Confirm that action to perform fresh checks and save the
local receipt. An auto-authorised proposal offers this action immediately.
After commitment, download the mock receipt from the same action bar. Existing
proposals and history stay in the database; very old proposals without recorded
requirements/evidence must be recreated before mock commitment.

### From the external client

The reference client now automatically commits a newly created proposal if it
is within authority. To stop at a proposal, add `--draft-only`:

```powershell
python agent_client.py --date 2026-11-16 --litres 100
python agent_client.py --date 2026-11-16 --litres 1000
```

The larger request normally requires review. After the reviewer approves it:

```powershell
python agent_client.py --commit-proposal P-YOUR_ACTUAL_PROPOSAL_ID
```

An expired proposal or changed offer must be recreated and reapproved rather than
reusing old authority. No real payment, production order, stock reservation or
delivery guarantee is made by this prototype. A production adapter would require
Valio's actual order interface and complete delivery/deposit cost handling.

The 31 tests also cover pending-order denial, automatic commitment, reviewed
commitment, same-receipt retries, changed-price refusal, new stock/claim failure,
policy/expiry/buyer checks and atomic receipt/audit persistence.


## Version 0.3.1 — avoiding empty/unorderable shortlists

Catalogue query searches now prioritise products with supported conversions for
L/KG. They query dynamic data in batches of at most 20, continuing past the first
batch when fewer than five eligible options are found (at most 60 candidates per
comparison). The response reports match/conversion/checked/eligible counts and a
`next_scan_offset` when more compatible candidates remain. Use the dashboard's
**Check more matching products** or pass that offset in the next `/offers`
request with the same criteria. Explicit SKU requests still show those SKUs,
including unresolved ones, rather than silently substituting other products.

The dashboard puts eligible choices first, with blocked/unresolved results in a
separate expandable section. It shows per-sales-unit prices when a physical
basket cannot be calculated. **Use sales units instead** changes the unit only
when clicked and clears the old quantity: enter a new pack/case count yourself.
It never reinterprets 100 kilograms as 100 packs automatically.

Case-level net weights can now be used when the CASE record, sales-unit GTIN and
labelled multipack count agree with the unit hierarchy. The case weight is NOT
multiplied by the pack count a second time. Gross weight is never used as net
food weight, and a weight is never invented from the product name. Records with
insufficient evidence remain unresolved in KG/L; use sales units explicitly if
that meets the buying need.

A passed order cut-off and unavailable stock remain genuine blockers. Changing
units does not override them. Choose another eligible product or try a later
delivery date; fixed mock dates may still make a particular SKU unavailable.
Product searches now match whole words, avoiding e.g. `pasta` matching a Finnish
compound word for chilli paste. Specific queries such as `macaroni` or a brand
and pasta shape give more relevant choices than broad `pasta` searches.
