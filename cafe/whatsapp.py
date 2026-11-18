"""Official Meta transport and signed webhooks; no send occurs in web requests."""

import hashlib
import hmac
import json
import os
import re
import secrets
import time
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.error import HTTPError, URLError
from flask import Blueprint, request, abort, current_app
from .db import db, settings

bp = Blueprint("whatsapp", __name__)
AUTOMATIC = {"Confirmed": "confirmed", "Out for Delivery": "out"}


def environment():
    return {
        k: os.environ.get("META_" + k, "")
        for k in (
            "ACCESS_TOKEN",
            "APP_SECRET",
            "WHATSAPP_VERIFY_TOKEN",
            "GRAPH_VERSION",
            "PHONE_NUMBER_ID",
            "WABA_ID",
        )
    }


def mode():
    return os.environ.get("CAFE_LUX_WHATSAPP_MODE", "disabled")


def enqueue(order, status):
    if (
        status not in AUTOMATIC
        or not order["whatsapp_opt_in"]
        or settings().get("wa_automation") != "1"
    ):
        return
    db().execute(
        "INSERT OR IGNORE INTO whatsapp_jobs(job_key,order_id,kind) VALUES(?,?,?)",
        (secrets.token_hex(16), order["id"], status),
    )


@bp.route("/integrations/whatsapp/webhook", methods=["GET", "POST"])
def webhook():
    env = environment()
    if request.method == "GET":
        if (
            env["WHATSAPP_VERIFY_TOKEN"]
            and request.args.get("hub.mode") == "subscribe"
            and hmac.compare_digest(
                request.args.get("hub.verify_token", ""), env["WHATSAPP_VERIFY_TOKEN"]
            )
        ):
            return (
                request.args.get("hub.challenge", ""),
                200,
                {"Content-Type": "text/plain"},
            )
        abort(403)
    raw = request.get_data()
    if not env["APP_SECRET"] or len(raw) > 1024 * 1024:
        abort(403)
    expected = (
        "sha256="
        + hmac.new(env["APP_SECRET"].encode(), raw, hashlib.sha256).hexdigest()
    )
    if not hmac.compare_digest(
        request.headers.get("X-Hub-Signature-256", ""), expected
    ):
        abort(403)
    try:
        payload = json.loads(raw)
        if (
            not isinstance(payload, dict)
            or payload.get("object") != "whatsapp_business_account"
        ):
            abort(400)
        conn = db()
        conn.execute("BEGIN IMMEDIATE")
        conn.execute(
            "INSERT OR REPLACE INTO settings VALUES('wa_webhook_seen',?)",
            (str(time.time()),),
        )
        for entry in payload.get("entry", []):
            if env["WABA_ID"] and str(entry.get("id")) != env["WABA_ID"]:
                continue
            for change in entry.get("changes", []):
                value = change.get("value", {})
                phone_id = str(value.get("metadata", {}).get("phone_number_id", ""))
                number = (
                    conn.execute(
                        "SELECT * FROM whatsapp_numbers WHERE cloud_phone_id=? AND active=1",
                        (phone_id,),
                    ).fetchall()
                    if phone_id
                    else []
                )
                for message in value.get("messages", []):
                    mid = message.get("id", "")
                    sender = str(message.get("from", ""))
                    if (
                        not isinstance(mid, str)
                        or not 1 <= len(mid) <= 300
                        or not re.fullmatch(r"[1-9][0-9]{7,14}", sender)
                    ):
                        continue
                    text = (
                        message.get("text", {}).get("body", "")
                        if message.get("type") == "text"
                        else ""
                    )
                    refs = set(re.findall(r"\bLUX-[A-Fa-f0-9]{12}\b", text.upper()))
                    matched = None
                    state = "manual_review"
                    if len(refs) == 1 and len(number) == 1:
                        order = conn.execute(
                            "SELECT * FROM orders WHERE reference=?",
                            (next(iter(refs)),),
                        ).fetchone()
                        try:
                            sent = int(message.get("timestamp", "0"))
                        except (TypeError, ValueError):
                            sent = 0
                        # Authentic transport is not enough: bind sender, receiver and time.
                        if (
                            order
                            and order["phone"].lstrip("+") == sender
                            and order["receiving_phone"] == number[0]["phone"]
                            and sent > 0
                        ):
                            from datetime import datetime, timezone

                            created = (
                                datetime.fromisoformat(order["created"])
                                .replace(tzinfo=timezone.utc)
                                .timestamp()
                            )
                            if created - 300 <= sent <= time.time() + 300:
                                matched = order
                                state = "matched"
                    inserted = conn.execute(
                        "INSERT OR IGNORE INTO whatsapp_incoming(message_id,sender,phone_id,reference_text,order_id,state) VALUES(?,?,?,?,?,?)",
                        (
                            mid,
                            sender,
                            phone_id,
                            ",".join(sorted(refs))[:500],
                            matched["id"] if matched else None,
                            state,
                        ),
                    ).rowcount
                    if inserted and matched:
                        conn.execute(
                            "UPDATE orders SET incoming_message_id=? WHERE id=?",
                            (mid, matched["id"]),
                        )
                        if matched["status"] == "Pending WhatsApp Submission":
                            conn.execute(
                                "UPDATE orders SET status='Received' WHERE id=?",
                                (matched["id"],),
                            )
                            conn.execute(
                                "INSERT INTO order_history(order_id,status,username) VALUES(?,?,?)",
                                (
                                    matched["id"],
                                    "Received",
                                    "Verified WhatsApp webhook",
                                ),
                            )
                for status in value.get("statuses", []):
                    update_status(status, phone_id)
        conn.commit()
    except (ValueError, TypeError, KeyError, AttributeError):
        db().rollback()
        abort(400)
    return "", 200


