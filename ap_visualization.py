"""Plotly-Abbildungen: Karte mit Matching und Verbesserungsweg, Beweis (Knotenüberdeckung), Runden, Verteilungen, Reichweite-Sweep und Aufwand.
Achsen sind gesperrt (fixedrange), damit Touch-Geräte beim Scrollen nicht zoomen. Punkte auf einer Geraden werden mit Bögen gezeichnet."""

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import ap_constants as C


def lock_axes(fig):
    fig.update_xaxes(fixedrange=True)
    fig.update_yaxes(fixedrange=True)
    return fig


def _base(fig, height):
    fig.update_layout(height=height, margin=dict(l=10, r=10, t=10, b=10), legend=dict(orientation="h", y=-0.08), plot_bgcolor="rgba(0,0,0,0)")
    return lock_axes(fig)


def _collinear(sc):
    """Liegen alle Punkte auf einer Geraden? Dann würden sich die Paar-Linien überdecken - sie werden gebogen gezeichnet."""
    pts = list(sc.vehicles + sc.orders)
    (x0, y0), (x1, y1) = pts[0], next((p for p in pts if p != pts[0]), pts[0])
    return all((x1 - x0) * (y - y0) - (y1 - y0) * (x - x0) == 0 for x, y in pts)


def _edge_path(sc, i, j, curved, steps=14):
    """Punkte einer Paar-Linie: gerade, oder (bei Punkten auf einer Geraden) als Bogen, dessen Seite je Paar wechselt."""
    (vx, vy), (ox, oy) = sc.vehicles[i], sc.orders[j]
    if not curved:
        return [vx, ox], [vy, oy]
    dx, dy = ox - vx, oy - vy
    side = 1 if (i + j) % 2 == 0 else -1
    cx, cy = (vx + ox) / 2 - side * 0.35 * dy, (vy + oy) / 2 + side * 0.35 * dx      # Kontrollpunkt senkrecht zur Verbindung
    ts = [k / steps for k in range(steps + 1)]
    return ([(1 - t) ** 2 * vx + 2 * (1 - t) * t * cx + t * t * ox for t in ts], [(1 - t) ** 2 * vy + 2 * (1 - t) * t * cy + t * t * oy for t in ts])


def _segments(sc, pairs, curved=False):
    """Linienspur für eine Menge von Paaren (None trennt die Segmente)."""
    x, y = [], []
    for i, j in pairs:
        px, py = _edge_path(sc, i, j, curved)
        x += px + [None]
        y += py + [None]
    return x, y


def _feasible_pairs(sc):
    return [(i, j) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j]]


def _map_layout(fig, sc, height):
    xs = [p[0] for p in sc.vehicles + sc.orders]
    ys = [p[1] for p in sc.vehicles + sc.orders]
    pad = 8
    if _collinear(sc):
        # Punkte auf einer Geraden: nur die Bögen brauchen Höhe. Das Seitenverhältnis wird freigegeben, sonst wird eine lange Kette zu einem dünnen Streifen.
        span = max(max(xs) - min(xs), max(ys) - min(ys), 1)
        cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
        if max(xs) - min(xs) >= max(ys) - min(ys):
            fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad])
            fig.update_yaxes(visible=False, range=[cy - span * 0.22, cy + span * 0.22])
        else:
            fig.update_xaxes(visible=False, range=[cx - span * 0.22, cx + span * 0.22])
            fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
        return _base(fig, min(height, 320))
    fig.update_xaxes(visible=False, range=[min(xs) - pad, max(xs) + pad], scaleanchor="y", scaleratio=1)
    fig.update_yaxes(visible=False, range=[min(ys) - pad, max(ys) + pad])
    return _base(fig, height)


def _vertices(fig, sc, matched_v, matched_o, cover_v=(), cover_o=()):
    """Fahrzeuge (Quadrate) und Aufträge (Kreise); ohne Partner nur als Umriss; Ecken der Überdeckung in Violett."""
    small = sc.n + sc.m <= 16
    cover_v, cover_o = set(cover_v), set(cover_o)
    for kind, pts, matched, cover, symbol, color, prefix, tpos in (("Fahrzeug", sc.vehicles, matched_v, cover_v, "square", C.COLORS["vehicle"], "F", "top center"),
                                                                    ("Auftrag", sc.orders, matched_o, cover_o, "circle", C.COLORS["order"], "A", "bottom center")):
        for on, sym, name in ((True, symbol, f"{kind} mit Partner"), (False, symbol + "-open", f"{kind} ohne Partner")):
            idx = [k for k in range(len(pts)) if (k in matched) == on and k not in cover]
            if idx:
                fig.add_trace(go.Scatter(
                    x=[pts[k][0] for k in idx], y=[pts[k][1] for k in idx], mode="markers+text" if small else "markers", name=name,
                    text=[f"{prefix}{k + 1}" for k in idx] if small else None, textposition=tpos,
                    hovertext=[f"{kind} {k + 1} ({pts[k][0]}, {pts[k][1]})" for k in idx], hoverinfo="text",
                    marker=dict(symbol=sym, size=10 if on else 11, color=color, line=dict(width=2, color=color))))
        idx = sorted(cover)
        if idx:
            fig.add_trace(go.Scatter(
                x=[pts[k][0] for k in idx], y=[pts[k][1] for k in idx], mode="markers+text" if small else "markers", name=f"{kind} in der Überdeckung",
                text=[f"{prefix}{k + 1}" for k in idx] if small else None, textposition=tpos,
                hovertext=[f"{kind} {k + 1} ({pts[k][0]}, {pts[k][1]}) - Ecke der Überdeckung" for k in idx], hoverinfo="text",
                marker=dict(symbol=symbol, size=12, color=C.COLORS["cover"], line=dict(width=2, color="#4b2d73"))))


