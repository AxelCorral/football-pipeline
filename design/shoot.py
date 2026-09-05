"""Captures d'écran du dashboard — outil de revue, pas de production.

Usage : python design/shoot.py <dossier de sortie> [port]
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "design/after")
PORT = sys.argv[2] if len(sys.argv) > 2 else "8502"
URL = f"http://localhost:{PORT}"
PAGES = ["Overview", "Standings", "Prediction", "About"]

OUT.mkdir(parents=True, exist_ok=True)


def settle(page, ms: int = 2500) -> None:
    page.wait_for_timeout(ms)


with sync_playwright() as p:
    browser = p.chromium.launch()
    page = browser.new_page(viewport={"width": 1440, "height": 1000})
    page.goto(URL, wait_until="networkidle", timeout=60_000)
    settle(page, 5000)

    # Ce que le rendu nous apprend, une fois pour toutes.
    facts = page.evaluate(
        """() => {
        const btn = document.querySelector('[data-testid="stBaseButton-primary"]')
                 || document.querySelector('[data-testid="baseButton-primary"]');
        const body = getComputedStyle(document.body);
        const h1 = document.querySelector('h1');
        return {
          buttonTestId: btn ? btn.getAttribute('data-testid') : 'aucun bouton primaire sur cette page',
          bodyFont: body.fontFamily,
          bodyBg: body.backgroundColor,
          h1Font: h1 ? getComputedStyle(h1).fontFamily : null,
          appBg: getComputedStyle(document.querySelector('.stApp')).backgroundColor,
        };
    }"""
    )
    print("FAITS :", facts)

    for name in PAGES:
        try:
            page.get_by_text(name, exact=True).first.click(timeout=10_000)
        except Exception as exc:  # pragma: no cover - outil de revue
            print(f"  !! navigation vers {name} : {exc}")
            continue
        settle(page)
        if name == "Prediction":
            try:
                page.get_by_role("button", name="Predict").click(timeout=10_000)
                settle(page, 3500)
            except Exception as exc:
                print(f"  !! clic Predict : {exc}")
        path = OUT / f"{name.lower()}.png"
        page.screenshot(path=str(path), full_page=True)
        print(f"  {path}")

    browser.close()