def update_status(status, phone_id):
    mid = status.get("id", "")
    state = status.get("status", "")
    if not isinstance(mid, str) or state not in ("sent", "delivered", "read", "failed"):
        return
    job = (
        db()
        .execute("SELECT * FROM whatsapp_jobs WHERE message_id=?", (mid,))
        .fetchone()
    )
    if not job:
        key = status.get("biz_opaque_callback_data")
        job = (
            db()
            .execute(
                "SELECT * FROM whatsapp_jobs WHERE job_key=? AND state IN ('processing','uncertain')",
                (key,),
            )
            .fetchone()
            if isinstance(key, str)
            else None
        )
    archive = None
    if not job:
        key = status.get("biz_opaque_callback_data", "")
        archive = (
            db()
            .execute(
                "SELECT a.*,j.order_id FROM whatsapp_attempts a JOIN whatsapp_jobs j ON j.id=a.job_id WHERE a.message_id=? OR a.attempt_key=? ORDER BY a.id DESC LIMIT 1",
                (mid, key if isinstance(key, str) else ""),
            )
            .fetchone()
        )
    if job or archive:
        receiver = (
            db()
            .execute(
                "SELECT 1 FROM whatsapp_numbers n JOIN orders o ON n.phone=o.receiving_phone WHERE o.id=? AND n.cloud_phone_id=?",
                ((job or archive)["order_id"], phone_id),
            )
            .fetchone()
        )
        if not receiver:
            return
    event = hashlib.sha256(json.dumps(status, sort_keys=True).encode()).hexdigest()
    if not db().execute(
        "INSERT OR IGNORE INTO whatsapp_events(event_key,message_id,status) VALUES(?,?,?)",
        (event, mid[:300], state),
    ).rowcount or not (job or archive):
        return
    ranks = {"submitted": 0, "sent": 1, "delivered": 2, "read": 3}
    if archive:
        if archive["state"] in ("delivered", "read") and state == "failed":
            return
        if state != "failed" and ranks.get(state, 0) < ranks.get(archive["state"], 0):
            return
        db().execute(
            "UPDATE whatsapp_attempts SET state=?,message_id=? WHERE id=?",
            (state, mid[:300], archive["id"]),
        )
        if state in ("sent", "delivered", "read"):
            db().execute(
                "UPDATE whatsapp_jobs SET state='cancelled',error='Earlier attempt confirmed sent; retry cancelled' WHERE id=? AND (state IN ('queued','retry','blocked') OR (state='processing' AND request_started=0))",
                (archive["job_id"],),
            )
        return
    if job["state"] in ("delivered", "read") and state == "failed":
        return
    if state != "failed" and ranks.get(state, 0) < ranks.get(job["state"], 0):
        return
    db().execute(
        "UPDATE whatsapp_jobs SET state=?,message_id=?,error=?,updated=CURRENT_TIMESTAMP WHERE id=?",
        (
            state,
            mid[:300],
            "Provider reported failure" if state == "failed" else "",
            job["id"],
        ),
    )


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


class DeliveryError(Exception):
    def __init__(self, state, code):
        self.state, self.code = state, code


