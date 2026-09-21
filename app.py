"""Augmentierende Pfade - eine Zuordnung darf wieder freigegeben werden - interaktive Konzept-Demo
Sebastian Hanisch - Operations Research und Machine Learning

Anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo EIN Verfahren - Verbesserungswege im bipartiten Matching - und lässt stattdessen das Beispiel wachsen.
Zweites Stück der Matching-Linie der "Konzepte"-Reihe, Fortsetzung der Greedy-Matching-Demo: sie behebt deren Schwäche (eine gewählte Zuordnung bleibt). Siehe README für die Einordnung.

Lauffähig mit: streamlit run app.py
"""

import time

import streamlit as st

import ap_constants as C
import ap_evaluation as ev
from ap_presets import (
    KEPT,
    apply_preset,
    bounds,
    init_session_state_defaults,
    load_permalink_settings,
    randomize_seed,
    sync_query_params,
)
from ap_scenario import build
from ap_visualization import build_cover_map, build_gap_compare, build_reach_sweep, build_rounds, build_rounds_hist, build_scaling, build_state_map

st.set_page_config(page_title="Augmentierende Pfade – Sebastian Hanisch", layout="wide")


def _pct(x, digits=0):
    return "–" if x is None else f"{x:.{digits}f} %".replace(".", ",")


def _share(x):
    """Anteil (0..1) als 'nn %'."""
    return f"{100 * x:.0f} %"


def _f(x, digits=1):
    return "–" if x is None else f"{x:.{digits}f}".replace(".", ",")


def _path_text(path):
    """'+F1–A1, −F2–A1, ...': + wird gewählt, − wird freigegeben."""
    return ", ".join(f"{'+' if kind == 'add' else '−'}F{i + 1}–A{j + 1}" for i, j, kind in path)


@st.cache_resource(show_spinner=False, max_entries=16)
def _analysis(params, start, search):
    return ev.analyse(build(*params), start, search)


@st.cache_data(show_spinner=False)
def _compare(params):
    return ev.compare_table(build(*params))


@st.cache_data(show_spinner=False)
def _distribution(n, m, reach, ballung, start, search):
    return ev.distribution(n, m, reach, ballung, start, search)


@st.cache_data(show_spinner=False)
def _effort(n, m, reach, ballung):
    return ev.effort_table(n, m, reach, ballung)


@st.cache_data(show_spinner=False)
def _reach_sweep(n, m, ballung, start, search):
    return ev.reach_sweep(n, m, ballung, start, search)


@st.cache_data(show_spinner=False)
def _scaling():
    return ev.scaling()


st.title("🔁 Augmentierende Pfade – eine Zuordnung darf wieder freigegeben werden")
st.markdown(
    """
Greedy legt Zuordnungen fest und nimmt sie **nie zurück** - und verliert deshalb auf den meisten Karten Paare. **Augmentierende Pfade** (Verbesserungswege) beheben genau das:
ein Weg beginnt bei einem **freien Fahrzeug**, geht über eine nicht gewählte Kante zu einem Auftrag, von dort über dessen **gewählte** Kante zurück zu seinem Fahrzeug, wieder über eine nicht gewählte Kante zu einem Auftrag, und so weiter,
bis er bei einem **freien Auftrag** endet. Klappt man den Weg um - gewählte Kanten werden frei, nicht gewählte gewählt -, ist ein Paar **mehr** entstanden. Gibt es keinen solchen Weg mehr, ist die Paarzahl größtmöglich (Berge).
Der Haken: die Suche **zählt Paare, nicht Kosten**. Diese Demo zeigt beides - dass die Paarzahl auf jeder Karte größtmöglich wird, und was dabei aus den Kosten wird.
"""
)
st.caption(
    "Anders als die Fall-Demos im Portfolio, die an einem Anwendungsfall mehrere Verfahren vergleichen, zeigt diese Demo - zweites Stück der Matching-Linie der \"Konzepte\"-Reihe, Fortsetzung der Greedy-Matching-Demo - **ein** Verfahren an einem wachsenden Beispiel. "
    "Die Schwächen dieses Stücks sind die Ansatzpunkte der nächsten: **Ungarische Methode** (die Kosten entscheiden, welche Kanten weichen), **Hopcroft–Karp** (viele kürzeste Wege je Suche) und **Blossom** (auch Paare innerhalb einer Gruppe) - noch nicht gebaut. "
    "Das Optimum in dieser Demo kommt aus der kleinen exakten Referenz der Greedy-Matching-Demo, die hier nur zum Messen dient."
)