def build_state_map(sc, pairs, path=None, show_costs=True, height=430):
    """Karte mit allen möglichen Kanten (blass) und dem Matching (blau). Mit `path`: die Kanten, die der Verbesserungsweg neu wählt (grün) und
    die er freigibt (rot gestrichelt, das sind gewählte Kanten)."""
    curved = _collinear(sc)
    fig = go.Figure()
    ex, ey = _segments(sc, _feasible_pairs(sc), curved)
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.35)", width=1), hoverinfo="skip", name="mögliche Paare"))
    dropped = {(i, j) for i, j, kind in path if kind == "drop"} if path else set()
    added = [(i, j) for i, j, kind in path if kind == "add"] if path else []
    kept = [p for p in pairs if p not in dropped]
    kx, ky = _segments(sc, kept, curved)
    fig.add_trace(go.Scatter(x=kx, y=ky, mode="lines", line=dict(color=C.COLORS["matched"], width=3.5), hoverinfo="skip", name="gewählt"))
    if path:
        dx, dy = _segments(sc, sorted(dropped), curved)
        fig.add_trace(go.Scatter(x=dx, y=dy, mode="lines", line=dict(color=C.COLORS["drop"], width=4.5, dash="dash"), hoverinfo="skip", name="wird freigegeben"))
        ax, ay = _segments(sc, added, curved)
        fig.add_trace(go.Scatter(x=ax, y=ay, mode="lines", line=dict(color=C.COLORS["add"], width=4.5), hoverinfo="skip", name="wird gewählt"))
    if show_costs and sc.n + sc.m <= 16 and not (curved and sc.n + sc.m > 8):     # bei einer langen Kette überdecken sich die Beschriftungen
        labelled = list(kept) + sorted(dropped) + added
        pts = []
        for i, j in labelled:
            px, py = _edge_path(sc, i, j, curved)
            k = len(px) // 2
            pts.append(((px[k] + px[k - 1]) / 2 if len(px) % 2 == 0 else px[k], (py[k] + py[k - 1]) / 2 if len(py) % 2 == 0 else py[k], int(sc.cost[i, j])))
        if pts:
            fig.add_trace(go.Scatter(x=[p[0] for p in pts], y=[p[1] for p in pts], mode="text", text=[f"{p[2]} min" for p in pts], textposition="bottom center", hoverinfo="skip", showlegend=False))
    matched_v = {i for i, _ in pairs} | {i for i, j in added}
    matched_o = {j for _, j in pairs} | {j for i, j in added}
    _vertices(fig, sc, matched_v, matched_o)
    return _map_layout(fig, sc, height)


def build_cover_map(sc, pairs, cover_v, cover_o, height=430):
    """Beweis der Erschöpfung: die violetten Ecken (Knotenüberdeckung) berühren jede mögliche Kante, und es sind genau so viele wie Paare."""
    curved = _collinear(sc)
    fig = go.Figure()
    ex, ey = _segments(sc, _feasible_pairs(sc), curved)
    fig.add_trace(go.Scatter(x=ex, y=ey, mode="lines", line=dict(color="rgba(150,150,150,0.4)", width=1), hoverinfo="skip", name="mögliche Paare"))
    px, py = _segments(sc, pairs, curved)
    fig.add_trace(go.Scatter(x=px, y=py, mode="lines", line=dict(color=C.COLORS["matched"], width=3.5), hoverinfo="skip", name="gewählt"))
    _vertices(fig, sc, {i for i, _ in pairs}, {j for _, j in pairs}, cover_v, cover_o)
    return _map_layout(fig, sc, height)


