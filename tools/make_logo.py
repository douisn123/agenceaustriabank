"""Regenerates the PNG logos from static/logo-mark.svg with headless Chrome.
Run: python tools/make_logo.py  (needs google-chrome or chromium on PATH)."""
import shutil
import subprocess
import tempfile
from pathlib import Path

STATIC = Path(__file__).resolve().parent.parent / "static"
SVG = (STATIC / "logo-mark.png").read_text()
FONT = (STATIC / "fonts" / "PlusJakartaSans-ExtraBold.ttf").as_uri()

PAGE = """<html><head><style>
@font-face {{ font-family: PJS; src: url('{font}'); }}
html, body {{ margin: 0; background: transparent; }}
.logo {{ display: flex; align-items: center; gap: 22px; height: 96px; font-family: PJS; }}
.logo svg {{ width: 96px; height: 96px; }}
.name {{ font-size: 54px; line-height: 54px; color: {colour}; letter-spacing: -1px; }}
.bank {{ font-size: 18px; letter-spacing: 9px; color: #D4AF37; margin-top: 4px; }}
</style></head><body>{body}</body></html>"""

TARGETS = {
    "logo-mark.png": (256, 256, f'<div style="width:256px;height:256px">{SVG.replace("<svg ", "<svg width=256 height=256 ")}</div>', ""),
    "favicon.png": (64, 64, f'<div style="width:64px;height:64px">{SVG.replace("<svg ", "<svg width=64 height=64 ")}</div>', ""),
    "logo-email.png": (340, 96, f'<div class="logo">{SVG}<div><div class="name">Danubia</div><div class="bank">BANK</div></div></div>', "#FFFFFF"),
    "logo-light.png": (340, 96, f'<div class="logo">{SVG}<div><div class="name">Danubia</div><div class="bank">BANK</div></div></div>', "#0B192C"),
}


def main():
    chrome = shutil.which("google-chrome") or shutil.which("chromium") or shutil.which("chrome") or next(
        (p for p in [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                     r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                     "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"] if Path(p).exists()), None)
    with tempfile.TemporaryDirectory() as tmp:
        for name, (w, h, body, colour) in TARGETS.items():
            html = Path(tmp) / "logo.html"
            html.write_text(PAGE.format(font=FONT, colour=colour or "#0B192C", body=body))
            subprocess.run([chrome, "--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars",
                            "--default-background-color=00000000", "--force-device-scale-factor=2",
                            f"--window-size={w},{h}", f"--screenshot={STATIC / name}", html.as_uri()],
                           check=True, capture_output=True)
            print("written", name)


if __name__ == "__main__":
    main()
