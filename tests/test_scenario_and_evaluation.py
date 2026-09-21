"""Karten und Auswertung: Einordnung, Verdict, Verteilung über viele Karten, Vergleichstabelle, Reichweite-Sweep, Aufwand-Experiment."""

import numpy as np
import pytest

import ap_constants as C
import ap_evaluation as ev
from ap_algorithm import SEARCHES, STARTS, augment, start_pairs
from ap_greedy import Matching, optimum
from ap_scenario import build, generate, long_chain, p4_chain, steal_2x2


# --- Karten (Ergänzung zur Wurzel: die lange Kette) ----------------------------------------------------------------------------------------

def test_build_fixed_nets_ignore_random_parameters():
    a, b = build("chain", 5, 5, 99, 100, 123), build("chain", 30, 30, 10, 0, 1)
    assert a.vehicles == b.vehicles and a.orders == b.orders and a.reach == 10 and a.n == 7
    assert build("steal", 1, 1, 1, 1, 1).n == 2 and build("p4", 1, 1, 1, 1, 1).n == 2 and build("paths", 1, 1, 1, 1, 1).n == 6


def test_random_build_matches_generate():
    a, b = build("random", 9, 8, 45, 25, 4), generate(9, 8, 45, 25, 4)
    assert np.array_equal(a.cost, b.cost) and a.vehicles == b.vehicles


@pytest.mark.parametrize("k", range(1, 8))
def test_long_chain_has_a_unique_path_of_2k_plus_1_edges(k):
    sc = long_chain(k)
    res = augment(sc, start_pairs(sc, "edge"), "bfs")
    assert [r.length for r in res.rounds] == [2 * k + 1] and res.count == k + 1


# --- Einordnung und Verdict ------------------------------------------------------------------------------------------------------------------

def test_classify_and_cost_gap():
    opt = Matching(((0, 0),), 10)
    assert ev.classify(type("R", (), {"cost": 10})(), opt) == ev.OPTIMAL
    assert ev.classify(type("R", (), {"cost": 12})(), opt) == ev.COSTLIER
    assert ev.classify(type("R", (), {"cost": 0})(), Matching((), 0)) == ev.NONE
    assert ev.cost_gap_pct(18, 10) == pytest.approx(80.0) and ev.cost_gap_pct(5, 0) is None


@pytest.mark.parametrize("net,level,code,start_count,rounds,path_max,cost,opt_cost", [
    ("steal", "warning", ev.COSTLIER, 2, 0, None, 18, 10),
    ("p4", "success", ev.OPTIMAL, 1, 1, 3, 20, 20),
    ("chain", "success", ev.OPTIMAL, 6, 1, 13, 70, 70),
])
def test_verdict_of_the_fixed_nets(net, level, code, start_count, rounds, path_max, cost, opt_cost):
    for search in SEARCHES:
        got_level, got_code, d = ev.verdict(ev.analyse(build(net, 20, 20, 40, 0, 2), "edge", search))
        assert (got_level, got_code) == (level, code)
        assert (d["start_count"], d["rounds"], d["path_max"], d["cost"], d["opt_cost"]) == (start_count, rounds, path_max, cost, opt_cost)
        assert d["pairs_max"] and d["count"] == d["opt_count"] and d["cover_size"] == d["count"]


def test_verdict_data_carries_the_numbers_the_texts_use():
    _, _, d = ev.verdict(ev.analyse(steal_2x2()))
    assert d["cost_gap_pct"] == pytest.approx(80.0) and d["cost_gap_abs"] == 8 and d["start_cost"] == 18 and d["path_mean"] is None and d["scanned"] == 0


def test_verdict_none_without_any_feasible_edge():
    sc = next(s for s in (generate(3, 3, 10, 0, k) for k in range(200)) if not s.feasible.any())
    level, code, d = ev.verdict(ev.analyse(sc))
    assert (level, code) == ("info", ev.NONE) and d["count"] == 0 and d["cover_size"] == 0


def test_analysis_keeps_the_greedy_results_of_the_root():
    sc = generate(20, 20, 40, 0, 2)
    a = ev.analyse(sc, "empty", "dfs")
    assert (a.greedy["edge"].count, a.greedy["edge"].cost) == (17, 232) and a.opt == optimum(sc) and a.result.start == ()


# --- Vergleichstabelle, Verteilung, Aufwand -----------------------------------------------------------------------------------------------

def test_compare_table_has_six_rows_with_the_same_final_pair_count():
    rows = ev.compare_table(generate(15, 15, 40, 0, 5))
    assert len(rows) == 6 and {(r["start"], r["search"]) for r in rows} == {(s, t) for s in STARTS for t in SEARCHES}
    assert len({r["count"] for r in rows}) == 1


def test_distribution_fields_and_shares():
    d = ev.distribution(20, 20, 40, 0, "edge", "bfs")
    assert d["n_seeds"] == 100 == d["n_valid"] == len(d["rounds_list"]) and d["share_max_pairs"] == 1.0
    assert 0.0 <= d["share_optimal_cost"] <= 1.0 and len(d["cost_gaps"]) == 100 and d["cost_gap_p90"] >= d["cost_gap_median"]
    assert d["start_pairs_mean"] <= d["opt_pairs_mean"] and d["rounds_max"] >= d["rounds_mean"]


def test_distribution_is_repeatable_and_independent_of_the_user_seed():
    assert ev.distribution(15, 15, 40, 25, "order", "dfs") == ev.distribution(15, 15, 40, 25, "order", "dfs")


def test_distribution_without_feasible_pairs():
    bad = tuple(s for s in range(60) if not generate(3, 3, 10, 0, s).feasible.any())
    assert len(bad) >= 3
    d = ev.distribution(3, 3, 10, 0, "edge", "bfs", seeds=bad)
    assert d["n_valid"] == 0 and d["rounds_mean"] is None and d["cost_gap_median"] is None and d["share_max_pairs"] == 0.0


def test_effort_table_rows():
    rows = ev.effort_table(20, 20, 40, 0)
    assert len(rows) == 6 and all(r["share_max_pairs"] == 1.0 for r in rows)


def test_reach_sweep_rows():
    rows = ev.reach_sweep(15, 15, 0, "edge", "bfs", values=(10, 40, 150), seeds=C.SWEEP_SEEDS[:10])
    assert [r["x"] for r in rows] == [10, 40, 150] and rows[-1]["rounds_mean"] == 0.0


def test_scaling_rows_and_reach_rule():
    rows = ev.scaling(ns=(10, 20), seeds=C.SCALE_SEEDS[:3])
    assert [r["n"] for r in rows] == [10, 20] and [r["reach"] for r in rows] == [57, 40]
    assert all(set(r) >= {("edge", "bfs"), ("empty", "dfs"), "edges", "reach"} for r in rows)


def test_cell_rows_are_integers():
    rows = ev.cell_rows(10, 10, 40, 0, tuple(C.SWEEP_SEEDS[:5]))
    assert all(isinstance(v, int) for row in rows for key, val in row.items() for v in (val if isinstance(val, tuple) else (val,)))
