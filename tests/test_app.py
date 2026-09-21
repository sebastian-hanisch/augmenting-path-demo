"""Rauchtests der Streamlit-Oberfläche per AppTest: Standard, jedes Preset, alle Kombinationen aus Start und Suche, Randgrößen, Schritt-Zustand, ausgeblendete Regler, Permalink, Experimente auf Abruf, Schlüssel und Achsensperre."""

import re
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

import ap_constants as C
from ap_presets import PRESET_KEYS

ROOT = Path(__file__).resolve().parent.parent
APP = ROOT / "app.py"

# Anfang der Meldung zur gezeigten Karte und (bei Zufallskarten) der Meldung zur Verteilung (Streamlit legt das führende Emoji in `icon`, nicht in `value`)
EXPECTED = {
    "⚖️ Nichts zu verbessern": ("Größtmögliche Paarzahl (2), aber die Kosten liegen bei 18 statt 10 Minuten", None),
    "🔗 Pfad aus vier Punkten": ("Größtmögliche Paarzahl (2) und auch die Kosten sind optimal: 20 Minuten", None),
    "⛓️ Lange Kette": ("Größtmögliche Paarzahl (7) und auch die Kosten sind optimal: 70 Minuten", None),
    "🗺️ Mittlere Reichweite": ("Größtmögliche Paarzahl (20), aber die Kosten liegen bei 409 statt 380 Minuten", "Die Paarzahl ist auf 100 %"),
    "🕳️ Von leer starten": ("Größtmögliche Paarzahl (20), aber die Kosten liegen bei 513 statt 380 Minuten", "Die Paarzahl ist auf 100 %"),
    "🌐 Alles erreichbar": ("Größtmögliche Paarzahl (20), aber die Kosten liegen bei 614 statt 538 Minuten", "Die Paarzahl ist auf 100 %"),
    "📡 Knappe Reichweite": ("Größtmögliche Paarzahl (8) und auch die Kosten sind optimal: 58 Minuten", "Auf 95 %"),
    "🌲 Tiefensuche": ("Größtmögliche Paarzahl (20), aber die Kosten liegen bei 470 statt 380 Minuten", "Die Paarzahl ist auf 100 %"),
}


def _run(setup=None, timeout=600):
    at = AppTest.from_file(str(APP), default_timeout=timeout)
    at.run()
    assert not at.exception, [e.value for e in at.exception]
    if setup is not None:
        setup(at)
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    return at


def _apply(at, p):
    for key, state_key in PRESET_KEYS.items():
        at.session_state[state_key] = p[key]


def _labels(at):
    return {w.label for w in list(at.sidebar.slider) + list(at.sidebar.selectbox) + list(at.sidebar.number_input) + list(at.sidebar.radio)}


def _texts(at):
    return [e.value for e in list(at.success) + list(at.warning) + list(at.info)]


def _has(at, prefix):
    return any(t.startswith(prefix) for t in _texts(at))


def _step(at):
    found = [s for s in at.slider if s.key == "ap_step"]
    return found[0] if found else None


def test_default_renders_without_exception():
    at = _run()
    assert any("Verbesserungswege in Aktion" in m.value for m in at.markdown)
    assert _has(at, EXPECTED["🗺️ Mittlere Reichweite"][0]) and not at.error


@pytest.mark.parametrize("name", list(C.PRESETS))
def test_every_preset_renders_with_its_verdicts(name):
    at = _run(lambda a: _apply(a, C.PRESETS[name]))
    top, dist = EXPECTED[name]
    assert _has(at, top), _texts(at)
    if dist is not None:
        assert _has(at, dist), _texts(at)
    else:
        assert any(t.startswith("Feste Karte") for t in _texts(at))


@pytest.mark.parametrize("start", list(C.START_LABELS))
@pytest.mark.parametrize("search", list(C.SEARCH_LABELS))
def test_every_start_and_search_reaches_the_maximum_on_the_default_map(start, search):
    at = _run(lambda a: (a.session_state.__setitem__("start_radio", start), a.session_state.__setitem__("search_radio", search)))
    assert not at.error and [m.value for m in at.metric if m.label == "Paare (Ergebnis)"] == ["20 von 20"]


