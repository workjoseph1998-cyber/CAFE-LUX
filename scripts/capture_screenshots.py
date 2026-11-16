"""Explore-only browser acceptance on an actual disposable Flask application."""

import json
import secrets
import sys
import tempfile
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cafe import create_app
from cafe.db import db
from playwright.sync_api import sync_playwright, expect
from werkzeug.serving import make_server
from werkzeug.security import generate_password_hash

ROOT = Path(__file__).resolve().parents[1]


def main():
    with tempfile.TemporaryDirectory(prefix="lux-explore-") as data:
        app = create_app(
            {
                "TESTING": True,
                "DATA_DIR": data,
                "SESSION_COOKIE_SECURE": False,
                "SEED_STARTER_CATALOG": True,
            }
        )
        password = secrets.token_urlsafe(24)
        with app.app_context():
            c = db()
            c.execute(
                "INSERT INTO users(username,password) VALUES (?,?)",
                ("screenshot-admin", generate_password_hash(password)),
            )
            c.execute(
                "UPDATE settings SET value='TEST PREVIEW · Synthetic prices for illustration only' WHERE key='banner'"
            )
            c.execute("UPDATE variants SET price=375")
            ground = c.execute(
                "SELECT id FROM products WHERE name='House Blend'"
            ).fetchone()[0]
            c.execute(
                "UPDATE variants SET price=625 WHERE product_id=? AND grams=500",
                (ground,),
            )
            espresso = c.execute(
                "SELECT id FROM products WHERE name='Espresso'"
            ).fetchone()[0]
            c.commit()
        server = make_server("127.0.0.1", 0, app, threaded=True)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        output = ROOT / "screenshots"
        output.mkdir(exist_ok=True)
        # Replace only generated screenshots/report; never touch user/runtime data.
        for file in output.glob("*.png"):
            file.unlink()
        (output / "browser-report.json").unlink(missing_ok=True)
        checks = []
        errors = []
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
            base = f"http://127.0.0.1:{server.server_port}"

            def goto(path):
                response = page.goto(base + path)
                assert response.status == 200, (path, response.status)
                page.wait_for_load_state("networkidle")
                assert page.locator("body").evaluate(
                    "(e)=>e.scrollWidth<=innerWidth"
                ), path + " overflows"
                assert (
                    page.locator(
                        'a[href="/cart"],a[href="/checkout"],form[action="/cart/add"]'
                    ).count()
                    == 0
                )

            def shot(name):
                page.locator("img").evaluate_all(
                    "imgs => imgs.forEach(i => i.loading = 'eager')"
                )
                for attempt in range(100):
                    if page.evaluate(
                        "() => Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)"
                    ):
                        break
                    page.wait_for_timeout(50)
                else:
                    raise AssertionError("A screenshot image did not load")
                page.screenshot(path=str(output / (name + ".png")), full_page=True)

            goto("/")
            shot("01-home-desktop")
            page.set_viewport_size({"width": 390, "height": 844})
            goto("/")
            shot("02-home-mobile")
            page.locator(".menu-toggle").click()
            expect(page.locator("#navigation")).to_be_visible()
            page.locator(".menu-toggle").click()
            checks.append("Mobile navigation and no public ordering links")
            for width in [320, 375, 390, 768, 1024, 1440]:
                page.set_viewport_size({"width": width, "height": 950})
                for path in ["/shop", "/shop?kind=ground", f"/product/{espresso}"]:
                    goto(path)
            checks.append("No horizontal overflow at 320/375/390/768/1024/1440")
            page.set_viewport_size({"width": 1440, "height": 1000})
            goto("/shop")
            expect(page.locator(".product-card")).to_have_count(15)
            shot("03-drinks")
            page.locator(".category-chips").get_by_role(
                "link", name="Iced Coffee", exact=True
            ).click()
            page.wait_for_load_state("networkidle")
            expect(page.locator(".product-card")).to_have_count(4)
            page.fill("#menu-search", "nonexistentchoice")
            page.get_by_role("button", name="Search", exact=True).click()
            expect(page.locator("main")).to_contain_text("No matches")
            page.get_by_role("link", name="Clear filters").first.click()
            expect(page.locator(".product-card")).to_have_count(15)
            checks.append("Category buttons, item counts, search and clear filters")
            goto("/shop?kind=ground")
            expect(page.locator(".product-card")).to_have_count(4)
            card = page.locator(".product-card").filter(
                has=page.get_by_role("heading", name="House Blend", exact=True)
            )
            option = (
                card.locator("option").filter(has_text="500 g").get_attribute("value")
            )
            card.locator("select").select_option(option)
            expect(card.locator("output")).to_have_text("USD 6.25")
            shot("04-ground-coffee")
            checks.append(
                "Weight selection previews configured price without an order request"
            )
            goto(f"/product/{espresso}")
            expect(page.locator("main")).to_contain_text("Sizes & prices")
            shot("05-product-detail")
            page.set_viewport_size({"width": 390, "height": 844})
            goto("/shop")
            shot("06-menu-mobile")
            page.locator("button[name=lang]").click()
            goto("/shop")
            assert page.locator("html").get_attribute("dir") == "rtl"
            shot("07-menu-arabic")
            checks.append("Arabic RTL explore flow")
            for path in ["/cart", "/checkout", "/order/anything"]:
                assert page.request.get(base + path).status == 404
            assert (
                page.request.post(
                    base + "/cart/add", form={"variant": "1", "qty": "1"}
                ).status
                == 404
            )
            assert (
                page.request.post(base + "/checkout", form={"name": "Synthetic"}).status
                == 404
            )
            checks.append(
                "Public cart, checkout, order confirmation and submissions rejected"
            )
            # Switch back before capturing the administration screens.
            page.locator("button[name=lang]").click()
            page.set_viewport_size({"width": 1440, "height": 1000})
            goto("/admin/login")
            page.fill("[name=username]", "screenshot-admin")
            page.fill("[name=password]", password)
            page.get_by_role("button", name="Sign in").click()
            page.wait_for_url("**/admin/")
            shot("08-admin-dashboard")
            goto("/admin/products")
            shot("09-product-management")
            for path in ["/admin/settings", "/admin/media", "/admin/categories"]:
                goto(path)
            checks.append(
                "Admin login/catalog/settings/media/categories remain functional"
            )
            motion = browser.new_context(reduced_motion="no-preference")
            animated = motion.new_page()
            animated.goto(base + "/")
            animated.wait_for_timeout(200)
            names = animated.evaluate(
                "document.getAnimations().map(a=>a.animationName)"
            )
            assert all(x in names for x in ["pour", "steam", "grind", "sip"])
            motion.close()
            browser.close()
            checks.append("Coffee animations retained; reduced-motion screenshots")
        server.shutdown()
        thread.join()
        assert not errors, errors
        report = dict(
            result="PASS",
            browser="Chromium (Linux)",
            mode="Explore only",
            checks=checks,
            javascript_errors=errors,
        )
        (output / "browser-report.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
