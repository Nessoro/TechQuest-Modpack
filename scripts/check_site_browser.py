"""Developer-only browser checks; serve the existing Pages site locally."""
import functools
import json
import os
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    output = ROOT / "output/site-preview"
    output.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(QuietHandler, directory=str(ROOT / "docs"))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = "http://127.0.0.1:%s/" % server.server_port
    try:
        with sync_playwright() as playwright:
            executable = os.environ.get("TECHQUEST_BROWSER_PATH") or shutil.which("chromium")
            browser = playwright.chromium.launch(executable_path=executable, args=["--no-sandbox"])
            context = browser.new_context(viewport={"width": 1440, "height": 1000}, device_scale_factor=1)

            def github(route):
                if "/releases/tags/" in route.request.url:
                    data = {"published_at": "2026-11-11T12:00:00Z",
                            "assets": [{"name": "TechQuestInstaller.exe", "state": "uploaded",
                                "browser_download_url": "https://github.com/Nessoro/TechQuest-Modpack/releases/download/v0.3.3-micro1-preview/TechQuestInstaller.exe"}]}
                else:
                    data = [{"number": 21, "title": "<script>bad()</script> Обновление установщика",
                             "html_url": "https://github.com/Nessoro/TechQuest-Modpack/issues/21",
                             "created_at": "2026-11-08T12:00:00Z", "labels": []}]
                route.fulfill(json=data)

            context.route("https://api.github.com/**", github)
            page = context.new_page()
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.add_init_script("window.open=(url)=>{window.__draft=url;return null}")
            page.goto(url, wait_until="networkidle")
            assert page.locator(".mod-card").count() == 12
            assert page.locator("#download-link").get_attribute("href").endswith("/releases/download/v0.3.3-micro1-preview/TechQuestInstaller.exe")
            assert "<script>bad()</script>" in page.locator("#issues-feed").inner_text()
            assert page.locator("#issues-feed script").count() == 0
            page.screenshot(path=str(output / "desktop.png"))
            page.locator("#download").screenshot(path=str(output / "download.png"))
            page.locator("#feedback").screenshot(path=str(output / "feedback.png"))
            page.evaluate("scrollTo(0,0)")
            for width in (360, 390, 768, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
                if width == 390:
                    page.screenshot(path=str(output / "mobile.png"))
            page.locator("#show-all-mods").click()
            count = page.evaluate("window.TQ_MODS.length")
            assert page.locator(".mod-card").count() == count
            page.locator("#mod-search").fill("Aquamirae")
            assert "Aquamirae" in page.locator(".mod-card h3").all_text_contents()
            page.locator("#mod-search").fill("not-a-real-mod-0")
            assert page.locator(".mod-card").count() == 0
            assert "Ничего не найдено" in page.locator("#mods-grid").inner_text()
            page.locator("#mod-search").fill("")
            page.locator('[data-category="Мобы"]').click()
            assert page.locator('[data-category="Мобы"]').get_attribute("aria-pressed") == "true"
            assert page.locator(".mod-card").count() > 0
            assert all(t == "Мобы" for t in page.locator(".mod-card .category").all_text_contents())
            for form_id in ("bug-form", "mod-form"):
                form = page.locator("#" + form_id)
                form.locator('[name="title"]').fill("Проверка формы")
                form.locator('[name="details"]').fill("Подробное описание проблемы для проверки формы.")
                form.locator('[type="submit"]').click()
                draft = page.evaluate("window.__draft")
                assert draft.startswith("https://github.com/Nessoro/TechQuest-Modpack/issues/new?")
                assert "body=" in draft and "title=" in draft
            for anchor in page.locator('a[href^="#"]').all():
                target = anchor.get_attribute("href")[1:]
                assert page.locator('[id="%s"]' % target).count() == 1, target
            # API failure keeps a usable download link and a direct Issues link.
            context.unroute("https://api.github.com/**", github)
            context.route("https://api.github.com/**", lambda route: route.fulfill(status=403, json={}))
            page.reload(wait_until="networkidle")
            assert "Не удалось" in page.locator("#build-status").inner_text()
            assert "недоступны" in page.locator("#issues-feed").inner_text()
            assert "/releases" in page.locator("#download-link").get_attribute("href")
            assert not errors, errors
            context.close()
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page()
            page.goto(url)
            assert page.locator("#download-link").is_visible()
            assert page.locator("noscript").is_visible()
            context.close()
            browser.close()
            print(json.dumps({"catalog_entries": count, "widths": [360, 390, 768, 1024, 1440],
                              "forms": 2, "api_success_and_failure": True, "no_javascript_fallback": True,
                              "page_errors": errors, "screenshots": str(output)}, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
