"""Auswertung: eine Karte (`analyse`, `verdict`), viele Karten (`distribution`, `effort_table`) und das Aufwand-Experiment (`scaling`).

Alle Größen kommen aus ganzen Zahlen und einem deterministischen Verfahren; nur die Anzeige-Statistiken (Anteile, Mediane) sind Gleitkomma.
Aufwand wird in durchsuchten Kanten gezählt, nie in Sekunden.
"""

import math
from dataclasses import dataclass
from functools import lru_cache

import numpy as np

import ap_constants as C
from ap_algorithm import SEARCHES, STARTS, augment, start_pairs
from ap_greedy import RULES, optimum, run_rule
from ap_scenario import build, generate

OPTIMAL, COSTLIER, NONE = "optimal", "costlier", "none"


@dataclass
class Analysis:
    scenario: object
    start: str
    search: str
    result: object      # ap_algorithm.Result
    opt: object         # exakte Messlatte (Paare zuerst, dann Kosten)
    greedy: dict        # {"edge": Matching, "order": Matching} - die Greedy-Ergebnisse der Wurzel auf derselben Karte


def analyse(sc, start=C.DEFAULT_START, search=C.DEFAULT_SEARCH):
    return Analysis(sc, start, search, augment(sc, start_pairs(sc, start), search), optimum(sc), {r: run_rule(sc, r) for r in RULES})


def cost_gap_pct(cost, opt_cost):
    """Mehrkosten in Prozent des Optimums bei gleicher Paarzahl; nur definiert, wenn das Optimum positive Kosten hat."""
    return None if opt_cost <= 0 else 100.0 * (cost - opt_cost) / opt_cost


def classify(res, opt):
    if opt.count == 0:
        return NONE
    return OPTIMAL if res.cost == opt.cost else COSTLIER


def verdict(a):
    """(Stufe, Code, Zahlen) für die Anzeige; `Zahlen` enthält jede Zahl, die der Text nennt. Die Paarzahl ist nach den Verbesserungswegen immer größtmöglich."""
    r, o = a.result, a.opt
    code = classify(r, o)
    lens = [x.length for x in r.rounds]
    data = {"start_count": len(r.start), "count": r.count, "opt_count": o.count, "cost": r.cost, "opt_cost": o.cost, "rounds": len(r.rounds),
            "cost_gap_pct": cost_gap_pct(r.cost, o.cost), "cost_gap_abs": r.cost - o.cost, "path_mean": float(np.mean(lens)) if lens else None,
            "path_max": max(lens) if lens else None, "scanned": r.scanned_total, "cover_size": len(r.cover_v) + len(r.cover_o),
            "pairs_max": r.count == o.count, "start_cost": int(sum(a.scenario.cost[i, j] for i, j in r.start))}
    level = {NONE: "info", OPTIMAL: "success", COSTLIER: "warning"}[code]
    return level, code, data


def compare_table(sc):
    """Alle sechs Kombinationen (Start x Suche) auf einer Karte."""
    opt = optimum(sc)
    rows = []
    for start in STARTS:
        for search in SEARCHES:
            r = augment(sc, start_pairs(sc, start), search, record=False)
            lens = [x.length for x in r.rounds]
            rows.append({"start": start, "search": search, "start_count": len(r.start), "count": r.count, "cost": r.cost, "rounds": len(r.rounds),
                         "path_mean": float(np.mean(lens)) if lens else None, "path_max": max(lens) if lens else None, "scanned": r.scanned_total,
                         "cost_gap_pct": cost_gap_pct(r.cost, opt.cost)})
    return rows


# --- viele Karten --------------------------------------------------------------------------------------------------------------

@lru_cache(maxsize=256)
def cell_rows(n, m, reach, ballung, seeds):
    """Je Seed und Kombination (Start, Suche): (Paare, Kosten, Runden, Summe der Weglängen, längster Weg, durchsuchte Kanten), dazu Optimum und Startpaare.
    Ganzzahlen, plattformunabhängig. Rückgabe: Tupel von Dicts."""
    rows = []
    for s in seeds:
        sc = generate(n, m, reach, ballung, s)
        o = optimum(sc)
        row = {"opt_count": o.count, "opt_cost": o.cost, "edges": int(sc.feasible.sum())}
        for start in STARTS:
            sp = start_pairs(sc, start)
            row[("start", start)] = (len(sp), int(sum(sc.cost[i, j] for i, j in sp)))
            for search in SEARCHES:
                r = augment(sc, sp, search, record=False)
                lens = [x.length for x in r.rounds]
                row[(start, search)] = (r.count, r.cost, len(r.rounds), sum(lens), max(lens) if lens else 0, r.scanned_total)
        rows.append(row)
    return tuple(rows)