with st.expander("So funktionieren augmentierende Pfade", expanded=True):
    st.markdown(
        """
1. **Wechselweg:** Start an einem *freien* Fahrzeug; abwechselnd eine *nicht gewählte* Kante (Fahrzeug → Auftrag) und eine *gewählte* Kante (Auftrag → sein Fahrzeug). Ein **Verbesserungsweg** endet an einem *freien* Auftrag - er hat immer eine nicht gewählte Kante mehr als gewählte.
2. **Umklappen:** die nicht gewählten Kanten des Wegs werden gewählt, die gewählten freigegeben. Jedes Fahrzeug und jeder Auftrag auf dem Weg hat danach wieder genau einen Partner, nur die beiden Enden sind neu dazugekommen: **ein Paar mehr**.
3. **Berge:** ein Matching ist genau dann größtmöglich, wenn es **keinen** Verbesserungsweg gibt. Man sucht also, klappt um und sucht wieder - bis die Suche scheitert.
4. **Wegesuche:** die **Breitensuche** startet von allen freien Fahrzeugen gleichzeitig und findet einen *kürzesten* Weg; die **Tiefensuche** (Kuhn) versucht es von einem freien Fahrzeug nach dem anderen und findet irgendeinen, oft sehr langen Weg. Beide finden immer dieselbe Paarzahl.
5. **Beweis:** die erfolglose Suche liefert eine Menge von Ecken (die *Überdeckung*), die jede mögliche Kante berührt und genau so viele Ecken hat wie das Matching Paare - mehr Paare kann es dann nicht geben.
        """
    )

st.caption("🎯 Schnellstart – eine Beispielkarte laden:")
names = list(C.PRESETS.keys())
for row in range(0, len(names), 4):
    preset_cols = st.columns(4)
    for col, name in zip(preset_cols, names[row:row + 4]):
        with col:
            st.button(name, width="stretch", on_click=apply_preset, args=(name,), help=C.PRESET_HELP[name])

st.caption(
    "🔗 Die Adresszeile oben spiegelt Ihre aktuelle Konfiguration wider – einfach kopieren, "
    "um ein Szenario zu teilen."
)

load_permalink_settings()
init_session_state_defaults()

