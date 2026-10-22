"""End-to-end check of the viewer in headless Chromium (software WebGL). Saves screenshots to results/figures."""
import functools
import json
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
FIG = ROOT / "results" / "figures"


def main():
    handler = functools.partial(SimpleHTTPRequestHandler, directory=str(ROOT / "web"))
    handler.log_message = lambda *a: None
    srv = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{srv.server_port}/index.html"
    errors, out = [], {}
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=swiftshader", "--enable-unsafe-swiftshader"])
        page = b.new_page(viewport={"width": 1400, "height": 860})
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.goto(url)
        page.wait_for_function("window.app && window.app.state.ready", timeout=60000)
        out["points"] = page.evaluate("app.state.points")
        page.wait_for_timeout(800)
        page.screenshot(path=str(FIG / "viewer_overview.png"))
        assert page.evaluate("app.select('R2')")
        page.wait_for_timeout(900)
        out["panel_visible"] = page.is_visible("#panel")
        out["panel_has_kpis"] = page.locator(".kpi").count()
        page.screenshot(path=str(FIG / "viewer_equipment.png"))
        page.fill("#search", "centrale")
        page.press("#search", "Enter")
        page.wait_for_timeout(900)
        out["search_selected"] = page.evaluate("app.state.selected.data.tag")
        page.click("[data-proc='P-HPU-FILTER']")
        page.wait_for_timeout(300)
        page.click("#next")
        page.wait_for_timeout(900)
        out["step_text"] = page.inner_text("#step-text")
        page.screenshot(path=str(FIG / "viewer_procedure.png"))
        for _ in range(5):
            page.click("#next")
        out["procedure_closed"] = not page.is_visible("#steps")
        page.evaluate("app.addMeasurePoint(-1.6,0.8,0); app.addMeasurePoint(1.6,0.8,0)")
        out["toast"] = page.inner_text("#toast")
        out["log_events"] = page.evaluate("app.state.log.map(e => e.event)")
        out["step_events"] = sum(1 for e in out["log_events"] if e == "step_done")
        page.set_viewport_size({"width": 390, "height": 800})
        page.evaluate("app.select('CV1')")
        page.wait_for_timeout(900)
        page.screenshot(path=str(FIG / "viewer_mobile.png"))
        b.close()
    srv.shutdown()
    out["errors"] = errors
    print(json.dumps(out, ensure_ascii=False, indent=1))
    ok = (out["points"] > 100000 and out["panel_visible"] and out["panel_has_kpis"] == 6
          and out["search_selected"] == "HPU" and out["procedure_closed"] and out["step_events"] == 6
          and "3.20 m" in out["toast"] and not errors)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
