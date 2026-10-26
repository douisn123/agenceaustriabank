"""Danubia Bank brand mark: a gold "D" with the Danube flowing through it. Shared by PDFs (reportlab)."""
from math import pi, sin
from pathlib import Path

from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

NAVY, GOLD, RIVER, FOAM = "#0B192C", "#D4AF37", "#7FA7D9", "#F8FAFC"
WAVES = [(42, RIVER), (50, FOAM)]  # baseline y (64-unit box, y down), colour

FONT = "Helvetica-Bold"
_font = Path(__file__).parent / "static" / "fonts" / "PlusJakartaSans-ExtraBold.ttf"
if _font.exists():
    pdfmetrics.registerFont(TTFont("PJS-ExtraBold", str(_font)))
    FONT = "PJS-ExtraBold"


def wave_y(x, base):
    return base - 2.5 * sin(pi * (x - 4) / 8)


def draw_mark(c, x, y, size):
    """Draw the mark with its bottom-left corner at (x, y) on a reportlab canvas."""
    k = size / 64.0
    P = lambda px, py: (x + px * k, y + (64 - py) * k)  # noqa: E731
    c.saveState()
    c.setFillColor(colors.HexColor(NAVY))
    c.roundRect(x, y, size, size, 14 * k, stroke=0, fill=1)
    clip = c.beginPath()
    clip.roundRect(x, y, size, size, 14 * k)
    c.clipPath(clip, stroke=0, fill=0)
    c.setLineCap(1)
    c.setLineJoin(1)
    d = c.beginPath()
    d.moveTo(*P(19, 13))
    d.lineTo(*P(30, 13))
    d.arcTo(*P(11, 51), *P(49, 13), startAng=90, extent=-180)
    d.lineTo(*P(19, 51))
    d.close()
    c.setStrokeColor(colors.HexColor(GOLD))
    c.setLineWidth(6 * k)
    c.drawPath(d, stroke=1, fill=0)
    for base, col in WAVES:
        w = c.beginPath()
        w.moveTo(*P(4, wave_y(4, base)))
        for i in range(5, 61):
            w.lineTo(*P(i, wave_y(i, base)))
        for width, stroke in [(8, NAVY), (3, col)]:
            c.setStrokeColor(colors.HexColor(stroke))
            c.setLineWidth(width * k)
            c.drawPath(w, stroke=1, fill=0)
    c.restoreState()


def draw_logo(c, x, y, size, light=True):
    """Mark + wordmark; (x, y) is the bottom-left of the mark."""
    draw_mark(c, x, y, size)
    c.setFillColor(colors.white if light else colors.HexColor(NAVY))
    c.setFont(FONT, size * 0.52)
    c.drawString(x + size * 1.25, y + size * 0.36, "Danubia")
    c.setFillColor(colors.HexColor(GOLD))
    c.setFont(FONT, size * 0.2)
    c.drawString(x + size * 1.27, y + size * 0.06, "B  A  N  K")
