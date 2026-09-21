"""Presets: vollständig, in den Grenzen, und jede Beispielkarte zeigt, was ihr Hilfetext behauptet."""

import numpy as np
import pytest

import ap_constants as C
import ap_evaluation as ev
import ap_presets as P
from ap_scenario import build

KEYS = set(P.PRESET_KEYS)


def _sc(p):
    return build(p["net"], p["n"], p["m"], p["reach"], p["ballung"], p["seed"])


def test_every_preset_has_help_and_all_keys():
    assert set(C.PRESETS) == set(C.PRESET_HELP) and len(C.PRESETS) == 8
    assert all(C.PRESET_HELP[name].strip() for name in C.PRESETS)
    for name, p in C.PRESETS.items():
        assert set(p) == KEYS, name


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_values_are_inside_the_bounds_and_on_the_step_grid(name):
    p = C.PRESETS[name]
    assert p["net"] in C.NETS and p["start"] in C.START_LABELS and p["search"] in C.SEARCH_LABELS
    for key, state_key in P.PRESET_KEYS.items():
        spec = P.SETTING_SPECS[state_key]
        if spec.lo is not None:
            assert spec.lo <= p[key] <= spec.hi, (name, key)
    assert (p["reach"] - C.REACH_MIN) % 5 == 0 and p["ballung"] % 25 == 0


def test_setting_specs_have_room_to_move():
    """Ein Regler mit lo == hi würde Streamlit abstürzen lassen."""
    assert all(spec.lo < spec.hi for spec in P.SETTING_SPECS.values() if spec.lo is not None)


def test_presets_use_seeds_outside_the_distribution_set():
    for name, p in C.PRESETS.items():
        assert p["seed"] not in C.DIST_SEEDS, name


def test_defaults_equal_the_mid_reach_preset():
    p = C.PRESETS["🗺️ Mittlere Reichweite"]
    assert (p["n"], p["m"], p["reach"], p["ballung"], p["seed"], p["start"], p["search"]) == (C.DEFAULT_N, C.DEFAULT_M, C.DEFAULT_REACH, C.DEFAULT_BALLUNG, C.DEFAULT_SEED, C.DEFAULT_START, C.DEFAULT_SEARCH)


def test_the_three_mid_reach_presets_share_one_map():
    mid, empty, dfs = (C.PRESETS[k] for k in ("🗺️ Mittlere Reichweite", "🕳️ Von leer starten", "🌲 Tiefensuche"))
    assert all(p[k] == mid[k] for p in (empty, dfs) for k in ("net", "n", "m", "reach", "ballung", "seed"))
    assert (empty["start"], empty["search"], dfs["start"], dfs["search"]) == ("empty", "bfs", "edge", "dfs")


EXPECTED = {   # Einordnung der gezeigten Karte (Paarzahl ist immer größtmöglich; es geht um die Kosten)
    "⚖️ Nichts zu verbessern": ev.COSTLIER, "🔗 Pfad aus vier Punkten": ev.OPTIMAL, "⛓️ Lange Kette": ev.OPTIMAL, "🗺️ Mittlere Reichweite": ev.COSTLIER,
    "🕳️ Von leer starten": ev.COSTLIER, "🌐 Alles erreichbar": ev.COSTLIER, "📡 Knappe Reichweite": ev.OPTIMAL, "🌲 Tiefensuche": ev.COSTLIER,
}


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_preset_shows_the_class_it_promises(name):
    p = C.PRESETS[name]
    a = ev.analyse(_sc(p), p["start"], p["search"])
    _, code, d = ev.verdict(a)
    assert code == EXPECTED[name] and d["pairs_max"]


@pytest.mark.parametrize("name", [n for n, p in C.PRESETS.items() if p["net"] == "random"])
def test_random_preset_is_a_typical_draw(name):
    """Die gezeigte Karte gehört zur häufigsten Klasse der 100 festen Karten, hat die mediane Rundenzahl (±1) und liegt bei den Mehrkosten nahe am Median (kein dramatisch ausgesuchtes Beispiel)."""
    p = C.PRESETS[name]
    dist = ev.distribution(p["n"], p["m"], p["reach"], p["ballung"], p["start"], p["search"])
    a = ev.analyse(_sc(p), p["start"], p["search"])
    _, code, d = ev.verdict(a)
    modal = ev.OPTIMAL if dist["share_optimal_cost"] >= 0.5 else ev.COSTLIER
    assert code == modal
    assert abs(d["rounds"] - float(np.median(dist["rounds_list"]))) <= 1
    if code == ev.COSTLIER:
        assert abs(d["cost_gap_pct"] - dist["cost_gap_median"]) <= 3.0


def test_the_presets_are_not_all_bad_news():
    """Positive UND negative Aussagen: mindestens ein Preset zeigt, dass es reicht (Paare und Kosten optimal), mindestens fünf zeigen die Kostenschwäche."""
    classes = [EXPECTED[n] for n in C.PRESETS]
    assert classes.count(ev.OPTIMAL) >= 1 and classes.count(ev.COSTLIER) >= 5


def test_fixed_presets_hide_the_random_controls():
    assert {n for n, p in C.PRESETS.items() if p["net"] in C.FIXED_NETS} == {"⚖️ Nichts zu verbessern", "🔗 Pfad aus vier Punkten", "⛓️ Lange Kette"}