def test_extreme_sizes_render():
    for n, m, reach in ((C.N_MIN, C.M_MIN, C.REACH_MIN), (C.N_MAX, C.M_MAX, C.REACH_MAX), (C.N_MIN, C.M_MAX, C.REACH_MIN), (C.N_MAX, C.M_MIN, C.REACH_MAX)):
        def setup(at, n=n, m=m, reach=reach):
            at.session_state["n_slider"], at.session_state["m_slider"], at.session_state["reach_slider"] = n, m, reach
        at = _run(setup)
        step = _step(at)
        assert step is None or step.value == step.max


def test_hidden_controls_follow_the_net():
    def labels_for(net):
        return _labels(_run(lambda a: a.session_state.__setitem__("net_select", net)))
    random_labels, fixed = labels_for("random"), labels_for("chain")
    assert {"Karte", "Start", "Wegesuche", "Fahrzeuge", "Aufträge", "Reichweite [min]", "Ballung [%]", "Zufalls-Seed"} <= random_labels
    assert fixed == {"Karte", "Start", "Wegesuche"}                                             # keine toten Regler bei festen Karten


def test_hidden_slider_values_come_back_when_the_random_map_is_shown_again():
    at = _run(lambda a: a.session_state.__setitem__("reach_slider", 90))
    at.session_state["net_select"] = "steal"
    at.run()
    at.session_state["net_select"] = "random"
    at.run()
    assert not at.exception and at.slider(key="reach_slider").value == 90


def test_round_slider_returns_to_the_last_round_when_the_map_changes():
    at = _run()
    assert _step(at).max == 3 and _step(at).value == 3
    _step(at).set_value(1)
    at.run()
    assert _step(at).value == 1
    at.session_state["net_select"] = "p4"
    at.run()
    assert not at.exception and _step(at).value == 1 == _step(at).max


def test_round_slider_at_zero_shows_the_first_path():
    at = _run()
    _step(at).set_value(0)
    at.run()
    assert not at.exception and any("Weg dieser Runde:" in c.value for c in at.caption)


def test_no_round_slider_when_there_is_nothing_to_improve():
    at = _run(lambda a: a.session_state.__setitem__("net_select", "steal"))
    assert _step(at) is None and any(b.label == "▶️ Abspielen" and b.disabled for b in at.button)
    assert any("Die letzte Suche" in c.value for c in at.caption)                               # rechts der Beweis


def test_play_runs_through_all_rounds():
    at = _run(lambda a: a.session_state.__setitem__("net_select", "p4"))
    [b for b in at.button if b.label == "▶️ Abspielen"][0].click()
    at.run()
    assert not at.exception


def test_permalink_parameters_are_clamped_and_snapped():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["reach"] = "9999"
    at.query_params["ballung"] = "abc"
    at.query_params["n"] = "-5"
    at.run()
    assert not at.exception
    assert at.slider(key="reach_slider").value == C.REACH_MAX and at.slider(key="ballung_slider").value == C.DEFAULT_BALLUNG and at.slider(key="n_slider").value == C.N_MIN
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["reach"] = "42"
    at.query_params["ballung"] = "60"
    at.run()
    assert at.slider(key="reach_slider").value == 40 and at.slider(key="ballung_slider").value == 50      # auf die Regler-Schritte gerundet


def test_unknown_values_in_the_permalink_fall_back_to_the_defaults():
    at = AppTest.from_file(str(APP), default_timeout=600)
    at.query_params["net"] = "ring"
    at.query_params["start"] = "zufall"
    at.query_params["search"] = "sprung"
    at.run()
    assert not at.exception and at.selectbox(key="net_select").value == C.DEFAULT_NET
    assert at.radio(key="start_radio").value == C.DEFAULT_START and at.radio(key="search_radio").value == C.DEFAULT_SEARCH