with st.sidebar:
    st.header("⚙️ Einstellungen")
    net_key = st.selectbox(
        "Karte", list(C.NETS), key="net_select", format_func=lambda k: C.NETS[k],
        help="Eine zufällige Karte mit Fahrzeugen und Aufträgen, oder eine der festen Lehrbuchkarten, an denen sich der Verbesserungsweg von Hand nachrechnen lässt (die lange Kette braucht einen Weg durch alle 13 Kanten).",
    )
    start = st.radio(
        "Start", list(C.START_LABELS), key="start_radio", format_func=lambda k: C.START_LABELS[k],
        help="Wovon aus die Verbesserungswege starten: von der leeren Paarung oder vom Ergebnis einer Greedy-Regel aus der Greedy-Matching-Demo. Bei Reichweite 40 braucht es vom leeren Start im Mittel 19,5 Verbesserungswege, "
             "von Greedy 'Billigste Kante zuerst' aus 2,7 - dafür liegen die Kosten dann im Median 8 % statt 36 % über dem Optimum.",
    )
    search = st.radio(
        "Wegesuche", list(C.SEARCH_LABELS), key="search_radio", format_func=lambda k: C.SEARCH_LABELS[k],
        help="Beide Suchen finden auf jeder Karte die größtmögliche Paarzahl. Bei Reichweite 40 und Start von Greedy sind die Wege der Tiefensuche im Mittel 15,6 Kanten lang, die der Breitensuche 4,3; "
             "die Kosten liegen im Median 27 % gegen 8 % über dem Optimum.",
    )
    if net_key == "random":
        n = st.slider("Fahrzeuge", *bounds("n_slider"), key="n_slider", help="Anzahl der Fahrzeuge.")
        st.session_state[KEPT["n_slider"]] = n
        m = st.slider("Aufträge", *bounds("m_slider"), key="m_slider", help="Anzahl der Aufträge.")
        st.session_state[KEPT["m_slider"]] = m
        reach = st.slider(
            "Reichweite [min]", *bounds("reach_slider"), key="reach_slider", step=5,
            help="Wie weit ein Fahrzeug höchstens fahren darf. Bei 10 hat Greedy auf 80 von 100 Karten schon die größtmögliche Paarzahl, bei 40 fehlen im Mittel 2,7 Paare, bei 150 keins - dafür bleibt die Kostenlücke von 14 %.",
        )
        st.session_state[KEPT["reach_slider"]] = reach
        ballung = st.slider("Ballung [%]", *bounds("ballung_slider"), key="ballung_slider", step=25, help="0 = Fahrzeuge und Aufträge gleichmäßig verteilt, 100 = alle um drei Stadtteile gruppiert.")
        st.session_state[KEPT["ballung_slider"]] = ballung
        seed = st.number_input("Zufalls-Seed", *bounds("seed_input"), key="seed_input", step=1)
        st.session_state[KEPT["seed_input"]] = seed
        st.button("🎲 Neue Karte generieren", width="stretch", on_click=randomize_seed, help="Würfelt einen neuen Zufalls-Seed. Die Verteilung über 100 feste Karten weiter unten ändert sich dabei nicht - nur die Marke „Ihre Ziehung“ wandert.")
    else:
        n = int(st.session_state.get(KEPT["n_slider"], C.DEFAULT_N))
        m = int(st.session_state.get(KEPT["m_slider"], C.DEFAULT_M))
        reach = int(st.session_state.get(KEPT["reach_slider"], C.DEFAULT_REACH))
        ballung = int(st.session_state.get(KEPT["ballung_slider"], C.DEFAULT_BALLUNG))
        seed = int(st.session_state.get(KEPT["seed_input"], C.DEFAULT_SEED))
        st.caption("Diese Karte ist fest - es gibt nichts zu erzeugen. Zahl der Fahrzeuge und Aufträge, Reichweite, Ballung und Seed gehören zur zufälligen Karte.")

sync_query_params({"net_select": net_key, "start_radio": start, "search_radio": search, "n_slider": int(n), "m_slider": int(m), "reach_slider": int(reach), "ballung_slider": int(ballung), "seed_input": int(seed)})

# feste Karten ignorieren die Zufallsregler: sonst würden gleiche Karten unter verschiedenen Schlüsseln mehrfach berechnet
params = (net_key, int(n), int(m), int(reach), int(ballung), int(seed))
if net_key in C.FIXED_NETS:
    params = (net_key, C.DEFAULT_N, C.DEFAULT_M, C.DEFAULT_REACH, C.DEFAULT_BALLUNG, C.DEFAULT_SEED)
with st.spinner("Rechne..."):
    a = _analysis(params, start, search)
sc, res, opt = a.scenario, a.result, a.opt
level, code, d = ev.verdict(a)
n_rounds = len(res.rounds)

# --- Verbesserungswege in Aktion -------------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Verbesserungswege in Aktion")
if st.session_state.get("ap_step_owner") != (params, start, search):
    st.session_state["ap_step"] = n_rounds
    st.session_state["ap_step_owner"] = (params, start, search)
step_col, play_col = st.columns([5, 2])
with step_col:
    if n_rounds > 0:
        step = st.slider("Runde", 0, n_rounds, key="ap_step", help="Wie viele Verbesserungswege schon umgeklappt sind. Bei 0 ist der Start zu sehen, mit dem ersten Weg; ganz rechts das fertige Matching und der Beweis.")
    else:
        step = 0
        st.caption("Hier gibt es keinen Verbesserungsweg: das Start-Matching hat schon die größtmögliche Paarzahl. Rechts der Beweis dafür.")
with play_col:
    auto_play = st.button("▶️ Abspielen", width="stretch", disabled=n_rounds == 0)
view_slot = st.empty()