def build_rounds(states_counts, lengths, height=260):
    """Paarzahl vor und nach jeder Runde (Linie) und die Länge des Wegs je Runde (Balken)."""
    fig = make_subplots(specs=[[{"secondary_y": True}]])
    rounds = list(range(1, len(lengths) + 1))
    fig.add_trace(go.Bar(x=rounds, y=lengths, name="Weglänge [Kanten]", marker_color=C.COLORS["add"], opacity=0.55), secondary_y=True)
    fig.add_trace(go.Scatter(x=list(range(0, len(states_counts))), y=states_counts, mode="lines+markers", name="Paare", line=dict(color=C.COLORS["matched"])), secondary_y=False)
    fig.update_xaxes(title="Runde (0 = Start)", dtick=1 if len(states_counts) <= 25 else None)
    fig.update_yaxes(title="Paare", secondary_y=False, rangemode="tozero", dtick=1 if max(states_counts) <= 12 else None)
    fig.update_yaxes(title="Weglänge", secondary_y=True, rangemode="tozero", showgrid=False, dtick=2 if max(lengths, default=1) <= 21 else None)
    return _base(fig, height)


def build_gap_compare(gaps_by_label, current=None, height=320):
    """Mehrkosten gegenüber dem Optimum (bei gleicher, nämlich größtmöglicher Paarzahl) je Start, übereinandergelegt."""
    colors = ["#1f77b4", "#ff7f0e", "#2ca02c", "#9467bd"]
    fig = go.Figure()
    for k, (label, gaps) in enumerate(gaps_by_label.items()):
        fig.add_trace(go.Histogram(x=gaps, xbins=dict(size=5), name=label, marker_color=colors[k % 4], opacity=0.6))
    fig.update_layout(barmode="overlay")
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="Mehrkosten gegenüber dem Optimum [%]")
    fig.update_yaxes(title="Karten")
    fig = _base(fig, height)
    fig.update_layout(legend=dict(orientation="h", y=-0.4), margin=dict(l=10, r=10, t=10, b=10), height=height + 60)
    return fig


def build_rounds_hist(rounds_list, current=None, height=300):
    """Wie viele Verbesserungswege werden gebraucht - Anteil der Karten je Rundenzahl."""
    values, counts = np.unique(np.array(rounds_list, dtype=int), return_counts=True)
    fig = go.Figure(go.Bar(x=values, y=100.0 * counts / len(rounds_list), marker_color=C.COLORS["add"], showlegend=False,
                           hovertemplate="%{x} Verbesserungsweg(e): %{y:.0f} % der Karten<extra></extra>"))
    if current is not None:
        fig.add_vline(x=current, line=dict(color=C.COLORS["optimal"], dash="dash"), annotation_text="Ihre Ziehung", annotation_position="top")
    fig.update_xaxes(title="Verbesserungswege bis zum Ende", dtick=1 if max(values) <= 25 else None)
    fig.update_yaxes(title="Anteil der Karten [%]")
    return _base(fig, height)


def build_reach_sweep(rows, current=None, height=420):
    """Oben: mittlere Zahl der Verbesserungswege; unten: mediane Mehrkosten - je über der Reichweite."""
    x = [r["x"] for r in rows]
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.1, subplot_titles=("Verbesserungswege (Mittel)", "Mehrkosten gegenüber dem Optimum (Median)"))
    fig.add_trace(go.Scatter(x=x, y=[r["rounds_mean"] for r in rows], mode="lines+markers", name="Verbesserungswege", line=dict(color=C.COLORS["add"])), row=1, col=1)
    fig.add_trace(go.Scatter(x=x, y=[r["cost_gap_median"] for r in rows], mode="lines+markers", name="Mehrkosten [%]", line=dict(color=C.COLORS["drop"])), row=2, col=1)
    if current is not None and min(x) <= current <= max(x):
        fig.add_vline(x=current, line=dict(color="#555", dash="dot"))
    fig.update_xaxes(title="Reichweite [min]", row=2, col=1)
    fig.update_yaxes(title="Wege", row=1, col=1)
    fig.update_yaxes(title="%", row=2, col=1)
    fig = _base(fig, height)
    fig.update_layout(showlegend=False, margin=dict(l=10, r=10, t=30, b=10))
    return fig


def build_scaling(rows, height=340):
    """Durchsuchte Kanten gegen die Kartengröße (doppelt logarithmisch), je Kombination aus Start und Suche."""
    fig = go.Figure()
    styles = {("empty", "bfs"): ("Leer, Breitensuche", "#1f77b4", "solid"), ("empty", "dfs"): ("Leer, Tiefensuche", "#1f77b4", "dot"),
              ("edge", "bfs"): ("Greedy A, Breitensuche", "#2ca02c", "solid"), ("edge", "dfs"): ("Greedy A, Tiefensuche", "#2ca02c", "dot")}
    for key, (label, color, dash) in styles.items():
        fig.add_trace(go.Scatter(x=[r["n"] for r in rows], y=[r[key]["scanned"] for r in rows], mode="lines+markers", name=label, line=dict(color=color, dash=dash)))
    fig.add_trace(go.Scatter(x=[r["n"] for r in rows], y=[r["edges"] for r in rows], mode="lines+markers", name="Kanten des Graphen", line=dict(color="#555", dash="dashdot")))
    fig.update_xaxes(title="Fahrzeuge = Aufträge", type="log")
    fig.update_yaxes(title="durchsuchte Kanten", type="log")
    return _base(fig, height)
