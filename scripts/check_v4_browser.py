"""V4 browser acceptance using only disposable synthetic data and mock Meta jobs."""

import json
import os
import secrets
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cafe import create_app
from cafe.db import db
from cafe.whatsapp import process_one
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect

OUTPUT = Path(__file__).resolve().parents[1] / "screenshots" / "v4"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    os.environ["CAFE_LUX_WHATSAPP_MODE"] = "mock"
    checks = []
    errors = []
    with tempfile.TemporaryDirectory(prefix="lux-v4-browser-") as data:
        app = create_app(
            {"TESTING": True, "DATA_DIR": data, "SESSION_COOKIE_SECURE": False}
        )
        admin_password = secrets.token_urlsafe(20)
        with app.app_context():
            conn = db()
            conn.execute(
                "INSERT INTO users(username,password) VALUES(?,?)",
                ("synthetic-admin", generate_password_hash(admin_password)),
            )
            conn.execute(
                "INSERT INTO products(name,name_ar,description,description_ar,kind,active,featured,temperature) VALUES('Synthetic daily cup','فنجان تجريبي','Synthetic browser fixture only.','منتج تجريبي فقط.','drink',1,1,'hot')"
            )
            conn.execute(
                "INSERT INTO variants(product_id,label,price,stock,unit_cost) VALUES(1,'Regular',400,50,100)"
            )
            conn.execute(
                "INSERT INTO products(name,name_ar,description,kind,active,featured,grinds) VALUES('Synthetic home blend','خلطة تجريبية','Synthetic browser fixture only.','ground',1,1,'Whole beans')"
            )
            conn.execute(
                "INSERT INTO variants(product_id,label,price,stock,unit_cost) VALUES(2,'200 g',800,50,300)"
            )
            conn.execute(
                "INSERT INTO bundles(name,name_ar,description,price,active) VALUES('Synthetic pair','مجموعة تجريبية','Browser fixture, not a real offer.',1000,1)"
            )
            conn.execute(
                "INSERT INTO bundle_items(bundle_id,variant_id,qty,temperature) VALUES(1,1,2,'hot')"
            )
            conn.execute(
                "INSERT INTO promotions(code,kind,value,active) VALUES('SYNTHETIC','percent',10,1)"
            )
            conn.execute(
                "INSERT INTO whatsapp_numbers(label,phone,cloud_phone_id) VALUES('Synthetic receiver','+96171111111','1234')"
            )
            conn.execute(
                "INSERT INTO delivery_areas(name,fee,whatsapp_id) VALUES('Synthetic area',200,1)"
            )
            conn.execute(
                "UPDATE settings SET value='1' WHERE key IN ('ordering','wa_automation')"
            )
            conn.execute(
                "UPDATE settings SET value='SYNTHETIC PREVIEW · Not real offers' WHERE key='banner'"
            )
            conn.commit()
        server = make_server("127.0.0.1", 0, app, threaded=True)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    executable_path="/usr/bin/chromium", args=["--no-sandbox"]
                )
                context = browser.new_context(
                    viewport={"width": 1366, "height": 900}, reduced_motion="reduce"
                )
                page = context.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("dialog", lambda d: d.accept())
                base = f"http://127.0.0.1:{server.server_port}"

                def goto(path):
                    response = page.goto(base + path)
                    assert response.status == 200, (path, response.status)
                    page.wait_for_load_state("networkidle")
                    assert page.evaluate("document.body.scrollWidth<=innerWidth"), (
                        path,
                        page.viewport_size,
                    )

                def shot(name):
                    page.locator("img").evaluate_all(
                        "async images=>{images.forEach(i=>i.loading='eager');await Promise.all(images.map(i=>i.decode()));}"
                    )
                    page.screenshot(path=str(OUTPUT / (name + ".png")), full_page=True)

                goto("/")
                shot("v4-published-home-desktop")
                goto("/drinks")
                page.get_by_role("button", name="Save to favorites").click()
                expect(page.locator("main")).to_contain_text("Synthetic daily cup")
                goto("/account/register")
                page.fill("[name=username]", "synthetic-customer")
                page.fill("[name=password]", "Synthetic-long-password")
                page.get_by_role("button", name="Create account", exact=True).click()
                codes = page.locator(".recovery-code code").all_text_contents()
                assert len(codes) == 3
                shot("account-recovery-codes")
                page.get_by_role("link", name="I have saved my codes").click()
                page.fill("[name=name]", "Synthetic Browser Customer")
                page.fill("[name=phone]", "+96171111112")
                page.fill("[name=email]", "synthetic@example.test")
                page.get_by_role("button", name="Save profile").click()
                page.get_by_text("Add an address", exact=True).click()
                page.fill("[name=label]", "Synthetic home")
                page.fill("[name=address]", "Synthetic browser street")
                page.fill("[name=building]", "Synthetic building")
                page.get_by_role("button", name="Save address", exact=True).click()
                goto("/favorites")
                expect(page.locator("main")).to_contain_text("Synthetic daily cup")
                checks.append(
                    "Guest favorites merge into optional customer account; recovery codes shown once; profile/email/address saved"
                )
                goto("/drinks")
                page.get_by_role("button", name="Add to bag +", exact=True).click()
                goto("/bundles")
                expect(page.locator("main")).to_contain_text("2 × Synthetic daily cup")
                page.get_by_role("button", name="Add bundle to bag").click()
                goto("/cart")
                page.fill("[name=code]", "SYNTHETIC")
                page.get_by_role("button", name="Apply", exact=True).click()
                expect(page.locator(".cart-summary")).to_contain_text("1.40")
                shot("v4-promotion-bundle-cart")
                goto("/checkout?address=1")
                expect(page.locator("[name=name]")).to_have_value(
                    "Synthetic Browser Customer"
                )
                expect(page.locator("[name=address]")).to_have_value(
                    "Synthetic browser street"
                )
                page.locator("[name=whatsapp_opt_in]").check()
                page.get_by_role("button", name="Review your order").click()
                expect(page.locator("main")).to_contain_text("14.60")
                shot("v4-final-review")
                page.get_by_role(
                    "button", name="Confirm & prepare WhatsApp order"
                ).click()
                expect(page.locator("main")).to_contain_text(
                    "Pending WhatsApp Submission"
                )
                # Do not click the external WhatsApp link.
                checks.append(
                    "Quick add, bundle component summary, promotion, saved-address checkout, explicit consent and manual-Send pending confirmation"
                )
                goto("/account")
                expect(page.locator("main")).to_contain_text("LUX-")
                shot("account-profile-history-desktop")
                page.get_by_role("button", name="Reorder at current prices").click()
                expect(page.locator("main")).to_contain_text("Synthetic pair")
                checks.append(
                    "Authenticated order history and reordering rebuild current server-priced cart"
                )
                customer_page = page
                admin_context = browser.new_context(
                    viewport={"width": 1366, "height": 900}, reduced_motion="reduce"
                )
                admin_page = admin_context.new_page()
                admin_page.on("pageerror", lambda e: errors.append(str(e)))
                admin_page.on("dialog", lambda d: d.accept())
                page = admin_page
                goto("/admin/login")
                page.fill("[name=username]", "synthetic-admin")
                page.fill("[name=password]", admin_password)
                page.get_by_role("button", name="Sign in").click()
                goto("/admin/orders/1")
                page.select_option("[name=status]", "Confirmed")
                page.get_by_role("button", name="Update status").click()
                with app.app_context():
                    process_one()
                    assert (
                        db().execute("SELECT state FROM whatsapp_jobs").fetchone()[0]
                        == "mocked"
                    )
                    assert (
                        db()
                        .execute("SELECT stock FROM variants WHERE id=1")
                        .fetchone()[0]
                        == 47
                    )
                goto("/admin/whatsapp")
                expect(page.locator("main")).to_contain_text("mocked")
                shot("whatsapp-automation-desktop")
                checks.append(
                    "Staff confirmation deducts normal and bundle stock exactly; durable worker reports MOCK with no real send"
                )
                for path in [
                    "/admin/",
                    "/admin/inventory",
                    "/admin/customers",
                    "/admin/customers/1",
                    "/admin/promotions",
                    "/admin/bundles",
                    "/admin/website",
                    "/admin/website/preview",
                    "/admin/whatsapp",
                    "/admin/reports",
                    "/admin/settings",
                ]:
                    goto(path)
                goto("/admin/inventory")
                shot("inventory-desktop")
                goto("/admin/reports")
                shot("reports-desktop")
                goto("/admin/")
                shot("v4-dashboard-desktop")
                for width in [320, 390, 768, 1366]:
                    customer_page.set_viewport_size({"width": width, "height": 844})
                    admin_page.set_viewport_size({"width": width, "height": 844})
                    for path in [
                        "/account",
                        "/favorites",
                        "/bundles",
                        "/account/login",
                        "/account/recover",
                        "/cart",
                        "/checkout",
                        "/admin/inventory",
                        "/admin/customers",
                        "/admin/promotions",
                        "/admin/bundles",
                        "/admin/website",
                        "/admin/whatsapp",
                        "/admin/reports",
                    ]:
                        page = (
                            admin_page if path.startswith("/admin") else customer_page
                        )
                        goto(path)
                page = customer_page
                checks.append(
                    "New account/favorites/bundle/admin pages responsive at 320,390,768,1366 pixels without body overflow"
                )
                page.set_viewport_size({"width": 390, "height": 844})
                goto("/")
                shot("v4-published-home-mobile")
                goto("/account")
                shot("account-profile-history-mobile")
                page.locator('.header [action="/language"] button').click()
                for path in ["/", "/favorites", "/bundles", "/account", "/checkout"]:
                    goto(path)
                    assert page.locator("html").get_attribute("dir") == "rtl"
                goto("/")
                shot("v4-arabic-home-mobile")
                goto("/account")
                shot("account-arabic-mobile")
                checks.append(
                    "Arabic RTL account, favorites, bundles, home and checkout render without overflow"
                )
                assert not errors, errors
                report = {
                    "checks": checks,
                    "javascript_errors": errors,
                    "real_whatsapp_sends": 0,
                }
                (OUTPUT / "v4-feature-browser-report.json").write_text(
                    json.dumps(report, indent=2) + "\n"
                )
                print(json.dumps(report, indent=2))
                browser.close()
        finally:
            server.shutdown()


if __name__ == "__main__":
    main()