def distribution(n, m, reach, ballung, start, search, seeds=C.DIST_SEEDS):
    """Verteilung über viele Karten für eine Kombination (Start, Suche)."""
    rows = cell_rows(n, m, reach, ballung, tuple(seeds))
    valid = [r for r in rows if r["opt_count"] > 0]
    n_valid = len(valid)
    cells = [r[(start, search)] for r in valid]
    counts = np.array([c[0] for c in cells]) if n_valid else np.array([])
    opt_counts = np.array([r["opt_count"] for r in valid]) if n_valid else np.array([])
    gaps = np.array([100.0 * (c[1] - r["opt_cost"]) / r["opt_cost"] for c, r in zip(cells, valid) if r["opt_cost"] > 0])
    rounds = np.array([c[2] for c in cells]) if n_valid else np.array([])
    total_len = sum(c[3] for c in cells)
    total_rounds = int(rounds.sum()) if n_valid else 0
    start_counts = np.array([r[("start", start)][0] for r in valid]) if n_valid else np.array([])
    share = lambda mask: float(np.mean(mask)) if n_valid else 0.0
    return {
        "n_seeds": len(rows), "n_valid": n_valid,
        "share_max_pairs": share(counts == opt_counts), "share_start_max": share(start_counts == opt_counts),
        "share_optimal_cost": float(np.mean(gaps == 0)) if len(gaps) else 0.0,
        "cost_gaps": gaps.tolist(), "cost_gap_median": float(np.median(gaps)) if len(gaps) else None,
        "cost_gap_mean": float(gaps.mean()) if len(gaps) else None, "cost_gap_p90": float(np.quantile(gaps, 0.9)) if len(gaps) else None,
        "rounds_mean": float(rounds.mean()) if n_valid else None, "rounds_max": int(rounds.max()) if n_valid else None, "rounds_list": rounds.tolist(),
        "path_mean": total_len / total_rounds if total_rounds else None, "path_max": max((c[4] for c in cells), default=0),
        "scanned_mean": float(np.mean([c[5] for c in cells])) if n_valid else None, "edges_mean": float(np.mean([r["edges"] for r in valid])) if n_valid else None,
        "start_pairs_mean": float(start_counts.mean()) if n_valid else None, "opt_pairs_mean": float(opt_counts.mean()) if n_valid else None,
    }


def effort_table(n, m, reach, ballung, seeds=C.DIST_SEEDS):
    """Zeilen für die sechs Kombinationen: Runden, Weglängen, durchsuchte Kanten, Kostenlücke (Median) - über die festen Karten."""
    rows = []
    for start in STARTS:
        for search in SEARCHES:
            d = distribution(n, m, reach, ballung, start, search, seeds)
            rows.append({"start": start, "search": search, "rounds_mean": d["rounds_mean"], "path_mean": d["path_mean"], "path_max": d["path_max"],
                         "scanned_mean": d["scanned_mean"], "cost_gap_median": d["cost_gap_median"], "share_max_pairs": d["share_max_pairs"]})
    return rows


def reach_sweep(n, m, ballung, start, search, values=C.REACH_SWEEP, seeds=C.SWEEP_SEEDS):
    """Je Reichweite: mittlere Runden und mediane Kostenlücke."""
    out = []
    for reach in values:
        d = distribution(n, m, reach, ballung, start, search, seeds)
        out.append({"x": reach, "rounds_mean": d["rounds_mean"], "cost_gap_median": d["cost_gap_median"], "start_pairs_mean": d["start_pairs_mean"], "opt_pairs_mean": d["opt_pairs_mean"]})
    return out


def scaling(ns=C.SCALE_NS, seeds=C.SCALE_SEEDS):
    """Aufwand wächst mit der Karte: n = m bei konstantem mittlerem Grad (Reichweite ~ 1/sqrt(n)); durchsuchte Kanten je Kombination."""
    out = []
    for n in ns:
        reach = max(5, round(C.SCALE_REACH_AT_20 * math.sqrt(20 / n)))
        acc = {}
        edges = []
        for s in seeds:
            sc = generate(n, n, reach, 0, s)
            edges.append(int(sc.feasible.sum()))
            for start in STARTS:
                for search in SEARCHES:
                    r = augment(sc, start_pairs(sc, start), search, record=False)
                    acc.setdefault((start, search), []).append((len(r.rounds), r.scanned_total))
        row = {"n": n, "reach": reach, "edges": float(np.mean(edges))}
        for key, vals in acc.items():
            row[key] = {"rounds": float(np.mean([v[0] for v in vals])), "scanned": float(np.mean([v[1] for v in vals]))}
        out.append(row)
    return out


def scenario_from_settings(net, n, m, reach, ballung, seed):
    return build(net, n, m, reach, ballung, seed)
