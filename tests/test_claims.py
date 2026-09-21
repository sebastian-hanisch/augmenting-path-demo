"""Jede Zahl in den Hilfetexten, Presets, Tabellen und Grenzen der App ist hier über die 100 festen Karten (DIST_SEEDS) belegt.
Alles rechnet mit ganzen Zahlen und einem eigenen Zufallsgenerator - die Werte sind auf jeder Plattform dieselben; die Toleranzen decken nur die Rundung auf die im Text genannten Stellen.
Positive UND negative Aussagen: wo Verbesserungswege reichen (Paarzahl, knappe Reichweite), steht hier ebenso ein Test wie dort, wo sie nicht reichen (Kosten)."""

import numpy as np
import pytest

import ap_constants as C
import ap_evaluation as ev
from ap_algorithm import SEARCHES, STARTS, augment, start_pairs
from ap_greedy import optimum, run_rule
from ap_scenario import long_chain, p4_chain, steal_2x2


def near(value, expected, tol):
    assert abs(value - expected) <= tol, f"{value:.3f} statt {expected}"


def dist(start="edge", search="bfs", n=20, m=20, reach=40, ballung=0):
    return ev.distribution(n, m, reach, ballung, start, search)


# --- feste Karten (Preset-Hilfe) ---------------------------------------------------------------------------------------------------------

def test_steal_2x2_numbers():
    sc = steal_2x2()
    res = augment(sc, start_pairs(sc, "edge"), "bfs")
    assert res.rounds == () and res.cost == 18 and optimum(sc).cost == 10 and res.count == 2      # "keinen Verbesserungsweg ... 18 statt 10 Minuten"


def test_p4_numbers():
    sc = p4_chain(1)
    res = augment(sc, start_pairs(sc, "edge"), "bfs")
    assert (len(res.start), res.count, [r.length for r in res.rounds]) == (1, 2, [3])            # "Greedy hat 1 Paar. Ein Verbesserungsweg aus 3 Kanten ... 2 Paare"


def test_long_chain_numbers():
    sc = long_chain(6)
    res = augment(sc, start_pairs(sc, "edge"), "bfs")
    assert (len(res.start), res.count, len(res.rounds), res.rounds[0].length) == (6, 7, 1, 13)  # "6 Paare ... 13 Kanten"
    assert sum(1 for _i, _j, kind in res.rounds[0].path if kind == "drop") == 6                  # "gibt alle 6 gewählten Paare frei"
    assert sc.n == 7 and sc.m == 7                                                                # "sieben Fahrzeuge und sieben Aufträge"


# --- Verteilungen über 100 Karten -----------------------------------------------------------------------------------------------------------

def test_every_start_and_search_reaches_the_maximum_pair_count_on_every_map():
    """Die zentrale positive Aussage: alle sechs Kombinationen, auf allen 100 Karten, bei jeder Reichweite der Sweep-Reihe."""
    for reach in C.REACH_SWEEP:
        for start in STARTS:
            for search in SEARCHES:
                assert dist(start, search, reach=reach)["share_max_pairs"] == 1.0, (reach, start, search)


def test_mid_reach_numbers_from_greedy():
    d = dist()
    near(d["rounds_mean"], 2.7, 0.05)                                        # "genügen 2,7 Verbesserungswege"
    near(d["start_pairs_mean"], 16.7, 0.05)                                  # "Greedy hat 16,7 von 19,5 Paaren"
    near(d["opt_pairs_mean"], 19.5, 0.05)
    near(d["cost_gap_median"], 8.0, 0.5)                                     # "im Median 8 % über dem Optimum"
    assert d["share_start_max"] == pytest.approx(0.01)                       # Einleitung: Greedy verliert auf 99 von 100 Karten Paare (Preset der Wurzel)
    assert d["share_optimal_cost"] == pytest.approx(0.01)                    # "Das ist die Ausnahme"


def test_from_empty_numbers():
    d = dist("empty")
    near(d["rounds_mean"], 19.5, 0.05)                                       # "19,5 Verbesserungswege statt 2,7"
    near(d["cost_gap_median"], 36.0, 0.5)                                    # "36 % statt 8 %"


def test_depth_first_numbers():
    bfs, dfs = dist("edge", "bfs"), dist("edge", "dfs")
    near(bfs["path_mean"], 4.3, 0.05)                                        # "4,3 Kanten"
    near(dfs["path_mean"], 15.6, 0.05)                                       # "15,6 statt 4,3 Kanten"
    near(dfs["cost_gap_median"], 27.0, 0.5)                                  # "27 % statt 8 %"
    assert dfs["rounds_mean"] == bfs["rounds_mean"]                          # dieselbe Zahl Wege: jeder gibt ein Paar dazu
    assert dfs["path_max"] > bfs["path_max"]


