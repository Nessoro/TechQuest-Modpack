"""Developer-only browser checks; serve the existing Pages site locally."""
import functools
import json
import os
import shutil
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]
GH = "https://github.com/Nessoro/TechQuest-Modpack"
API = "https://api.github.com/repos/Nessoro/TechQuest-Modpack"
RELEASES = API + "/releases?per_page=30"
ISSUES = API + "/issues?state=open&per_page=15"
FALLBACK_TAG = "v0.3.3-micro2-preview"
MOCK_TAG = "v0.3.3.1-browser-test"
CORS = {"Access-Control-Allow-Origin": "*"}


def release_url(tag, filename):
    return f"{GH}/releases/download/{tag}/{filename}"


def mock_release(tag, date, filename="TechQuest_0.3.3.1.exe", draft=False):
    return {
        "tag_name": tag, "published_at": date, "draft": draft, "prerelease": True,
        "assets": [
            {"name": filename, "state": "uploaded", "size": 71000000,
             "browser_download_url": release_url(tag, filename)},
            {"name": "SHA256SUMS.txt", "state": "uploaded", "size": 196,
             "browser_download_url": release_url(tag, "SHA256SUMS.txt")},
        ],
    }


def check_download(page, tag, filename):
    expected = release_url(tag, filename)
    expect(page.locator("#download-link")).to_have_attribute("href", expected)
    for link in page.locator("[data-direct-installer]").all():
        expect(link).to_have_attribute("href", expected)
    expect(page.locator("#checksum-link")).to_have_attribute(
        "href", release_url(tag, "SHA256SUMS.txt"))
    print("Installer href:", page.locator("#download-link").get_attribute("href"))


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

            # Exact endpoint mocks: a Releases response is not an Actions run or an issue.
            older = mock_release(FALLBACK_TAG, "2026-11-13T12:00:00Z", "TechQuestInstaller.exe")
            chosen = mock_release(MOCK_TAG, "2026-11-20T12:00:00Z")
            draft = mock_release("v0.3.3.2-draft", "2026-11-24T12:00:00Z", draft=True)
            missing_checksum = mock_release("v0.3.3.2-missing", "2026-11-23T12:00:00Z")
            missing_checksum["assets"].pop()
            bad_url = mock_release("v0.3.3.2-bad-url", "2026-11-22T12:00:00Z")
            bad_url["assets"][0]["browser_download_url"] = GH + "/actions/runs/456/artifacts/123"
            incomplete = mock_release("v0.3.3.2-incomplete", "2026-11-21T12:00:00Z")
            incomplete["assets"][0]["state"] = "new"
            releases = [older, draft, missing_checksum, chosen, bad_url, incomplete]
            scenario = "success"
            requests = []
            unexpected = []
            errors = []

            def github(route):
                endpoint = route.request.url
                requests.append(endpoint)
                print("Mock GitHub API:", scenario, endpoint)
                if endpoint == RELEASES:
                    if scenario == "unavailable":
                        route.fulfill(status=403, json={}, headers=CORS)
                    else:
                        data = releases if scenario == "success" else [
                            draft, missing_checksum, bad_url, incomplete]
                        route.fulfill(json=data, headers=CORS)
                elif endpoint == ISSUES:
                    if scenario == "unavailable":
                        route.fulfill(status=403, json={}, headers=CORS)
                    else:
                        route.fulfill(json=[{"number": 21,
                            "title": "<script>bad()</script> Обновление установщика",
                            "html_url": GH + "/issues/21",
                            "created_at": "2026-11-08T12:00:00Z", "labels": []}], headers=CORS)
                elif endpoint.startswith(API + "/actions/"):
                    # Actions artifacts (including expired ones) must not replace
                    # the public installer. A regression gets a deterministic response.
                    unexpected.append(endpoint)
                    if "/artifacts" in endpoint:
                        route.fulfill(json={"artifacts": [{"id": 123,
                            "name": "TechQuest-Windows-GUI-Installer", "expired": True}]}, headers=CORS)
                    else:
                        route.fulfill(json={"workflow_runs": [{"id": 456,
                            "conclusion": "success", "html_url": GH + "/actions/runs/456"}]}, headers=CORS)
                else:
                    unexpected.append(endpoint)
                    route.fulfill(status=404, json={}, headers=CORS)

            context.route("https://api.github.com/**", github)
            page = context.new_page()
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.on("console", lambda message: print("Browser console:", message.type, message.text)
                    if message.type == "error" else None)
            page.on("requestfailed", lambda request: print("Request failed:", request.url, request.failure))
            page.on("response", lambda response: print("API response:", response.status, response.url)
                    if response.url.startswith(API) else None)
            page.add_init_script("window.open=(url)=>{window.__draft=url;return null}")
            page.goto(url, wait_until="domcontentloaded")
            expect(page.locator(".mod-card")).to_have_count(6)
            expect(page.locator("#build-status")).to_contain_text(MOCK_TAG)
            check_download(page, MOCK_TAG, "TechQuest_0.3.3.1.exe")
            assert RELEASES in requests and ISSUES in requests, requests
            assert not page.locator("#mods").evaluate("(el) => el.open")
            assert not page.locator("#feedback").evaluate("(el) => el.open")
            page.locator("#issues > summary").click()
            expect(page.locator("#issues-feed")).to_contain_text("<script>bad()</script>")
            assert page.locator("#issues-feed script").count() == 0
            page.locator("#issues > summary").click()
            page.screenshot(path=str(output / "desktop.png"))
            page.locator("#download").screenshot(path=str(output / "download.png"))
            page.locator("#feedback").screenshot(path=str(output / "feedback.png"))
            page.evaluate("scrollTo(0,0)")
            for width in (360, 390, 768, 1024, 1440):
                page.set_viewport_size({"width": width, "height": 900})
                assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
                if width == 390:
                    page.screenshot(path=str(output / "mobile.png"))
            page.locator("#mods > summary").click()
            page.locator("#show-all-mods").click()
            count = page.evaluate("window.TQ_MODS.length")
            assert page.locator(".mod-card").count() == count
            page.locator("#mod-search").fill("Aquamirae")
            assert "Aquamirae" in page.locator(".mod-card h3").all_text_contents()
            for query, name in (
                ("DragonRise", "[SBW] DragonRise: Reforge"),
            ):
                page.locator("#mod-search").fill(query)
                assert name in page.locator(".mod-card h3").all_text_contents()
                row = page.evaluate("(name) => window.TQ_MODS.find(m => m.name === name)", name)
                assert row["required"] is False
                assert "Не входит в автоматический .mrpack" in row["description"]
            page.locator("#mod-search").fill("AcceleratedMcWarfare")
            assert page.locator(".mod-card").count() == 0
            page.locator("#mod-search").fill("not-a-real-mod-0")
            assert page.locator(".mod-card").count() == 0
            assert "Ничего не найдено" in page.locator("#mods-grid").inner_text()
            page.locator("#mod-search").fill("")
            page.locator('[data-category="Мобы"]').click()
            assert page.locator('[data-category="Мобы"]').get_attribute("aria-pressed") == "true"
            assert page.locator(".mod-card").count() > 0
            assert all(t == "Мобы" for t in page.locator(".mod-card .category").all_text_contents())
            page.locator("#feedback > summary").click()
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
            # Without an eligible release, keep the public fallback even if the
            # only hypothetical Actions artifact has expired.
            scenario = "no_eligible_release"
            requests.clear()
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#build-status")).to_contain_text("Новый публичный установщик не найден")
            check_download(page, FALLBACK_TAG, "TechQuestInstaller.exe")
            assert RELEASES in requests, requests
            # API failures keep the public EXE and checksum, not a login-only Actions link.
            scenario = "unavailable"
            requests.clear()
            page.reload(wait_until="domcontentloaded")
            expect(page.locator("#build-status")).to_contain_text("Не удалось")
            if not page.locator("#issues").evaluate("(el) => el.open"):
                page.locator("#issues > summary").click()
            expect(page.locator("#issues-feed")).to_contain_text("недоступны")
            check_download(page, FALLBACK_TAG, "TechQuestInstaller.exe")
            expect(page.locator('a[href="' + GH + '/actions/workflows/build-alpha.yml"]')).to_have_count(1)
            assert RELEASES in requests and ISSUES in requests, requests
            assert not unexpected, unexpected
            assert not errors, errors
            context.close()
            context = browser.new_context(java_script_enabled=False)
            page = context.new_page()
            page.goto(url)
            expect(page.locator("#download-link")).to_be_visible()
            check_download(page, FALLBACK_TAG, "TechQuestInstaller.exe")
            expect(page.locator("noscript")).to_be_visible()
            context.close()
            browser.close()
            print(json.dumps({"catalog_entries": count, "widths": [360, 390, 768, 1024, 1440],
                              "forms": 2, "api_success_and_failure": True, "no_eligible_release_fallback": True,
                              "actions_artifacts_not_advertised": True, "no_javascript_fallback": True,
                              "page_errors": errors, "screenshots": str(output)}, ensure_ascii=False))
    finally:
        server.shutdown()
        server.server_close()


if __name__ == "__main__":
    main()