def graph(path, payload=None):
    env = environment()
    if not env["ACCESS_TOKEN"] or not re.fullmatch(
        r"v[0-9]+\.[0-9]+", env["GRAPH_VERSION"]
    ):
        raise DeliveryError(
            "blocked", "Missing credentials or explicit Graph API version"
        )
    adapter = current_app.config.get("WHATSAPP_TRANSPORT")
    if adapter:
        return adapter(path, payload)
    if current_app.testing:
        raise DeliveryError("blocked", "Real HTTP is forbidden in tests")
    req = Request(
        "https://graph.facebook.com/" + env["GRAPH_VERSION"] + "/" + path,
        data=json.dumps(payload).encode() if payload is not None else None,
        headers={
            "Authorization": "Bearer " + env["ACCESS_TOKEN"],
            "Content-Type": "application/json",
        },
    )
    try:
        with build_opener(NoRedirect()).open(req, timeout=20) as response:
            return json.loads(response.read(1024 * 1024))
    except HTTPError as e:
        # A transport timeout/5xx can follow acceptance. Never blindly retry it.
        raise DeliveryError(
            "retry" if e.code == 429 else "uncertain" if e.code >= 500 else "failed",
            "HTTP " + str(e.code),
        ) from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise DeliveryError(
            "uncertain", "Transport outcome unknown; reconcile before retry"
        ) from None


