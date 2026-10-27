"""Darstellung "Zwei Seiten": Fahrzeuge links, Aufträge rechts. Nur Koordinaten ändern sich; Kosten, Paare und Wege bleiben die der Karte."""

from pathlib import Path

import numpy as np
import pytest
from streamlit.testing.v1 import AppTest

import ap_constants as C
import ap_evaluation as ev
from ap_scenario import build
from ap_visualization import arrange, build_cover_map, build_state_map

APP = Path(__file__).resolve().parent.parent / "app.py"
CASES = [("random", 20, 20, 40, 0, 165), ("random", 8, 8, 25, 50, 7), ("random", 5, 12, 40, 0, 3), ("steal", 20, 20, 40, 0, 165), ("p4", 20, 20, 40, 0, 165)]


@pytest.mark.parametrize("params", CASES)
def test_arrange_puts_each_side_in_its_own_column_with_distinct_places(params):
    sc = build(*params)
    arr = arrange(sc, "bipartit")
    assert {x for x, _ in arr.vehicles} == {0} and {x for x, _ in arr.orders} == {100}
    assert len(set(arr.vehicles)) == sc.n and len(set(arr.orders)) == sc.m          # jede Ecke hat ihren eigenen Platz
    assert all(0 <= y <= 100 for _, y in arr.vehicles + arr.orders)


@pytest.mark.parametrize("params", CASES)
def test_arrange_changes_only_the_coordinates(params):
    sc = build(*params)
    arr = arrange(sc, "bipartit")
    assert np.array_equal(arr.cost, sc.cost) and np.array_equal(arr.feasible, sc.feasible) and arr.reach == sc.reach
    assert arr.n == sc.n and arr.m == sc.m


def test_arrange_map_is_the_identity_and_is_repeatable():
    sc = build("random", 20, 20, 40, 0, 165)
    assert arrange(sc, "map") is sc
    first, second = arrange(sc, "bipartit"), arrange(sc, "bipartit")
    assert first.vehicles == second.vehicles and first.orders == second.orders


def test_every_edge_of_the_two_sided_drawing_joins_the_two_columns():
    """Das ist die Aussage "bipartit" im Bild: jede gezeichnete mögliche Kante beginnt links (Fahrzeug) und endet rechts (Auftrag)."""
    sc = build("random", 12, 12, 40, 0, 165)
    arr = arrange(sc, "bipartit")
    for i in range(sc.n):
        for j in range(sc.m):
            if sc.feasible[i, j]:
                assert arr.vehicles[i][0] < arr.orders[j][0]


def test_barycenter_order_does_not_cross_more_than_the_map_order():
    """Die Anordnung nach den Plätzen der Partner kreuzt im Mittel nicht mehr als die reine Sortierung nach Kartenlage."""
    def crossings(sc, arr):
        es = [(arr.vehicles[i][1], arr.orders[j][1]) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j]]
        return sum(1 for a in range(len(es)) for b in range(a + 1, len(es)) if (es[a][0] - es[b][0]) * (es[a][1] - es[b][1]) < 0)

    from ap_visualization import _two_sided_order
    better = 0
    for seed in range(100000, 100008):
        sc = build("random", 12, 12, 30, 0, seed)
        vo, oo = _two_sided_order(sc, sweeps=0)
        base = arrange(sc, "bipartit")
        v0 = {i: 100 - 100 * r / (sc.n - 1) for r, i in enumerate(vo)}
        o0 = {j: 100 - 100 * r / (sc.m - 1) for r, j in enumerate(oo)}
        from dataclasses import replace
        plain = replace(sc, vehicles=tuple((0, v0[i]) for i in range(sc.n)), orders=tuple((100, o0[j]) for j in range(sc.m)))
        better += crossings(sc, base) <= crossings(sc, plain)
    assert better == 8


@pytest.mark.parametrize("layout", list(C.LAYOUT_LABELS))
@pytest.mark.parametrize("params", CASES)
def test_both_figures_build_in_both_layouts(params, layout):
    a = ev.analyse(build(*params))
    sc, res = a.scenario, a.result
    figs = [build_state_map(sc, res.pairs, layout=layout), build_cover_map(sc, res.pairs, res.cover_v, res.cover_o, layout=layout)]
    if res.rounds:
        figs.append(build_state_map(sc, res.states[0], res.rounds[0].path, layout=layout))
    for fig in figs:
        assert len(fig.data) >= 2
        headers = {a.text for a in fig.layout.annotations if a.text and "<b>" in a.text}
        assert headers == ({"<b>Fahrzeuge</b>", "<b>Aufträge</b>"} if layout == "bipartit" else set())


def test_two_sided_drawing_has_the_same_markers_as_the_map_and_no_invented_coordinates():
    a = ev.analyse(build("random", 8, 8, 40, 0, 165))
    sc, res = a.scenario, a.result
    rows = {}
    for layout in C.LAYOUT_LABELS:
        fig = build_state_map(sc, res.pairs, layout=layout)
        rows[layout] = sorted(h for t in fig.data if t.hovertext is not None for h in t.hovertext)
    assert len(rows["map"]) == len(rows["bipartit"]) and rows["map"]
    assert all("(" in h for h in rows["map"]) and not any("(" in h for h in rows["bipartit"])


def test_cost_labels_in_the_two_sided_layout_do_not_share_one_place():
    """Alle Kanten haben dieselbe Mitte in x; die Kostenbeschriftungen sind deshalb entlang der Kante versetzt."""
    a = ev.analyse(build("random", 8, 8, 40, 0, 165))
    fig = build_state_map(a.scenario, a.result.pairs, layout="bipartit")
    labels = [t for t in fig.data if t.mode == "text"][0]
    assert len(set(zip(labels.x, labels.y))) == len(labels.x) and len(set(labels.x)) > 1


@pytest.mark.parametrize("search", list(C.SEARCH_LABELS))
def test_app_runs_in_the_two_sided_layout(search):
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["layout"] = "bipartit"
    at.query_params["search"] = search
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    assert at.radio(key="layout_radio").value == "bipartit"
    at.radio(key="layout_radio").set_value("map").run()
    assert not at.exception and at.radio(key="layout_radio").value == "map"


def test_unknown_layout_in_the_permalink_falls_back_to_the_map():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["layout"] = "kreis"
    at.run()
    assert not at.exception and at.radio(key="layout_radio").value == C.DEFAULT_LAYOUT