def _render(k):
    """Runde k: links der Zustand nach k Umklappungen (mit dem Weg der nächsten Runde), rechts der Zustand danach; am Ende der Beweis."""
    with view_slot.container():
        pairs_k = res.states[k]
        c1, c2 = st.columns(2)
        if k < n_rounds:
            rnd = res.rounds[k]
            c1.markdown(f"**Vor Runde {k + 1}** - der Weg: {rnd.length} Kanten")
            c1.plotly_chart(build_state_map(sc, pairs_k, rnd.path), width="stretch", key=f"map_before_{k}")
            c2.markdown(f"**Nach Runde {k + 1}** - {rnd.pairs_after} Paare")
            c2.plotly_chart(build_state_map(sc, res.states[k + 1]), width="stretch", key=f"map_after_{k}")
            st.caption(f"Weg dieser Runde: {_path_text(rnd.path)} (+ wird gewählt, − wird freigegeben). Die Suche hat dafür {rnd.scanned} Kanten durchsucht.")
        else:
            c1.markdown(f"**Ergebnis** - {res.count} Paare, {res.cost} Minuten")
            c1.plotly_chart(build_state_map(sc, pairs_k), width="stretch", key=f"map_result_{k}")
            c2.markdown(f"**Beweis:** {len(res.cover_v) + len(res.cover_o)} Ecken überdecken alle möglichen Paare")
            c2.plotly_chart(build_cover_map(sc, res.pairs, res.cover_v, res.cover_o), width="stretch", key=f"map_proof_{k}")
            st.caption(f"Die letzte Suche ({res.final_scanned} durchsuchte Kanten) findet keinen Verbesserungsweg. Die violetten Ecken - {len(res.cover_v)} Fahrzeuge und {len(res.cover_o)} Aufträge - berühren jede mögliche Kante (blasse Linien); "
                       f"da es genau so viele Ecken wie Paare ({res.count}) sind, kann kein Matching mehr Paare haben.")


if auto_play:
    for k in range(n_rounds + 1):
        _render(k)
        time.sleep(min(0.8, 8.0 / max(n_rounds, 1)))
    step = n_rounds
else:
    _render(step)

counts = [len(s) for s in res.states]
if n_rounds > 0:
    st.plotly_chart(build_rounds(counts, [r.length for r in res.rounds]), width="stretch", key="rounds_chart")
st.caption("Quadrate sind Fahrzeuge, Kreise Aufträge; ohne Partner nur als Umriss; blasse Linien sind mögliche Paare, blaue gewählte. Grün: der Weg wählt diese Kante neu, rot gestrichelt: der Weg gibt diese gewählte Kante frei.")

st.markdown("---")

# --- Paare optimal - und die Kosten? -----------------------------------------------------------------------------------------------------

st.markdown("## 🎯 Paare optimal – und die Kosten?")
st.caption("Die Suche kennt die Kosten nicht - sie sieht nur, welche Kanten möglich sind (in Indexreihenfolge). **Mehrkosten** = Kosten des Ergebnisses geteilt durch die des Optimums (gleiche, nämlich größtmögliche Paarzahl), minus 1; das Optimum kommt aus der kleinen exakten Referenz der Greedy-Matching-Demo.")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Paare (Ergebnis)", f"{res.count} von {opt.count}", delta=f"{res.count - d['start_count']:+d} gegenüber dem Start" if res.count != d["start_count"] else "wie der Start", delta_color="normal" if res.count != d["start_count"] else "off",
          help="Nach den Verbesserungswegen hat das Matching immer die größtmögliche Paarzahl.")
diff_cost = res.cost - opt.cost
m2.metric("Kosten", f"{res.cost} min", delta=f"{diff_cost:+d} min gegenüber dem Optimum" if diff_cost else "so billig wie das Optimum", delta_color="inverse" if diff_cost else "off",
          help=f"Summe der Anfahrtszeiten. Optimum bei größtmöglicher Paarzahl: {opt.cost} min. Die Kosten des Starts: {d['start_cost']} min.")
m3.metric("Verbesserungswege", f"{d['rounds']}", delta=f"Weglänge Ø {_f(d['path_mean'])}, längster {d['path_max']}" if d["rounds"] else "keiner nötig", delta_color="off",
          help="Zahl der umgeklappten Wege; jeder gibt ein Paar dazu. Die Weglänge zählt Kanten.")
m4.metric("Durchsuchte Kanten", f"{d['scanned']}", delta=f"von {int(sc.feasible.sum())} Kanten", delta_color="off", help="Alle Suchen zusammen, einschließlich der letzten erfolglosen. Maschinenunabhängig gezählt, keine Sekunden.")

