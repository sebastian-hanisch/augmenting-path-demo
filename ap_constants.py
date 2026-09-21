"""Konstanten, Regler-Grenzen, Presets und feste Seed-Mengen der Demo "Augmentierende Pfade"."""

# --- Regler (wie in der Greedy-Matching-Demo) ----------------------------------------------------------------------------------
N_MIN, N_MAX, DEFAULT_N = 3, 40, 20          # Fahrzeuge
M_MIN, M_MAX, DEFAULT_M = 3, 40, 20          # Aufträge
REACH_MIN, REACH_MAX, DEFAULT_REACH = 10, 150, 40   # Reichweite in Minuten; ab 142 ist auf der 100x100-Karte alles erreichbar
BALLUNG_MIN, BALLUNG_MAX, DEFAULT_BALLUNG = 0, 100, 0   # ganze Prozent, Schritt 25
DEFAULT_SEED = 165
SEED_MAX = 2_000_000_000

NETS = {"random": "Zufällige Karte", "steal": "Billigste Kante klaut (2×2)", "p4": "Pfad aus vier Punkten", "paths": "Drei Pfade hintereinander", "chain": "Lange Kette (13 Kanten)"}
DEFAULT_NET = "random"
FIXED_NETS = ("steal", "p4", "paths", "chain")

START_LABELS = {"empty": "Leer", "edge": "Greedy: billigste Kante zuerst", "order": "Greedy: Auftrag für Auftrag"}
DEFAULT_START = "edge"
SEARCH_LABELS = {"bfs": "Breitensuche (kürzester Weg)", "dfs": "Tiefensuche (Kuhn)"}
DEFAULT_SEARCH = "bfs"

# --- feste Seed-Mengen (dieselben wie in der Greedy-Matching-Demo; unabhängig vom Nutzer-Seed) --------------------------------------
DIST_SEEDS = tuple(range(100000, 100100))
SWEEP_SEEDS = DIST_SEEDS[:40]
REACH_SWEEP = (10, 15, 20, 25, 30, 40, 50, 60, 80, 100, 120, 150)
SCALE_NS = (10, 20, 40, 80, 160, 320)      # Aufwand-Experiment: Fahrzeuge = Aufträge, mittlerer Grad konstant (Reichweite ~ 1/sqrt(n))
SCALE_SEEDS = DIST_SEEDS[:10]
SCALE_REACH_AT_20 = 40

COLORS = {"matched": "#1f77b4", "add": "#2ca02c", "drop": "#d62728", "common": "#8c8c8c", "vehicle": "#111111", "order": "#ff7f0e", "cover": "#9467bd", "optimal": "#d62728"}

# --- Presets ------------------------------------------------------------------------------------------------------------------
_BASE = dict(net="random", start=DEFAULT_START, search=DEFAULT_SEARCH, n=DEFAULT_N, m=DEFAULT_M, reach=DEFAULT_REACH, ballung=DEFAULT_BALLUNG, seed=DEFAULT_SEED)
PRESETS = {
    "⚖️ Nichts zu verbessern": {**_BASE, "net": "steal"},
    "🔗 Pfad aus vier Punkten": {**_BASE, "net": "p4"},
    "⛓️ Lange Kette": {**_BASE, "net": "chain"},
    "🗺️ Mittlere Reichweite": {**_BASE, "seed": 165},
    "🕳️ Von leer starten": {**_BASE, "start": "empty", "seed": 165},
    "🌐 Alles erreichbar": {**_BASE, "reach": 150, "seed": 141},
    "📡 Knappe Reichweite": {**_BASE, "reach": 10, "seed": 3},
    "🌲 Tiefensuche": {**_BASE, "search": "dfs", "seed": 165},
}
# Jede Zahl in diesen Texten ist in tests/test_claims.py über die 100 festen Karten (DIST_SEEDS) belegt
PRESET_HELP = {
    "⚖️ Nichts zu verbessern": "Greedy hat hier schon die größtmögliche Paarzahl (2): es gibt keinen Verbesserungsweg, der Algorithmus tut nichts - und die Kosten bleiben bei 18 statt 10 Minuten. Verbesserungswege zählen Paare, keine Kosten.",
    "🔗 Pfad aus vier Punkten": "Greedy hat 1 Paar. Ein Verbesserungsweg aus 3 Kanten gibt die billige Mittelkante wieder frei und wählt die beiden äußeren: 2 Paare, das Optimum.",
    "⛓️ Lange Kette": "Sieben Fahrzeuge und sieben Aufträge in einer Kette: Greedy findet 6 Paare, der einzige Verbesserungsweg läuft durch die ganze Kette (13 Kanten) und gibt alle 6 gewählten Paare frei.",
    "🗺️ Mittlere Reichweite": "20 Fahrzeuge, 20 Aufträge, Reichweite 40, Start von Greedy: im Mittel über 100 Karten genügen 2,7 Verbesserungswege (Greedy hat 16,7 von 19,5 Paaren), danach ist die Paarzahl auf jeder Karte größtmöglich. Die Kosten liegen im Median 8 % über dem Optimum.",
    "🕳️ Von leer starten": "Dieselbe Karte ohne Greedy als Start: 19,5 Verbesserungswege statt 2,7, und die Kosten liegen im Median 36 % statt 8 % über dem Optimum - die Suche kennt die Kosten nicht und nimmt das erste mögliche Paar in Indexreihenfolge.",
    "🌐 Alles erreichbar": "Greedy bedient alle 20 Aufträge schon: es gibt keinen Verbesserungsweg, die Kosten bleiben im Median 14 % über dem Optimum. Vom leeren Start aus sind es im Median über 150 % - Verbesserungswege reparieren die Paarzahl, nicht das Geld.",
    "📡 Knappe Reichweite": "Nur wenige Paare sind möglich (Reichweite 10): auf 80 von 100 Karten hat Greedy schon die größtmögliche Paarzahl, im Mittel werden 0,2 Verbesserungswege gebraucht - und auf 95 von 100 Karten sind auch die Kosten optimal.",
    "🌲 Tiefensuche": "Dieselbe Karte mit Tiefensuche (Kuhn): dieselbe Paarzahl, aber die Wege sind im Mittel 15,6 statt 4,3 Kanten lang und die Kosten liegen im Median 27 % statt 8 % über dem Optimum - lange Wege klappen viele gewählte Paare um.",
}