def test_randomize_moves_the_seed_but_not_the_distribution():
    at = _run()
    before = {m.label: m.value for m in at.metric}
    seed_before = at.number_input(key="seed_input").value
    [b for b in at.sidebar.button if "Neue Karte" in b.label][0].click()
    at.run()
    assert not at.exception and at.number_input(key="seed_input").value != seed_before
    after = {m.label: m.value for m in at.metric}
    for label in ("Größtmögliche Paarzahl", "Mehrkosten (Median)", "Kosten optimal"):
        assert before[label] == after[label], label


def test_experiments_run_on_demand():
    at = _run()
    assert not any("Mittel über 40 feste Karten je Reichweite" in c.value for c in at.caption)
    assert not any("Gezählt werden **durchsuchte Kanten**" in c.value for c in at.caption)
    for key in ("sweep_start", "scaling_start"):
        at.button(key=key).click()
        at.run()
        assert not at.exception, [e.value for e in at.exception]
    text = " ".join(c.value for c in at.caption)
    assert "Mittel über 40 feste Karten je Reichweite" in text and "Gezählt werden **durchsuchte Kanten**" in text


def test_sweep_on_a_fixed_map_with_the_other_search():
    at = _run(lambda a: (a.session_state.__setitem__("net_select", "steal"), a.session_state.__setitem__("search_radio", "dfs")))
    at.button(key="sweep_start").click()
    at.run()
    assert not at.exception


def _calls(src, name):
    """Der Text jedes Aufrufs `name(...)` einschließlich verschachtelter Klammern."""
    out = []
    for m in re.finditer(re.escape(name) + r"\(", src):
        depth, i = 1, m.end()
        while depth:
            depth += {"(": 1, ")": -1}.get(src[i], 0)
            i += 1
        out.append(src[m.start():i])
    return out


def test_every_plotly_chart_has_an_explicit_key_and_axes_are_locked():
    calls = _calls(APP.read_text(encoding="utf-8"), "plotly_chart")
    assert len(calls) == 9 and all(re.search(r'key=f?"[a-z_]+(_\{\w+\})?"', c) for c in calls), calls
    assert len({re.search(r'key=f?"([a-z_]+?)(?:_\{\w+\})?"', c).group(1) for c in calls}) == 9            # jeder Schlüssel nur einmal
    viz = (ROOT / "ap_visualization.py").read_text(encoding="utf-8")
    bodies = [b for b in viz.split(chr(10) + "def ") if b.startswith("build_")]
    assert "fixedrange=True" in viz and len(bodies) == 7 and all("_base(" in b or "_map_layout(" in b for b in bodies)


def test_app_text_has_no_links_to_repository_files():
    assert not re.search(r"\]\(\w+\.py\)", APP.read_text(encoding="utf-8"))


def test_footer_is_verbatim():
    src = APP.read_text(encoding="utf-8")
    assert "https://sebastianhanisch.net/kontakt.html" in src and "Interesse an einer maßgeschneiderten Lösung für" in src and "Operations Research und Machine Learning" in src


def test_runtime_needs_only_numpy_pandas_plotly_streamlit():
    """Konvention der Konzepte-Wurzeln und -Stücke: Referenzbibliotheken (scipy, networkx) nur als Testorakel."""
    req = (ROOT / "requirements.txt").read_text(encoding="utf-8").lower()
    assert "scipy" not in req and "networkx" not in req
    for path in ROOT.glob("*.py"):
        assert not re.search(r"^\s*(import|from)\s+(scipy|networkx)\b", path.read_text(encoding="utf-8"), re.M), path.name


def test_play_runs_through_all_frames_without_duplicate_chart_keys():
    """Beim Abspielen entstehen in einem Lauf mehrere Diagramme mit demselben Namen - die Schlüssel tragen deshalb den Schritt (Regression: StreamlitDuplicateElementKey bei mehr als einem Bild)."""
    at = _run()
    [b for b in at.button if b.label == "▶️ Abspielen"][0].click()
    at.run()
    assert not at.exception, [e.value for e in at.exception]