def test_all_reachable_numbers():
    edge, empty = dist(reach=150), dist("empty", reach=150)
    assert edge["rounds_mean"] == 0.0 and edge["share_start_max"] == 1.0     # "es gibt keinen Verbesserungsweg", "bei 150 keins"
    near(edge["cost_gap_median"], 14.0, 0.5)                                 # "im Median 14 % über dem Optimum"
    assert empty["cost_gap_median"] > 150.0                                  # "vom leeren Start aus ... über 150 %"


def test_short_reach_greedy_is_enough():
    d = dist(reach=10)
    assert d["share_start_max"] == pytest.approx(0.80)                       # "auf 80 von 100 Karten ... schon die größtmögliche Paarzahl"
    near(d["rounds_mean"], 0.2, 0.005)                                       # "im Mittel 0,2 Verbesserungswege"
    assert d["share_optimal_cost"] == pytest.approx(0.95)                    # "auf 95 von 100 Karten ... auch die Kosten optimal"


def test_starting_from_greedy_keeps_the_costs_lower_than_starting_empty():
    """Text: 'wer von Greedy startet, behält dessen billige Kanten und klappt nur wenige um' - bei mittlerer Reichweite und in der ganzen Sweep-Reihe ab Reichweite 20."""
    for reach in (20, 30, 40, 60, 80, 100, 150):
        assert dist("edge", reach=reach)["cost_gap_median"] < dist("empty", reach=reach)["cost_gap_median"], reach


def test_search_effort_in_scanned_edges():
    """Aufwand in durchsuchten Kanten: vom Greedy-Start durchsucht die Tiefensuche etwas weniger, vom leeren Start mehr als das Doppelte der Breitensuche (Reichweite 40)."""
    assert dist("edge", "dfs")["scanned_mean"] < dist("edge", "bfs")["scanned_mean"]
    assert dist("empty", "dfs")["scanned_mean"] > 2 * dist("empty", "bfs")["scanned_mean"]
    assert dist("edge", "bfs")["scanned_mean"] < 1.1 * dist("edge", "bfs")["edges_mean"]        # ein Greedy-Start kostet im Mittel etwa eine Suche über alle Kanten


def test_rounds_are_largest_at_medium_reach():
    """Sweep-Text: bei knapper Reichweite kaum etwas zu verbessern, bei mittlerer die meisten Wege, bei allem erreichbar keiner."""
    rows = ev.reach_sweep(20, 20, 0, "edge", "bfs")
    rounds = {r["x"]: r["rounds_mean"] for r in rows}
    peak = max(rounds, key=rounds.get)
    assert 30 <= peak <= 60 and rounds[10] < 0.5 * rounds[peak] and rounds[150] == 0.0


# --- Aufwand-Experiment ----------------------------------------------------------------------------------------------------------------------

def test_scaling_grows_about_quadratically():
    """Text: 'auf mehr als das 100-Fache' von 20 auf 320 Fahrzeuge, 'etwa mit dem Quadrat der Kartengröße' (Steigung im doppelt logarithmischen Bild)."""
    rows = ev.scaling()
    ns = np.array([r["n"] for r in rows], dtype=float)
    scanned = np.array([r[("edge", "bfs")]["scanned"] for r in rows])
    assert scanned[-1] > 100 * scanned[list(ns).index(20)]
    slope = np.polyfit(np.log(ns), np.log(scanned), 1)[0]
    assert 1.7 <= slope <= 2.3
    edges = np.array([r["edges"] for r in rows])
    assert np.polyfit(np.log(ns), np.log(edges), 1)[0] < 1.3                                      # die Kantenzahl selbst wächst nur etwa linear (konstanter Grad)
    assert all(r[("edge", "bfs")]["rounds"] < r[("empty", "bfs")]["rounds"] for r in rows)


# --- die Wurzel (neu gemessen, nicht zitiert) -------------------------------------------------------------------------------------------------

def test_the_root_numbers_are_measured_again():
    """Die Schwäche der Wurzel wird hier neu gemessen: auf 99 von 100 Karten verliert Greedy bei Reichweite 40 Paare (16,7 statt 19,5), und die Zahl der Wege ist genau die Differenz."""
    d = dist()
    assert 1.0 - d["share_start_max"] == pytest.approx(0.99)
    near(d["opt_pairs_mean"] - d["start_pairs_mean"], d["rounds_mean"], 1e-9)
    for s in C.DIST_SEEDS[:20]:
        from ap_scenario import generate
        sc = generate(20, 20, 40, 0, s)
        g, o = run_rule(sc, "edge"), optimum(sc)
        assert len(augment(sc, g.pairs, "bfs", record=False).rounds) == o.count - g.count
