from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
STYLE_GUIDE_DIR = REPO_ROOT / "docs" / "brand_style_extraction"
HTML_FILE = STYLE_GUIDE_DIR / "AXOLOTL_STYLE_GUIDE_V4.html"
PDF_FILE = STYLE_GUIDE_DIR / "AXOLOTL_STYLE_GUIDE_V4.pdf"
PNG_FILE = Path("/tmp/AXOLOTL_STYLE_GUIDE_V4.png")
TMP_PDF_FILE = Path("/tmp/AXOLOTL_STYLE_GUIDE_V4.pdf")


def detect_browser() -> str:
    candidates = [
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
    ]
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise RuntimeError("No supported Chromium browser found. Install Google Chrome or Brave.")


def render_pdf(browser: str) -> None:
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--allow-file-access-from-files",
            "--no-pdf-header-footer",
            f"--print-to-pdf={PDF_FILE}",
            HTML_FILE.as_uri(),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    shutil.copy2(PDF_FILE, TMP_PDF_FILE)


def render_png(browser: str) -> None:
    subprocess.run(
        [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--hide-scrollbars",
            "--allow-file-access-from-files",
            "--window-size=1400,1900",
            f"--screenshot={PNG_FILE}",
            HTML_FILE.as_uri(),
        ],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def main() -> None:
    browser = detect_browser()
    render_pdf(browser)
    render_png(browser)
    print(HTML_FILE)
    print(PDF_FILE)
    print(TMP_PDF_FILE)
    print(PNG_FILE)


if __name__ == "__main__":
    main()
