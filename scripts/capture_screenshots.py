"""Browser acceptance checks against a disposable synthetic database, never live data."""

import json
import secrets
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cafe import create_app
from cafe.db import db
from werkzeug.serving import make_server
from werkzeug.security import generate_password_hash
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="lux-browser-") as data:
        app = create_app(
            {"TESTING": True, "DATA_DIR": data, "SESSION_COOKIE_SECURE": False}
        )
        password = secrets.token_urlsafe(24)
        with app.app_context():
            conn = db()
            conn.execute(
                "INSERT INTO users(username,password) VALUES (?,?)",
                ("screenshot-admin", generate_password_hash(password)),
            )
            conn.execute(
                "UPDATE settings SET value='TEST PREVIEW · Synthetic catalog and test prices · Not real offers' WHERE key='banner'"
            )
            conn.execute(
                "UPDATE settings SET value='1' WHERE key IN ('ordering','delivery')"
            )
            for category, kind, names in [
                (
                    "Coffee drinks",
                    "drink",
                    ["Signature Latte", "Espresso", "Mocha", "Cold Brew"],
                ),
                (
                    "Packaged coffee",
                    "ground",
                    ["House Blend", "Arabic Coffee", "Espresso Blend", "Single Origin"],
                ),
            ]:
                cid = conn.execute(
                    "INSERT INTO categories(name) VALUES (?)", (category,)
                ).lastrowid
                for name in names:
                    pid = conn.execute(
                        "INSERT INTO products(name,name_ar,description,description_ar,kind,category_id,active,featured,grinds,temperature) VALUES (?,?,?,?,?,?,1,1,?,?)",
                        (
                            "TEST " + name,
                            "قهوة تجريبية",
                            "Synthetic sample for testing only. Replace this copy before publishing.",
                            "منتج تجريبي للاختبار فقط.",
                            kind,
                            cid,
                            "Whole beans,Fine,Medium" if kind == "ground" else "",
                            "both",
                        ),
                    ).lastrowid
                    for label, grams, price in (
                        [
                            ("100 g", 100, 211),
                            ("200 g", 200, 397),
                            ("250 g", 250, 499),
                            ("500 g", 500, 899),
                            ("1 kg", 1000, 1501),
                            ("375 g", 375, 701),
                        ]
                        if kind == "ground"
                        else [("Regular", None, 375), ("Large", None, 610)]
                    ):
                        conn.execute(
                            "INSERT INTO variants(product_id,label,label_ar,grams,price,stock) VALUES (?,?,?,?,?,25)",
                            (pid, label, "حجم تجريبي", grams, price),
                        )
                    if kind == "drink":
                        conn.execute(
                            "INSERT INTO addons(product_id,name,price) VALUES (?,?,125)",
                            (pid, "TEST extra shot"),
                        )
            conn.execute("INSERT INTO whatsapp_numbers(label,phone,is_default) VALUES ('Synthetic receiver','+96171123456',1)")
            conn.execute("INSERT INTO delivery_areas(name,fee) VALUES ('Synthetic test area',250)")
            conn.commit()
        server = make_server("127.0.0.1", 0, app, threaded=True)
        port = server.server_port
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        output = ROOT / "screenshots"
        output.mkdir(exist_ok=True)
        (output / "browser-report.json").unlink(missing_ok=True)
        errors = []
        checks = []
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path="/usr/bin/chromium",
                headless=True,
                args=["--no-sandbox"],
            )
            context = browser.new_context(
                viewport={"width": 1440, "height": 1000}, reduced_motion="reduce"
            )
            page = context.new_page()
            page.on("pageerror", lambda e: errors.append(str(e)))

            def goto(path):
                response = page.goto(f"http://127.0.0.1:{port}" + path)
                assert response.status == 200, (path, response.status)
                page.wait_for_load_state("networkidle")
                assert page.locator("body").evaluate(
                    "(e)=>e.scrollWidth<=window.innerWidth"
                ), path + " overflow"

            def shot(name):
                page.screenshot(path=str(output / (name + ".png")), full_page=True)

            goto("/")
            shot("01-home-desktop")
            checks.append("Desktop homepage and layout")
            page.set_viewport_size({"width": 390, "height": 844})
            goto("/")
            shot("02-home-mobile")
            page.locator(".menu-toggle").click()
            assert page.locator("#navigation").is_visible()
            page.locator(".menu-toggle").click()
            checks.append("Mobile navigation at 390px")
            for width in [320, 375, 768, 1024]:
                page.set_viewport_size({"width": width, "height": 900})
                for path in [
                    "/",
                    "/shop?kind=drink",
                    "/product/1",
                    "/cart",
                    "/admin/login",
                ]:
                    goto(path)
            checks.append("No horizontal overflow at 320/375/390/768/1024/1440px")
            page.set_viewport_size({"width": 1440, "height": 1000})
            goto("/drinks")
            shot("03-drinks")
            goto("/coffee")
            shot("04-ground-coffee")
            goto("/product/1")
            page.select_option("[name=variant]", "1")
            page.check("[name=addon]")
            page.fill("[name=qty]", "2")
            assert page.locator("#product-total").inner_text() == "USD 10.00"
            shot("05-product-detail")
            page.get_by_role("button", name="Add to bag").click()
            page.wait_for_url("**/cart")
            goto("/product/5")
            page.select_option("[name=variant]", "10")
            page.select_option("[name=grind]", "Fine")
            page.get_by_role("button", name="Add to bag").click()
            page.wait_for_url("**/cart")
            shot("06-cart")
            page.set_viewport_size({"width":390,"height":844})
            shot("06b-cart-mobile")
            page.set_viewport_size({"width":1440,"height":1000})
            assert "13.97" in page.locator(".cart-total").inner_text()
            checks.append("Mixed cart: drink sizes, extras, independent coffee weight and grind, quantity and totals")
            goto("/checkout")
            shot("07-checkout")
            page.set_viewport_size({"width":390,"height":844})
            shot("07b-checkout-mobile")
            page.set_viewport_size({"width":1440,"height":1000})
            page.fill("[name=name]", "Synthetic Customer")
            page.fill("[name=phone]", "+96171111111")
            page.fill("[name=address]", "Synthetic test street")
            page.fill("[name=building]", "Synthetic test building")
            page.select_option("[name=area]", "1")
            page.get_by_role("button", name="Review your order").click()
            expect(page.locator("main")).to_contain_text("Nothing has been submitted yet.")
            shot("13-order-review")
            page.get_by_role("button", name="Confirm & prepare WhatsApp order").click()
            page.wait_for_url("**/order/**")
            expect(page.locator("main")).to_contain_text("Pending WhatsApp Submission")
            shot("11-confirmation")
            checks.append("Guest checkout reviewed, persisted as pending, WhatsApp URL prepared (not sent)")
            goto("/admin/login")
            page.fill("[name=username]", "screenshot-admin")
            page.fill("[name=password]", password)
            page.get_by_role("button", name="Sign in").click()
            page.wait_for_url("**/admin/")
            shot("08-admin-dashboard")
            goto("/admin/products")
            shot("09-product-management")
            goto("/admin/orders")
            shot("10-order-management")
            page.select_option(".order-card select[name=status]", "Confirmed")
            page.get_by_role("button", name="Update status").click()
            page.wait_for_load_state("networkidle")
            assert page.locator(".order-card select[name=status]").input_value() == "Confirmed"
            checks.append("Admin login and order status update")
            for path in [
                "/admin/products/1",
                "/admin/settings",
                "/admin/categories",
                "/admin/media",
                "/admin/users",
                "/admin/operations",
            ]:
                goto(path)
            goto("/admin/operations")
            shot("14-admin-operations")
            page.set_viewport_size({"width": 390, "height": 844})
            shot("15-admin-operations-mobile")
            for path in [
                "/admin",
                "/admin/products/1",
                "/admin/settings",
                "/admin/orders",
            ]:
                goto(path)
            checks.append("Admin screens at mobile width")
            goto("/")
            page.locator("button[name=lang]").click()
            page.wait_for_load_state("networkidle")
            assert page.locator("html").get_attribute("dir") == "rtl"
            shot("12-arabic-mobile")
            checks.append("Arabic RTL and translation fallback")
            goto("/product/1")
            assert page.locator("html").get_attribute("lang") == "ar"
            # Reduced motion overrides all decorative CSS animations.
            assert page.locator(".header").evaluate(
                '(e)=>matchMedia("(prefers-reduced-motion: reduce)").matches'
            )
            assert (
                page.locator(".hero-motion").count() == 0
            )  # Product page has no hero.
            goto("/")
            assert page.locator(".hero-photo").evaluate("(e)=>getComputedStyle(e,'::after').animationName") == "none"
            checks.append("Reduced motion disables decorative steam")
            browser.close()
        server.shutdown()
        thread.join()
        assert not errors, errors
        report = {
            "browser": "Chromium (Linux)",
            "data": "Disposable synthetic fixtures only",
            "checks": checks,
            "javascript_errors": errors,
            "result": "PASS",
        }
        (output / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