if code == "none":
    st.info("ℹ️ Keine einzige Kante ist möglich – die Reichweite ist zu klein. Es gibt nichts zuzuordnen.")
elif code == "optimal":
    st.success(f"✅ Größtmögliche Paarzahl ({res.count}) und auch die Kosten sind optimal: {res.cost} Minuten. Das ist die Ausnahme - die Verteilung unten zeigt, wie selten.")
else:
    more = f"{_pct(d['cost_gap_pct'])} mehr" if d["cost_gap_pct"] is not None else f"{d['cost_gap_abs']} Minuten mehr"
    why = (f"Es war kein Verbesserungsweg nötig: das Start-Matching hatte schon die größtmögliche Paarzahl, und Verbesserungswege sehen die Kosten nicht." if d["rounds"] == 0 and start != "empty"
           else f"Bei jedem Umklappen zählt nur, dass ein Paar dazukommt; welche gewählten Kanten dafür weichen, entscheidet die Suchreihenfolge, nicht der Preis.")
    st.warning(f"⚠️ Größtmögliche Paarzahl ({res.count}), aber die Kosten liegen bei {res.cost} statt {opt.cost} Minuten – **{more}**. {why}")

if net_key in C.FIXED_NETS:
    st.info("Feste Karte: es gibt nur diese eine Ziehung. Für die Verteilung über viele Karten eine zufällige Karte wählen.")
else:
    st.markdown(f"**Nicht nur diese eine Karte:** {len(C.DIST_SEEDS)} feste Karten mit denselben Einstellungen (Fahrzeuge {n}, Aufträge {m}, Reichweite {reach}, Ballung {ballung} %), getrennt vom Seed oben.")
    dist = _distribution(int(n), int(m), int(reach), int(ballung), start, search)
    if dist["n_valid"] == 0:
        st.info("ℹ️ Bei dieser Reichweite gibt es auf keiner der Karten ein mögliches Paar.")
    else:
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Größtmögliche Paarzahl", _share(dist["share_max_pairs"]), delta=f"schon der Start: {_share(dist['share_start_max'])}", delta_color="off",
                  help="Anteil der Karten, auf denen das Ergebnis so viele Paare hat wie das Optimum - hier immer alle. Im Delta der Anteil, bei dem schon das Start-Matching so viele hatte.")
        p2.metric("Verbesserungswege", _f(dist["rounds_mean"], 1), delta=f"Start: {_f(dist['start_pairs_mean'])} von {_f(dist['opt_pairs_mean'])} Paaren", delta_color="off",
                  help="Mittel der Wege über die Karten; im Delta die Paare des Starts gegenüber dem Optimum.")
        p3.metric("Mehrkosten (Median)", _pct(dist["cost_gap_median"]), delta=f"90 %-Quantil {_pct(dist['cost_gap_p90'])}", delta_color="off", help="Median der Mehrkosten über die Karten; im Delta das 90 %-Quantil.")
        p4.metric("Kosten optimal", _share(dist["share_optimal_cost"]), help="Anteil der Karten, auf denen auch die Kosten so niedrig sind wie beim Optimum.")
        if dist["share_optimal_cost"] >= 0.5:
            st.success(f"✅ Auf {_share(dist['share_optimal_cost'])} der {dist['n_seeds']} Karten sind auch die Kosten optimal - hier reichen Verbesserungswege.")
        else:
            st.warning(f"⚠️ Die Paarzahl ist auf {_share(dist['share_max_pairs'])} der {dist['n_seeds']} Karten größtmöglich, die Kosten liegen im Median {_pct(dist['cost_gap_median'])} über dem Optimum.")
        h1, h2 = st.columns(2)
        h1.plotly_chart(build_rounds_hist(dist["rounds_list"], current=n_rounds if code != "none" else None), width="stretch", key="rounds_hist")
        gaps = {C.START_LABELS[s]: _distribution(int(n), int(m), int(reach), int(ballung), s, search)["cost_gaps"] for s in C.START_LABELS}
        h2.plotly_chart(build_gap_compare({k: v for k, v in gaps.items() if v}, current=d["cost_gap_pct"]), width="stretch", key="gap_hist")
        h2.caption("Mehrkosten je Start (bei der gewählten Wegesuche): wer von Greedy startet, behält dessen billige Kanten und klappt nur wenige um.")
        st.markdown("**Aufwand und Kosten der sechs Kombinationen** (Mittel über die Karten, durchsuchte Kanten statt Sekunden):")
        eff = _effort(int(n), int(m), int(reach), int(ballung))
        st.table({"Start": [C.START_LABELS[r["start"]] for r in eff], "Suche": [C.SEARCH_LABELS[r["search"]].split(" (")[0] for r in eff],
                  "Wege": [_f(r["rounds_mean"]) for r in eff], "Weglänge Ø": [_f(r["path_mean"]) for r in eff], "längster Weg": [str(r["path_max"]) for r in eff],
                  "durchsuchte Kanten": [_f(r["scanned_mean"], 0) for r in eff], "Mehrkosten (Median)": [_pct(r["cost_gap_median"]) for r in eff]})
        st.caption(f"Das Netz hat im Mittel {_f(dist['edges_mean'], 0)} Kanten. Von Greedy aus sind es {_f(_distribution(int(n), int(m), int(reach), int(ballung), 'edge', 'bfs')['rounds_mean'])} Wege statt {_f(_distribution(int(n), int(m), int(reach), int(ballung), 'empty', 'bfs')['rounds_mean'])} vom leeren Start: "
                   "Greedy hat den größten Teil der Arbeit schon getan - und dabei billige Kanten gewählt, die die Suche nicht kennt und deshalb beim Umklappen meist stehen lässt.")