def process_one():
    conn = db()
    now = time.time()
    conn.execute("BEGIN IMMEDIATE")
    conn.execute(
        "UPDATE whatsapp_jobs SET state=CASE WHEN request_started=1 THEN 'uncertain' ELSE 'retry' END,error='Worker lease expired',lease_until=NULL WHERE state='processing' AND lease_until<?",
        (now,),
    )
    job = conn.execute(
        "SELECT * FROM whatsapp_jobs WHERE state IN ('queued','retry') AND due<=? ORDER BY id LIMIT 1",
        (now,),
    ).fetchone()
    conn.execute(
        "INSERT OR REPLACE INTO settings VALUES('wa_worker_heartbeat',?)", (str(now),)
    )
    if not job:
        conn.commit()
        return False
    order = conn.execute(
        "SELECT * FROM orders WHERE id=?", (job["order_id"],)
    ).fetchone()
    if not order["whatsapp_opt_in"] or order["status"] == "Cancelled":
        conn.execute(
            "UPDATE whatsapp_jobs SET state='cancelled',error='Opted out or cancelled' WHERE id=?",
            (job["id"],),
        )
        conn.commit()
        return True
    if settings().get("wa_automation") != "1" or mode() == "disabled":
        conn.execute(
            "UPDATE whatsapp_jobs SET state='blocked',error='Automation disabled' WHERE id=?",
            (job["id"],),
        )
        conn.commit()
        return True
    if mode() == "mock":
        conn.execute(
            "UPDATE whatsapp_jobs SET state='mocked',error='MOCK: no message sent',updated=CURRENT_TIMESTAMP WHERE id=?",
            (job["id"],),
        )
        conn.commit()
        return True
    template = settings().get(
        "wa_" + AUTOMATIC[job["kind"]] + "_" + order["language"], ""
    )
    number = conn.execute(
        "SELECT cloud_phone_id FROM whatsapp_numbers WHERE phone=? AND active=1",
        (order["receiving_phone"],),
    ).fetchall()
    phone_id = number[0][0] if len(number) == 1 else ""
    if (
        mode() != "live"
        or not re.fullmatch(r"[0-9]+", phone_id)
        or not re.fullmatch(r"[a-z0-9_]{1,512}", template)
    ):
        conn.execute(
            "UPDATE whatsapp_jobs SET state='blocked',error='Configure live mode, receiver phone ID and approved language template' WHERE id=?",
            (job["id"],),
        )
        conn.commit()
        return True
    # Do not send out-of-order status messages after an unresolved earlier request.
    earlier = conn.execute(
        "SELECT 1 FROM whatsapp_jobs WHERE order_id=? AND id<? AND state IN ('queued','retry','processing','uncertain','blocked','failed')",
        (order["id"], job["id"]),
    ).fetchone()
    if earlier:
        conn.execute("UPDATE whatsapp_jobs SET due=? WHERE id=?", (now + 60, job["id"]))
        conn.commit()
        return False
    conn.execute(
        "UPDATE whatsapp_jobs SET state='processing',attempts=attempts+1,lease_until=?,request_started=0 WHERE id=?",
        (now + 120, job["id"]),
    )
    conn.commit()
    # Verify the current approved template contract before crossing the send boundary.
    try:
        env = environment()
        if (
            not all(
                env[k]
                for k in (
                    "ACCESS_TOKEN",
                    "APP_SECRET",
                    "WHATSAPP_VERIFY_TOKEN",
                    "WABA_ID",
                )
            )
            or not env["WABA_ID"].isdigit()
        ):
            raise DeliveryError(
                "blocked", "Required Meta credentials or WABA ID missing"
            )
        templates = graph(
            env["WABA_ID"]
            + "/message_templates?name="
            + template
            + "&fields=name,status,language,components&limit=100"
        )
        approved = [
            t
            for t in templates.get("data", [])
            if t.get("name") == template
            and t.get("language") == order["language"]
            and t.get("status") == "APPROVED"
        ]
        bodies = [
            c.get("text", "")
            for t in approved
            for c in t.get("components", [])
            if c.get("type") == "BODY"
        ]
        unsupported = [
            c
            for t in approved
            for c in t.get("components", [])
            if c.get("type") not in ("BODY", "FOOTER")
        ]
        if (
            len(approved) != 1
            or len(bodies) != 1
            or set(re.findall(r"\{\{([0-9]+)\}\}", bodies[0])) != {"1"}
            or unsupported
        ):
            raise DeliveryError(
                "blocked",
                "Template must be APPROVED in this language, with one body parameter {{1}} and no header/buttons",
            )
    except DeliveryError as e:
        conn.execute(
            "UPDATE whatsapp_jobs SET state=?,due=?,lease_until=NULL,error=? WHERE id=? AND state='processing'",
            (
                "retry" if e.state == "retry" and job["attempts"] < 4 else "blocked",
                now + 60,
                e.code,
                job["id"],
            ),
        )
        conn.commit()
        return True
    # Persist the uncertainty boundary before leaving SQLite. No DB lock during HTTP.
    conn.execute("BEGIN IMMEDIATE")
    latest = conn.execute(
        "SELECT whatsapp_opt_in,status FROM orders WHERE id=?", (order["id"],)
    ).fetchone()
    lease = conn.execute(
        "SELECT state,job_key FROM whatsapp_jobs WHERE id=?", (job["id"],)
    ).fetchone()
    if lease["state"] != "processing" or lease["job_key"] != job["job_key"]:
        conn.commit()
        return True
    if (
        not latest["whatsapp_opt_in"]
        or latest["status"] == "Cancelled"
        or settings().get("wa_automation") != "1"
    ):
        conn.execute(
            "UPDATE whatsapp_jobs SET state='cancelled',error='Consent revoked or automation disabled',lease_until=NULL WHERE id=?",
            (job["id"],),
        )
        conn.commit()
        return True
    conn.execute("UPDATE whatsapp_jobs SET request_started=1 WHERE id=?", (job["id"],))
    conn.commit()
    payload = {
        "messaging_product": "whatsapp",
        "to": order["phone"].lstrip("+"),
        "type": "template",
        "template": {
            "name": template,
            "language": {"code": order["language"]},
            "components": [
                {
                    "type": "body",
                    "parameters": [{"type": "text", "text": order["reference"]}],
                }
            ],
        },
        "biz_opaque_callback_data": job["job_key"],
    }
    try:
        response = graph(phone_id + "/messages", payload)
        mid = response["messages"][0]["id"]
        if not isinstance(mid, str) or not mid:
            raise ValueError()
        # Webhook may already have advanced this job during the HTTP call.
        conn.execute(
            "UPDATE whatsapp_jobs SET state=CASE WHEN state IN ('sent','delivered','read','failed') THEN state ELSE 'submitted' END,message_id=?,lease_until=NULL,error='',updated=CURRENT_TIMESTAMP WHERE id=?",
            (mid, job["id"]),
        )
    except DeliveryError as e:
        state = e.state
        if state == "retry" and job["attempts"] >= 4:
            state = "failed"
        conn.execute(
            "UPDATE whatsapp_jobs SET state=?,due=?,lease_until=NULL,error=?,updated=CURRENT_TIMESTAMP WHERE id=? AND state='processing'",
            (state, now + min(3600, 30 * 2 ** job["attempts"]), e.code, job["id"]),
        )
    except (ValueError, KeyError, IndexError, TypeError):
        conn.execute(
            "UPDATE whatsapp_jobs SET state='uncertain',lease_until=NULL,error='Provider response missing message ID',updated=CURRENT_TIMESTAMP WHERE id=? AND state='processing'",
            (job["id"],),
        )
    conn.commit()
    return True


def health():
    env = environment()
    return {
        "mode": mode(),
        "configured": all(
            env[k]
            for k in (
                "ACCESS_TOKEN",
                "APP_SECRET",
                "WHATSAPP_VERIFY_TOKEN",
                "GRAPH_VERSION",
                "WABA_ID",
            )
        ),
        "worker": settings().get("wa_worker_heartbeat", ""),
        "worker_fresh": time.time()
        - float(settings().get("wa_worker_heartbeat", "0") or 0)
        < 180,
        "webhook": settings().get("wa_webhook_seen", ""),
        "connection": settings().get("wa_health_checked", ""),
        "enabled": settings().get("wa_automation") == "1",
    }


def register_commands(app):
    import click

    @app.cli.command("whatsapp-worker")
    @click.option(
        "--once", is_flag=True, help="Process at most one due job, then exit."
    )
    def worker(once):
        while True:
            processed = process_one()
            if once:
                break
            if not processed:
                time.sleep(3)
