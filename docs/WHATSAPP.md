# Official Meta WhatsApp Cloud API

## Real-world prerequisites

Use a Meta business account/WABA, a registered WhatsApp Business number, an app subscribed to the WABA `messages` webhook, a suitably permissioned long-lived/system-user token, approved templates and a supported Graph API version. Business verification, phone registration/coexistence requirements, policies, charges, template classification and approval are controlled by Meta. The application does not claim to complete those external steps.

Set credentials only in your service environment, from `config/v4.env.example`. Do not commit tokens or put them in settings/database/logs. Set `META_ACCESS_TOKEN`, `META_APP_SECRET`, a random `META_WHATSAPP_VERIFY_TOKEN`, `META_GRAPH_VERSION=vXX.X`, `META_PHONE_NUMBER_ID` and `META_WABA_ID`. Choose a currently supported Graph version in Meta's console. Avoid shell history containing secrets.

Register HTTPS callback `https://YOUR-HOST/integrations/whatsapp/webhook`. GET accepts the exact verify token and subscribe challenge. POST validates HMAC-SHA256 over the **raw body** with the app secret and constant-time comparison. Only this exact route is exempt from form CSRF; all other writes retain CSRF. Invalid signatures never update orders. Keep webhooks reachable publicly over HTTPS; do not add session/login gates.

Admin → WhatsApp Automation maps each existing receiving number to its **Meta phone-number ID**. With multiple receivers the selected order receiver's mapping is used, never an unrelated default. `META_PHONE_NUMBER_ID` is used by the explicit connection test; it does not override per-order routing.

## Templates to submit to Meta

Use four templates, language codes `en` and `ar`, a BODY containing exactly one numbered parameter `{{1}}` (the order reference), optional static footer, no header/buttons/extra parameters. Suggested names and text (proposals, not approved templates):

| Name | Language | Proposed body |
|---|---|---|
| cafe_lux_confirmed_en | en | Your Café LUX order {{1}} has been confirmed. Thank you for choosing Café LUX! |
| cafe_lux_confirmed_ar | ar | تم تأكيد طلبك {{1}} من كافيه لوكس. شكراً لاختيارك كافيه لوكس! |
| cafe_lux_out_en | en | Your Café LUX order {{1}} is on its way! Thank you for choosing Café LUX. |
| cafe_lux_out_ar | ar | طلبك {{1}} من كافيه لوكس في طريقه إليك! شكراً لاختيارك كافيه لوكس. |

Configure actual approved names in admin. The worker checks Meta's current `APPROVED` status, language and component contract before sending; unsuitable templates block the job. Connection test reads the phone identity and the first 100 template statuses without sending a message. A successful connection is not proof that any message was delivered.

## Consent and incoming workflow

The optional, initially unchecked checkout checkbox authorizes the two status updates **for that order**. The order snapshot records consent wording/version, timestamp and language. Existing orders are opted out. Customers can withdraw from their own confirmation page or account. Unconsented orders generate no jobs. A send already in flight cannot be recalled.

A click-to-chat handoff creates **Pending WhatsApp Submission**, never acceptance. The customer taps Send manually. Signed incoming messages must contain exactly one LUX reference, the order's normalized sender phone, the selected active business receiver's phone ID and a plausible timestamp after creation. Duplicate message IDs are ignored. Valid matches mark only Received, never Confirmed or stock deduction. Unmatched/ambiguous messages go to the admin inbox for staff verification and an audited manual match with a reason. Only references/metadata are retained, not arbitrary message bodies.

Staff confirm fulfillment using the existing order workflow. Only a change to **Confirmed** or **Out for Delivery** queues an automatic job; Received/Preparing/Ready/Delivered/Cancelled never do. One durable job per order/type prevents duplicate status submissions and status cycling from sending another notification.

## Worker and safe delivery

After testing on separate data, configure `CAFE_LUX_WHATSAPP_MODE=live` and enable automation in admin. Run a single supervised worker using the same virtualenv, external data directory and environment as web:

```bash
/path/to/.venv/bin/python /path/to/CAFE-LUX/manage.py whatsapp-worker
# Scheduled execution/testing: process at most one due job and exit
/path/to/.venv/bin/python /path/to/CAFE-LUX/manage.py whatsapp-worker --once
```

Use an always-on task/service with restart-on-failure. Credentials must exist in both web and worker environments. The worker uses short SQLite write transactions and performs network calls outside the DB lock. Its heartbeat and durable job/error state appear in admin. Keep the data on a local persistent disk, not a network share. SQLite's busy timeout and a single worker are suitable for a small single-host shop; load-test your actual traffic. For sustained write contention or multiple web hosts, plan a separately tested PostgreSQL/queue migration. No database/framework swap is needed for this release.

Delivery states: queued → processing → submitted → signed provider sent/delivered/read. An API message ID means accepted/submitted, not delivered. Signed failure callbacks record failure. Provider callbacks cannot move read/delivered backward. `biz_opaque_callback_data` links an authenticated callback even if the worker lost the HTTP response.

HTTP 429 is retried with bounded backoff (maximum five attempts). Definite configuration/4xx failures require correction and manual retry. Send timeouts, 5xx, malformed success responses and crashed workers after the persisted send boundary become **uncertain**. Meta does not provide a universal exactly-once send contract: blind retry could duplicate a message. Reconcile in Meta, then explicitly acknowledge duplicate risk before manual retry. A crash before starting a send safely returns to retry. Later notifications wait for unresolved earlier jobs. Each manually retried send receives a new callback identity; previous attempts remain in history. Late callbacks update that earlier attempt rather than claiming delivery for the new attempt. If an earlier attempt is confirmed sent before the retry starts sending, the retry is cancelled. Do not delete queue tables to recover a worker.

`disabled` is the default; no sends. `mock` records `mocked` with no provider ID and **no message sent**, for separate development data only. Automated tests forbid real transport even in live mode. Do not enable mock mode on a production shop and treat it as delivery.

## Hosting

PythonAnywhere free accounts do not supply reliable always-on workers and outbound Meta HTTPS may be blocked by their allowlist. Keep automation disabled and use manual WhatsApp ordering until a plan/host with always-on background tasks, required outbound networking and public HTTPS webhook is configured. Check your account's current task/network limits. Moving just the worker to another host cannot share this local SQLite file safely: use a proper shared database/queue architecture first.

Windows can run a dedicated service or Task Scheduler task for `manage.py whatsapp-worker`, with the same external data path and protected environment; the web remains Waitress behind existing IIS. Do not alter IIS just to start the worker. Worker supervision and production sends require separate deployment approval.
