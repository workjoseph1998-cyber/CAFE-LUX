"""V2.1 browser acceptance. All accounts, prices and orders live in disposable data."""

import io
import json
import secrets
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PIL import Image
from cafe import create_app
from cafe.db import db
from cafe.starter_catalog import seed_catalog
from werkzeug.security import generate_password_hash
from werkzeug.serving import make_server
from playwright.sync_api import sync_playwright, expect

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "screenshots" / "final"


def main():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="lux21-browser-") as data:
        app = create_app(
            {"TESTING": True, "DATA_DIR": data, "SESSION_COOKIE_SECURE": False}
        )
        password = secrets.token_urlsafe(24)
        with app.app_context():
            seed_catalog()
            conn = db()
            conn.execute(
                "INSERT INTO users(username,password) VALUES (?,?)",
                ("synthetic-admin", generate_password_hash(password)),
            )
            conn.execute(
                "UPDATE settings SET value='SYNTHETIC TEST PREVIEW · Not real offers' WHERE key='banner'"
            )
            conn.execute(
                "INSERT INTO whatsapp_numbers(label,phone,is_default) VALUES ('Synthetic test receiver','+96171111111',1)"
            )
            conn.execute(
                "INSERT INTO delivery_areas(name,fee) VALUES ('Synthetic area',250)"
            )
            for n in range(24):
                status = [
                    "Pending WhatsApp Submission",
                    "Received",
                    "Confirmed",
                    "Preparing",
                    "Ready",
                    "Out for Delivery",
                    "Delivered",
                ][n % 7]
                items = [
                    dict(
                        variant=1,
                        product=1,
                        name="Synthetic test coffee",
                        label="Single serving",
                        grind="",
                        temperature="hot",
                        addons=[],
                        qty=1,
                        unit=375,
                        total=375,
                    )
                ]
                conn.execute(
                    "INSERT INTO orders(reference,token,status,name,phone,address,fulfillment,currency,subtotal,delivery,total,items,area,receiving_phone,stock_deducted) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,0)",
                    (
                        f"SYNTHETIC-{n+1:04d}",
                        secrets.token_urlsafe(20),
                        status,
                        f"Synthetic Customer {n+1}",
                        "+96171111111",
                        "Fictional test street / test building",
                        "delivery",
                        "USD",
                        375,
                        250,
                        625,
                        json.dumps(items),
                        "Synthetic area",
                        "+96171111111",
                    ),
                )
            conn.commit()
            espresso = dict(
                conn.execute("SELECT * FROM products WHERE name='Espresso'").fetchone()
            )
            variant = dict(
                conn.execute(
                    "SELECT * FROM variants WHERE product_id=?", (espresso["id"],)
                ).fetchone()
            )
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_port}"
        errors = []
        checks = []
        measurements = []
        try:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    executable_path="/usr/bin/chromium",
                    headless=True,
                    args=["--no-sandbox"],
                )
                context = browser.new_context(
                    viewport={"width": 1366, "height": 768}, reduced_motion="reduce"
                )
                page = context.new_page()
                page.on("pageerror", lambda e: errors.append(str(e)))
                page.on("dialog", lambda d: d.accept())

                def goto(path):
                    response = page.goto(base + path)
                    assert response.status == 200, (path, response.status)
                    page.wait_for_load_state("networkidle")
                    assert page.locator("body").evaluate(
                        "(e)=>e.scrollWidth<=innerWidth"
                    ), (path + " body overflow")

                def shot(name, full=False):
                    if full:
                        page.locator("img").evaluate_all(
                            "async images => { images.forEach(image => image.loading = 'eager'); await Promise.all(images.map(image => image.decode())); }"
                        )
                    page.screenshot(path=str(OUTPUT / (name + ".png")), full_page=full)

                goto("/")
                assert "Double Espresso" not in page.locator("main").inner_text()
                shot("storefront-desktop", True)
                page.set_viewport_size({"width": 390, "height": 844})
                goto("/")
                shot("storefront-mobile", True)
                goto("/drinks")
                expect(page.locator("main")).to_contain_text(
                    "Our collection is being prepared."
                )
                goto("/coffee")
                expect(page.locator("main")).to_contain_text(
                    "Our collection is being prepared."
                )
                checks.append(
                    "Draft catalog hidden from home, drinks and coffee; public design retained"
                )
                page.set_viewport_size({"width": 1366, "height": 768})
                goto("/admin/login")
                page.fill("[name=username]", "synthetic-admin")
                page.fill("[name=password]", password)
                page.get_by_role("button", name="Sign in").click()
                page.wait_for_url("**/admin/")
                for width, height in [(1366, 768), (1440, 900), (1920, 1080)]:
                    page.set_viewport_size({"width": width, "height": height})
                    for path, name in [
                        ("/admin/", "dashboard"),
                        ("/admin/drinks", "drinks-table"),
                        ("/admin/coffee", "coffee-table"),
                        ("/admin/products/" + str(espresso["id"]), "product-editor"),
                        ("/admin/orders", "orders-table"),
                    ]:
                        goto(path)
                        shot(f"{name}-{width}")
                        if "table" in name:
                            visible = page.locator("tbody>tr").evaluate_all(
                                "(rows)=>rows.filter(r=>{const b=r.getBoundingClientRect();return b.top>=0&&b.bottom<=innerHeight;}).length"
                            )
                            measurements.append(
                                {
                                    "viewport": f"{width}x{height}",
                                    "page": path,
                                    "visible_rows": visible,
                                }
                            )
                            assert visible >= 4, (path, width, visible)
                            assert all(
                                page.locator("thead th").nth(i).is_visible()
                                for i in range(page.locator("thead th").count())
                            )
                checks.append(
                    "Dashboard, product/editor and order tables at 1366x768,1440x900,1920x1080; columns accessible"
                )
                page.set_viewport_size({"width": 1366, "height": 768})
                goto("/admin/drinks")
                page.get_by_role("button", name="Toggle sidebar").click()
                expect(page.locator("#admin-layout")).to_have_class(
                    "admin-layout is-collapsed"
                )
                page.reload()
                expect(page.locator("#admin-layout")).to_have_class(
                    "admin-layout is-collapsed"
                )
                assert page.locator('.admin-sidebar a[title="Drinks"]').is_visible()
                shot("sidebar-collapsed-1366")
                page.select_option("#table-density", "comfortable")
                page.reload()
                assert (
                    page.locator("body").get_attribute("data-density") == "comfortable"
                )
                page.select_option("#table-density", "compact")
                page.get_by_role("button", name="Toggle sidebar").click()
                checks.append(
                    "Sidebar collapse/expand, icon tooltips and density preferences survive reload"
                )
                goto("/admin/catalog-preview")
                expect(page.locator("main")).to_contain_text(
                    "Short, concentrated coffee."
                )
                page.get_by_role(
                    "button", name="Add sample images & descriptions"
                ).click()
                page.wait_for_load_state("networkidle")
                expect(page.locator(".flash")).to_contain_text("22 sample images added")
                assert page.locator(".product-grid .product-card").count() == 18
                assert page.locator(".product-grid img").first.evaluate(
                    "(image)=>image.complete&&image.naturalWidth>0"
                )
                shot("catalog-preview-drinks-desktop", True)
                goto("/admin/catalog-preview?kind=ground")
                assert page.locator(".product-grid .product-card").count() == 4
                shot("catalog-preview-coffee-desktop", True)
                page.set_viewport_size({"width": 390, "height": 844})
                goto("/admin/catalog-preview?kind=drink")
                shot("catalog-preview-drinks-mobile", True)
                page.set_viewport_size({"width": 1366, "height": 768})
                checks.append(
                    "One-click sample preparation, 22 small served images, full descriptions, private desktop/mobile catalog preview; drafts remain unpublished"
                )
                goto("/admin/drinks")

                page.fill("[name=q]", "Iced")
                page.select_option("[name=status]", "draft")
                page.get_by_role("button", name="Apply", exact=True).click()
                expect(page.locator("tbody")).to_contain_text("Iced Mocha")
                assert "Cappuccino" not in page.locator("tbody").inner_text()
                page.locator("#select-all").check()
                expect(page.locator("#selected-count")).to_contain_text("4 selected")
                page.get_by_role("button", name="Apply to selection").click()
                page.wait_for_url("**/admin/products")
                expect(page.locator(".flash")).to_contain_text("Updated 4 product(s).")
                checks.append(
                    "Product search, draft filter, selection and validated bulk drafting"
                )
                goto("/admin/products/" + str(espresso["id"]))
                # Unsaved-change state, then save edited review copy.
                page.fill(
                    "#product-editor [name=description]",
                    "Synthetic reviewed description for browser testing only.",
                )
                expect(page.locator("#save-state")).to_contain_text("Unsaved changes")
                page.get_by_role("button", name="Save product", exact=True).click()
                page.wait_for_load_state("networkidle")
                # Upload a synthetic image through the actual product editor.
                page.locator("#upload-photo>summary").click()
                image = io.BytesIO()
                Image.new("RGB", (80, 80), "#8d5a3b").save(image, "PNG")
                page.locator("#upload-photo [name=upload]").set_input_files(
                    {
                        "name": "synthetic.png",
                        "mimeType": "image/png",
                        "buffer": image.getvalue(),
                    }
                )
                page.get_by_role("button", name="Upload & assign photo").click()
                page.wait_for_load_state("networkidle")
                fid = "variant-" + str(variant["id"])
                page.fill(f'input[form="{fid}"][name=price]', "3.75")
                page.check(f'input[form="{fid}"][name=active]')
                page.locator("#" + fid + " button").click()
                page.wait_for_load_state("networkidle")
                page.get_by_role("button", name="Publish product", exact=True).click()
                page.wait_for_load_state("networkidle")
                expect(page.locator(".page-heading")).to_contain_text("Published")
                checks.append(
                    "Editor dirty-state warning, reviewed draft save, photo upload, independent variant price and valid publish"
                )
                goto("/drinks")
                expect(page.locator("main")).to_contain_text("Espresso")
                goto("/product/" + str(espresso["id"]))
                page.select_option("[name=variant]", str(variant["id"]))
                page.get_by_role("button", name="Add to bag").click()
                page.wait_for_url("**/cart")
                expect(page.locator(".cart-total")).to_contain_text("3.75")
                checks.append(
                    "Published starter appears only in drinks and can enter the validated cart"
                )
                goto("/admin/orders")
                page.locator("[data-inspect]").first.click()
                expect(page.locator("#order-inspector")).to_be_visible()
                expect(page.locator("#order-panel-content")).to_contain_text(
                    "Fictional test street"
                )
                shot("order-inspector-1366")
                page.get_by_role("button", name="Close order details").click()
                page.locator(".order-row").first.get_by_role(
                    "link", name="Details", exact=True
                ).click()
                page.wait_for_load_state("networkidle")
                page.select_option(".order-detail [name=status]", "Received")
                page.get_by_role("button", name="Update status", exact=True).click()
                page.wait_for_url("**/admin/orders")
                checks.append(
                    "Order inspector displays private details; full detail status update works without claiming WhatsApp delivery"
                )
                for path in [
                    "/admin/categories",
                    "/admin/operations",
                    "/admin/media",
                    "/admin/settings",
                    "/admin/users",
                ]:
                    goto(path)
                goto("/admin/operations")
                shot("operations-1366")
                page.set_viewport_size({"width": 390, "height": 844})
                for path in [
                    "/admin/",
                    "/admin/drinks",
                    "/admin/coffee",
                    "/admin/products/" + str(espresso["id"]),
                    "/admin/orders",
                    "/admin/operations",
                ]:
                    goto(path)
                goto("/admin/drinks")
                page.get_by_role("button", name="Toggle sidebar").click()
                assert page.locator("#admin-layout").evaluate(
                    '(e)=>e.classList.contains("menu-open")'
                )
                shot("admin-mobile-navigation")
                checks.append(
                    "Compact forms, scrollable complete tables and mobile navigation at 390px"
                )
                page.set_viewport_size({"width": 1366, "height": 768})
                goto("/admin/catalog-preview")
                page.get_by_role(
                    "button", name="Fill missing info & publish all with sample prices"
                ).click()
                page.wait_for_url("**/drinks")
                guest = browser.new_context(
                    viewport={"width": 1366, "height": 768}, reduced_motion="reduce"
                )
                page = guest.new_page()
                page.on("pageerror", lambda error: errors.append(str(error)))
                goto("/drinks")
                expect(page.locator("main")).to_contain_text("Cappuccino")
                assert page.locator(".product-card").count() == 18
                shot("customer-drinks-desktop", True)
                goto("/coffee")
                assert page.locator(".product-card").count() == 4
                shot("customer-coffee-desktop", True)
                goto("/")
                shot("customer-home-desktop", True)
                page.set_viewport_size({"width": 390, "height": 844})
                goto("/drinks")
                shot("customer-drinks-mobile", True)
                goto("/coffee")
                shot("customer-coffee-mobile", True)
                checks.append(
                    "All 22 starter products published to anonymous customer catalogs with actual small images, descriptions, editable sample prices and featured homepage sections"
                )

                browser.close()
            assert not errors, errors
            report = {
                "result": "PASS",
                "browser": "Chromium Linux headless",
                "data": "Disposable synthetic fixtures; all demo prices, accounts and orders discarded",
                "checks": checks,
                "measurements": measurements,
                "javascript_errors": errors,
            }
            (OUTPUT / "browser-report.json").write_text(
                json.dumps(report, indent=2) + "\n"
            )
            print(json.dumps(report, indent=2))
        finally:
            server.shutdown()
            thread.join()


if __name__ == "__main__":
    main()
