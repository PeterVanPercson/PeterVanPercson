"""Contribution skyline for the profile README: a year of GitHub activity as an
isometric city, one bar per day, rising in a wave from the oldest week to the
newest when the image loads. Writes skyline-light.svg and skyline-dark.svg."""
import datetime as dt
import json
import math
import os
import subprocess
from pathlib import Path

USER = "PeterVanPercson"
OUT = Path(__file__).resolve().parent

THEMES = {
    "light": {"fg": "#1f2328", "muted": "#59636e", "border": "#d1d9e0", "empty": "#ebedf0",
              "levels": ["#9be9a8", "#40c463", "#30a14e", "#216e39"], "accent": "#216e39"},
    "dark": {"fg": "#f0f6fc", "muted": "#9198a1", "border": "#3d444d", "empty": "#21262d",
             "levels": ["#0e4429", "#006d32", "#26a641", "#39d353"], "accent": "#39d353"},
}

W, H = 880, 420
YAW, ELEV = math.pi / 4, math.radians(34)
CS, SN, SE, CE = math.cos(YAW), math.sin(YAW), math.sin(ELEV), math.cos(ELEV)
FONT = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"


def fetch():
    q = '{user(login:"%s"){contributionsCollection{contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}' % USER
    raw = subprocess.check_output(["gh", "api", "graphql", "-f", f"query={q}"])
    weeks = json.loads(raw)["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    return [(d["date"], d["contributionCount"]) for w in weeks for d in w["contributionDays"]]


def build(days):
    end = dt.date.fromisoformat(days[-1][0])
    counts = {d: c for d, c in days}
    start = end - dt.timedelta(days=364)
    start -= dt.timedelta(days=(start.weekday() + 1) % 7)
    cells, d, i = [], start, 0
    while d <= end:
        cells.append({"date": d, "count": counts.get(d.isoformat(), 0), "week": i // 7, "day": i % 7})
        d += dt.timedelta(days=1)
        i += 1
    nz = sorted(c["count"] for c in cells if c["count"] > 0)
    busy = nz[int(0.95 * (len(nz) - 1))] if nz else 0
    for c in cells:
        n = c["count"]
        c["level"] = 0 if n <= 0 else 4 if busy <= 0 else 1 + min(3, int(n / busy * 4))
    return cells, nz[-1] if nz else 0


def stats(cells):
    total = sum(c["count"] for c in cells)
    busiest = max(cells, key=lambda c: c["count"])
    longest, run, run_start = (0, None, None), 0, None
    for c in cells:
        if c["count"] > 0:
            run_start = c["date"] if run == 0 else run_start
            run += 1
            if run > longest[0]:
                longest = (run, run_start, c["date"])
        else:
            run = 0
    j = len(cells) - 1
    if cells[j]["count"] == 0:
        j -= 1
    end_at = j
    while j >= 0 and cells[j]["count"] > 0:
        j -= 1
    current = (end_at - j, cells[j + 1]["date"], cells[end_at]["date"]) if end_at - j > 0 else (0, None, None)
    return total, busiest, longest, current, cells[0]["date"], cells[-1]["date"]


def fmt(d, year=False):
    return d.strftime("%b ") + str(d.day) + (d.strftime(", %Y") if year else "")


def span(a, b, year=False):
    return f"{fmt(a, year)} – {fmt(b, year)}" if a else "–"


def shade(hexc, k):
    r, g, b = (int(hexc[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (round(r * k), round(g * k), round(b * k))


def render(cells, max_count, theme):
    t = THEMES[theme]
    weeks = cells[-1]["week"] + 1
    bar = lambda n: 0.4 + (n / max_count) ** 0.85 * 7.2 if n > 0 and max_count else 0.2
    proj = lambda x, y, z: (x * CS - y * SN, (x * SN + y * CS) * SE - z * CE)

    w, off = 0.9, 0.05
    pts = []
    for c in cells:
        x0, y0, z = c["week"] + off, c["day"] + off, bar(c["count"])
        pts += [proj(x0, y0, z), proj(x0 + w, y0, z), proj(x0, y0 + w, z), proj(x0 + w, y0 + w, 0)]
    pts += [proj(0, 8.5, 0), proj(weeks, 8.5, 0)]
    minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
    miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
    pad_t, pad, avail_h = 56, 24, H - 56 - 20
    s = min((W - 2 * pad) / (maxx - minx), avail_h / (maxy - miny))
    ox = pad + ((W - 2 * pad) - (maxx - minx) * s) / 2 - minx * s
    oy = pad_t + (avail_h - (maxy - miny) * s) / 2 - miny * s
    P = lambda x, y, z: "%.1f,%.1f" % (ox + (x * CS - y * SN) * s, oy + ((x * SN + y * CS) * SE - z * CE) * s)

    fills = [t["empty"]] + t["levels"]
    out = []
    for c in sorted(cells, key=lambda c: (c["week"] + 0.5) * SN + (c["day"] + 0.5) * CS):
        x0, y0 = c["week"] + off, c["day"] + off
        x1, y1, z = x0 + w, y0 + w, bar(c["count"])
        col = fills[c["level"]]
        top = f'<polygon points="{P(x0, y0, z)} {P(x1, y0, z)} {P(x1, y1, z)} {P(x0, y1, z)}" fill="{col}"/>'
        left = f'<polygon points="{P(x0, y1, 0)} {P(x1, y1, 0)} {P(x1, y1, z)} {P(x0, y1, z)}" fill="{shade(col, 0.84)}"/>'
        right = f'<polygon points="{P(x1, y0, 0)} {P(x1, y1, 0)} {P(x1, y1, z)} {P(x1, y0, z)}" fill="{shade(col, 0.68)}"/>'
        if c["count"] > 0:
            delay = 0.25 + c["week"] / max(1, weeks - 1) * 1.3 + c["day"] / 6 * 0.2
            fz, fc = 0.2, fills[0]
            out.append(f'<polygon points="{P(x0, y1, 0)} {P(x1, y1, 0)} {P(x1, y1, fz)} {P(x0, y1, fz)}" fill="{shade(fc, 0.84)}"/>'
                       f'<polygon points="{P(x1, y0, 0)} {P(x1, y1, 0)} {P(x1, y1, fz)} {P(x1, y0, fz)}" fill="{shade(fc, 0.68)}"/>'
                       f'<polygon points="{P(x0, y0, fz)} {P(x1, y0, fz)} {P(x1, y1, fz)} {P(x0, y1, fz)}" fill="{fc}"/>')
            out.append(f'<g class="b" style="animation-delay:{delay:.2f}s"><title>{c["count"]} on {fmt(c["date"], True)}</title>{left}{right}{top}</g>')
        else:
            out.append(left + right + top)

    months, prev, edge = [], None, -1e9
    for wk in range(weeks):
        d = cells[wk * 7]["date"]
        if d.month != prev:
            months.append((wk, d.strftime("%b")))
        prev = d.month
    if len(months) > 1 and months[1][0] - months[0][0] < 3:
        months.pop(0)
    labels = []
    for wk, label in months:
        x, y = (float(v) for v in P(wk + 0.5, 7.4, 0).split(","))
        if x < edge or x + 26 > W:
            continue
        labels.append(f'<text x="{x:.1f}" y="{y + 10:.1f}" class="m">{label}</text>')
        edge = x + 34

    total, busiest, longest, current, first, last = stats(cells)
    plural = lambda n, one, many: one if n == 1 else many

    def stat(x, y, label, value, unit, sub, anchor):
        return (f'<text x="{x}" y="{y}" class="l" text-anchor="{anchor}">{label}</text>'
                f'<text x="{x}" y="{y + 38}" text-anchor="{anchor}"><tspan class="v">{value}</tspan><tspan class="u" dx="6">{unit}</tspan></text>'
                f'<text x="{x}" y="{y + 58}" class="l" text-anchor="{anchor}">{sub}</text>')

    corners = (stat(W - 24, 74, "1 year total", f"{total:,}", plural(total, "contribution", "contributions"), span(first, last, True), "end")
               + stat(W - 24, 168, "Busiest day", f"{busiest['count']:,}", plural(busiest["count"], "contribution", "contributions"), fmt(busiest["date"]), "end")
               + stat(24, H - 164, "Longest streak", longest[0], plural(longest[0], "day", "days"), span(longest[1], longest[2]), "start")
               + stat(24, H - 70, "Current streak", current[0], plural(current[0], "day", "days"), span(current[1], current[2]), "start"))

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-label="{total:,} GitHub contributions in the last year, as a 3D skyline">
<style>
text {{ font-family: {FONT}; fill: {t["fg"]}; }}
.h {{ font-size: 15px; }} .h tspan {{ font-weight: 600; }}
.m {{ font-size: 10px; fill: {t["muted"]}; }}
.l {{ font-size: 12px; fill: {t["muted"]}; }}
.v {{ font-size: 34px; font-weight: 600; fill: {t["accent"]}; letter-spacing: -0.02em; }}
.u {{ font-size: 14px; }}
.b {{ transform-box: fill-box; transform-origin: 50% 100%; animation: rise 0.9s cubic-bezier(0.33, 1, 0.68, 1) both; }}
.s {{ animation: fade 0.6s ease-out 1.6s both; }}
@keyframes rise {{ from {{ transform: scaleY(0.02); opacity: 0; }} 25% {{ opacity: 1; }} to {{ transform: scaleY(1); opacity: 1; }} }}
@keyframes fade {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: none; }} }}
@media (prefers-reduced-motion: reduce) {{ .b, .s {{ animation: none; }} }}
</style>
<rect x="0.5" y="0.5" width="{W - 1}" height="{H - 1}" rx="10" fill="none" stroke="{t["border"]}"/>
<text x="24" y="34" class="h"><tspan>{total:,}</tspan> contributions in the last year</text>
{"".join(out)}
{"".join(labels)}
<g class="s">{corners}</g>
</svg>
'''


if __name__ == "__main__":
    cells, max_count = build(fetch())
    for theme in THEMES:
        (OUT / f"skyline-{theme}.svg").write_text(render(cells, max_count, theme))