st.markdown("**Wie hängt es von der Reichweite ab?**")
if st.button("Reichweite von 10 bis 150 durchfahren (40 Karten je Wert, dauert wenige Sekunden)", key="sweep_start"):
    st.session_state["sweep_on"] = (int(n), int(m), int(ballung), start, search)
if st.session_state.get("sweep_on") == (int(n), int(m), int(ballung), start, search):
    with st.spinner(f"Rechne {len(C.REACH_SWEEP)} Reichweiten × {len(C.SWEEP_SEEDS)} Karten..."):
        sweep_rows = _reach_sweep(int(n), int(m), int(ballung), start, search)
    st.plotly_chart(build_reach_sweep(sweep_rows, current=int(reach) if net_key == "random" else None), width="stretch", key="sweep_chart")
    st.caption("Mittel über 40 feste Karten je Reichweite; Fahrzeuge, Aufträge, Ballung, Start und Wegesuche wie oben. Bei knapper Reichweite gibt es kaum etwas zu verbessern; bei mittlerer sind es die meisten Wege - "
               "hier liegt die Lücke, die Greedy hinterlässt. Ist alles erreichbar, braucht Greedy als Start keinen einzigen Weg mehr, und die Mehrkosten sind die von Greedy selbst.")

st.markdown("---")

# --- Vergleich -----------------------------------------------------------------------------------------------------------------------------

with st.expander("🔧 Wie wir das erreichen – Verfahren im Vergleich"):
    st.markdown("**Was jede Kombination für die Karte oben findet**")
    cmp_rows = _compare(params)
    st.table({"Start": [C.START_LABELS[r["start"]] for r in cmp_rows], "Suche": [C.SEARCH_LABELS[r["search"]].split(" (")[0] for r in cmp_rows], "Paare am Start": [r["start_count"] for r in cmp_rows],
              "Paare am Ende": [r["count"] for r in cmp_rows], "Wege": [r["rounds"] for r in cmp_rows], "Weglänge Ø": [_f(r["path_mean"]) for r in cmp_rows],
              "durchsuchte Kanten": [r["scanned"] for r in cmp_rows], "Kosten [min]": [r["cost"] for r in cmp_rows], "Mehrkosten": [_pct(r["cost_gap_pct"]) for r in cmp_rows]})
    st.caption("Bei jeder Kombination ist die Paarzahl am Ende dieselbe (die größtmögliche). Die Kosten des Optimums kommen aus einer exakten Referenz mit kürzesten augmentierenden Wegen und Potenzialen, die hier nur zum Messen dient; das Verfahren selbst ist Thema der Ungarischen Methode, eines späteren Stücks.")
    st.markdown("**Protokoll der Runden** (aktuelle Einstellung)")
    if n_rounds:
        st.dataframe({"Runde": list(range(1, n_rounds + 1)), "Weglänge": [r.length for r in res.rounds], "durchsuchte Kanten": [r.scanned for r in res.rounds], "Paare danach": [r.pairs_after for r in res.rounds],
                      "Weg": [_path_text(r.path) for r in res.rounds]}, hide_index=True, width="stretch")
    else:
        st.caption("Keine Runde: das Start-Matching hatte schon die größtmögliche Paarzahl.")

st.markdown("---")

# --- Aufwand -------------------------------------------------------------------------------------------------------------------------------

st.subheader("🔬 Aufwand: wie wächst die Suche mit der Karte?")
if st.button("Karten von 10 bis 320 Fahrzeugen durchrechnen (dauert einige Sekunden)", key="scaling_start"):
    st.session_state["scaling_on"] = True
if st.session_state.get("scaling_on"):
    with st.spinner("Rechne 6 Kartengrößen × 10 Karten × 6 Kombinationen..."):
        sc_rows = _scaling()
    c1, c2 = st.columns([3, 2])
    c1.plotly_chart(build_scaling(sc_rows), width="stretch", key="scaling_chart")
    c2.table({"Fahrzeuge = Aufträge": [r["n"] for r in sc_rows], "Reichweite": [r["reach"] for r in sc_rows], "Kanten": [_f(r["edges"], 0) for r in sc_rows],
              "Wege (Greedy A)": [_f(r[("edge", "bfs")]["rounds"]) for r in sc_rows], "durchsuchte Kanten": [_f(r[("edge", "bfs")]["scanned"], 0) for r in sc_rows]})
    st.caption("Fahrzeuge = Aufträge bei konstantem mittleren Grad (die Reichweite sinkt mit der Wurzel der Kartengröße), Mittel über 10 feste Karten. Gezählt werden **durchsuchte Kanten**, nicht Sekunden. "
               "Die Zahl der Wege wächst mit der Karte, und jede Suche kann fast alle Kanten anfassen: die Gesamtzahl wächst etwa mit dem **Quadrat** der Kartengröße (Zahl der Fahrzeuge mal Zahl der Kanten). "
               "Das ist der Ansatzpunkt von Hopcroft–Karp: viele kürzeste Wege je Suche statt einer.")

st.markdown("---")

# --- Grenzen -----------------------------------------------------------------------------------------------------------------------------

st.subheader("🚧 Wo die Annahmen enden")
st.markdown(
    """
| Annahme | Was passiert, wenn sie verletzt ist | Wer setzt an |
|---|---|---|
| **Nur die Paarzahl zählt** | Bei Reichweite 40 ist die Paarzahl auf allen 100 Karten größtmöglich, die Kosten liegen aber im Median 8 % (Start Greedy „Billigste Kante zuerst“) beziehungsweise 36 % (leerer Start) über dem Optimum. Bei allem erreichbar bleibt es bei 14 %: es gibt keinen Weg, der die Kosten anfasst. | **Ungarische Methode**: die Kosten entscheiden, welche gewählten Kanten weichen |
| **Ein Weg je Suche** | Bei konstantem mittleren Grad wächst die Zahl der durchsuchten Kanten von 20 auf 320 Fahrzeuge auf mehr als das 100-Fache: es gibt mehr Wege, und jede Suche kann fast alle Kanten anfassen. | **Hopcroft–Karp**: viele kürzeste Wege je Suche |
| **Es gibt zwei getrennte Seiten** | Fahrzeuge und Aufträge bilden zwei Gruppen. Sollen sich Fahrer untereinander paaren (Zweierteams), gibt es Zyklen ungerader Länge, in denen ein alternierender Weg im Kreis läuft und die Suche ihn nicht erkennt. | **Blossom**: allgemeine Graphen |
| **Zusagen dürfen zurückgenommen werden** | Umklappen gibt gewählte Zuordnungen wieder frei. Kommen Aufträge nacheinander und sind Fahrzeuge schon zugesagt, ist das nicht erlaubt. | **Online-Matching**: die Reihenfolge ist Teil des Problems |
| **Niemand hat Wünsche** | Fahrzeuge und Aufträge haben keine Vorlieben; sobald sie welche haben, ist nicht mehr die Paarzahl das Ziel, sondern dass niemand abwandern möchte. | **Gale–Shapley**: stabile Paarungen |
"""
)
st.caption("Die Nachbarn der Matching-Linie (noch nicht gebaut): Hopcroft–Karp, Ungarische Methode, Auktionsalgorithmus, Blossom, Gewichteter Blossom, Gale–Shapley, Stabile Mitbewohner und Online-Matching. Bereits gebaut: die Wurzel, die Greedy-Matching-Demo.")

st.markdown("---")

with st.expander("📐 Mathematische Formulierung"):
    st.markdown(
        r"""
**Modell.** Bipartiter Graph $G=(V\cup O,E)$ mit Fahrzeugen $V$, Aufträgen $O$ und möglichen Paaren $E$. Ein Matching $M\subseteq E$ enthält jede Ecke höchstens einmal. Ecken ohne Kante in $M$ heißen *frei*.

**Verbesserungsweg.** Ein Weg $P=(v_0,o_0,v_1,o_1,\dots,v_k,o_k)$ mit $v_0$ frei, $o_k$ frei, den Kanten $(v_i,o_i)\notin M$ und $(o_i,v_{i+1})\in M$. Er hat $2k+1$ Kanten, davon $k+1$ nicht in $M$. Die symmetrische Differenz $M\triangle P$ ist wieder ein Matching mit $|M|+1$ Kanten.

**Satz von Berge.** $M$ ist größtmöglich $\iff$ es gibt keinen Verbesserungsweg. *Beweisskizze ($\Leftarrow$):* Ist $M^*$ größer als $M$, besteht $M\triangle M^*$ aus Wegen und geraden Kreisen mit abwechselnden Kanten; weil $M^*$ mehr Kanten hat, gibt es einen Weg mit einer $M^*$-Kante mehr - einen Verbesserungsweg für $M$.

**Verfahren.** Wiederhole: suche einen Verbesserungsweg und klappe ihn um, bis keiner mehr existiert. Die **Breitensuche** startet von allen freien Fahrzeugen gleichzeitig (Schicht 0), geht über nicht gewählte Kanten zu Aufträgen und über gewählte zurück und findet einen *kürzesten* Weg. Die **Tiefensuche** (Kuhn) probiert die freien Fahrzeuge der Reihe nach, mit einem je Start zurückgesetzten „besucht“-Feld für Aufträge; scheitert sie für ein Fahrzeug, scheitert sie für dieses Fahrzeug auch später, deshalb genügt ein Durchgang.
Je Suche werden höchstens $|E|$ Kanten durchsucht, es gibt höchstens $\min(|V|,|O|)$ Wege: **Laufzeit $O(|V|\cdot|E|)$**.

**Beweis der Erschöpfung (König).** Sei $Z$ die Menge der Ecken, die von freien Fahrzeugen aus über alternierende Wege erreichbar sind. Nach der erfolglosen Suche ist $C=(V\setminus Z)\cup(O\cap Z)$ eine **Knotenüberdeckung**: jede Kante in $E$ hat mindestens eine Ecke in $C$, und $|C|=|M|$. Da jede Überdeckung mindestens so viele Ecken braucht wie jedes Matching Kanten hat, ist $M$ größtmöglich.

**Kosten.** Die Suche betrachtet die Nachbarn in Indexreihenfolge und kennt $c_{ij}$ nicht. Sie garantiert $|M|=\nu(G)$, aber nichts über $c(M)$; unter allen größtmöglichen Matchings minimiert die Ungarische Methode die Kosten.

Implementiert in `ap_scenario.py` (Karten, eigener Zufallsgenerator), `ap_greedy.py` (Greedy-Regeln und exakte Messlatte aus der Greedy-Matching-Demo), `ap_algorithm.py` (Verbesserungswege, Beweis), `ap_evaluation.py` (Kennzahlen, Verteilung, Aufwand).
        """
    )

st.markdown("---")

st.caption(
    "Diese Demo ist Teil des Portfolios von [Sebastian Hanisch](https://sebastianhanisch.net) – "
    "Operations Research und Machine Learning. Interesse an einer maßgeschneiderten Lösung für "
    "Ihr Unternehmen? [Kontakt aufnehmen](https://sebastianhanisch.net/kontakt.html)"
)
