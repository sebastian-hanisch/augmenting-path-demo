# Augmentierende Pfade – eine Zuordnung darf wieder freigegeben werden – Streamlit-Demo

Zweites Stück der **Matching-Linie** der "Konzepte"-Reihe für die Website "Sebastian Hanisch – Operations Research und Machine Learning", Fortsetzung der [Greedy-Matching-Demo](https://github.com/sebastian-hanisch/greedy-matching-demo):
anders als die Fall-Demos im Portfolio (ein Anwendungsfall, mehrere Verfahren im Vergleich) zeigt diese Demo **ein** Verfahren – **augmentierende Pfade** (Verbesserungswege im bipartiten Matching) – an einem wachsenden Beispiel.
Greedy legt Zuordnungen fest und nimmt sie nie zurück und verliert deshalb Paare. Ein **Verbesserungsweg** beginnt an einem freien Fahrzeug, geht abwechselnd über nicht gewählte und gewählte Kanten und endet an einem freien Auftrag;
klappt man ihn um, ist ein Paar **mehr** entstanden. Gibt es keinen mehr, ist die Paarzahl größtmöglich (Berge). Der Haken: die Suche **zählt Paare, nicht Kosten**.

**Einordnung in die Reihe (die Kanten des Graphen):** dieses Stück behebt die Schwäche der Wurzel (eine gewählte Zuordnung bleibt). Seine eigenen Schwächen sind die Ansatzpunkte der nächsten: die Kosten entscheiden nicht, welche Kanten weichen (**Ungarische Methode**),
jede Suche findet nur einen Weg und kann fast alle Kanten anfassen (**Hopcroft–Karp**), es gibt nur zwei getrennte Seiten (**Blossom**). Bisher gebaut: die Wurzel und dieses Stück.
```
greedy-matching-demo (Wurzel: eine gewählte Zuordnung bleibt)                     [gebaut]
  ├─ augmenting-path-demo (Verbesserungswege: Paare optimal, Kosten blind)        [dieses Stück]
  │    ├─ hopcroft-karp-demo (viele kürzeste Wege je Phase)                       [gebaut]
  │    ├─ hungarian-demo (Ungarische Methode: Paare zuerst, dann Kosten)           [gebaut]
  │    └─ blossom-demo (allgemeine Graphen: ungerade Kreise, Kontraktion)          [gebaut]
  │        └─ weighted-blossom-demo (Ungarisch + Blossom, Konvergenz)              [gebaut]
  ├─ Gale–Shapley → Stabile Mitbewohner, Krankenhaus-Zulassung, Top Trading Cycles, Nierentausch [gebaut]
  └─ online-matching-demo (Aufträge kommen nacheinander)                          [gebaut]
```

## Ergebnis (Zahlen aus den Tests)

Jede hier genannte Zahl ist in `tests/test_claims.py` über die 100 festen Karten (Seeds 100000–100099) belegt; sie sind dieselben wie in der Greedy-Matching-Demo. Standard: 20 Fahrzeuge, 20 Aufträge, Reichweite 40, Start Greedy „Billigste Kante zuerst“, Breitensuche. Die Greedy-Zahlen der Wurzel werden hier neu gemessen, nicht zitiert.

| Frage | Ergebnis |
|---|---|
| Wird die Paarzahl größtmöglich? | ✅ Ja, auf allen 100 Karten bei jeder Reichweite der Sweep-Reihe, mit jedem der drei Starts (leer, Greedy A, Greedy B) und beiden Suchen; unabhängig gegen scipy und networkx geprüft, dazu der Beweis (Knotenüberdeckung mit genau so vielen Ecken wie Paaren). Bei Reichweite 40 genügen von Greedy aus im Mittel 2,7 Verbesserungswege (Greedy hat 16,7 von 19,5 Paaren, auf 99 von 100 Karten fehlen Paare). |
| Und die Kosten? | ❌ Die Suche kennt sie nicht: die Kosten liegen im Median 8 % über dem Optimum (Start Greedy A), 36 % vom leeren Start aus; nur auf 1 von 100 Karten sind sie optimal. Vom Greedy-Start aus liegen sie bei jeder getesteten Reichweite ab 20 niedriger als vom leeren Start – Greedys billige Kanten bleiben meist stehen. |
| Alles erreichbar (Reichweite 150) | ⚠️ Greedy bedient schon alle 20 Aufträge: es gibt keinen Verbesserungsweg, die Kosten bleiben im Median 14 % über dem Optimum (vom leeren Start über 150 %). Verbesserungswege reparieren die Paarzahl, nicht das Geld. |
| Sehr knappe Reichweite (10 Minuten) | ✅ Auf 80 von 100 Karten hat Greedy schon die größtmögliche Paarzahl, im Mittel sind 0,2 Verbesserungswege nötig, und auf 95 von 100 Karten sind auch die Kosten optimal. |
| Breitensuche gegen Tiefensuche | ⚠️ Beide finden dieselbe Paarzahl in derselben Zahl Wegen, aber die Wege der Tiefensuche (Kuhn) sind im Mittel 15,6 statt 4,3 Kanten lang, und die Kosten liegen im Median 27 % statt 8 % über dem Optimum: lange Wege klappen viele gewählte Paare um. |
| Lange Kette | ✅ Sieben Fahrzeuge und sieben Aufträge in einer Kette: Greedy findet 6 Paare, ein einziger Verbesserungsweg durch die ganze Kette (13 Kanten) gibt alle 6 gewählten Paare frei. |
| Nichts zu verbessern (2 × 2) | ❌ Greedy hat schon die größtmögliche Paarzahl: kein Weg, die Kosten bleiben bei 18 statt 10 Minuten. |
| Wie wächst der Aufwand? | ⚠️ Bei konstantem mittleren Grad wächst die Zahl der durchsuchten Kanten von 20 auf 320 Fahrzeuge auf mehr als das 100-Fache, etwa mit dem Quadrat der Kartengröße (O(V·E)). Gezählt werden durchsuchte Kanten, nie Sekunden. |

## Was nicht funktioniert hat / Vorab-Hypothesen

Vor dem Schreiben der Texte wurde gemessen (400 Karten je Zelle); zwei Vermutungen aus der Planung stimmten nur teilweise:

- **„Die Tiefensuche durchsucht meist weniger Kanten als die Breitensuche.“** Nur vom Greedy-Start aus; vom leeren Start durchsucht sie bei Reichweite 40 mehr als das Doppelte.
- **„Jede Runde ist ein volles O(E).“** Bei den Standardgrößen nicht: ein ganzer Lauf vom Greedy-Start durchsucht bei 20 Fahrzeugen im Mittel etwa so viele Kanten, wie das Netz hat. Erst mit wachsender Karte zeigt sich das quadratische Wachstum (Aufwand-Experiment); der Ansatzpunkt für Hopcroft–Karp ist die Größe der Karte, nicht die Standarddemo.
- Bestätigt wurde: Verbesserungswege tun nach Greedy nichts mehr, wenn alles erreichbar ist (keine Runde), und der Start von Greedy hält die Kosten niedriger als der leere Start.

## Was die Demo zeigt

- **Verbesserungswege in Aktion:** Schritt-Slider und ▶️ über die Runden: links der Zustand mit dem Weg der nächsten Runde (grün = wird gewählt, rot gestrichelt = wird freigegeben), rechts der Zustand danach; am Ende der **Beweis** – die Knotenüberdeckung, deren Ecken jede mögliche Kante berühren und deren Größe der Paarzahl entspricht.
- **Paare optimal – und die Kosten?** Ergebnis gegen die exakte Messlatte, Verteilung über 100 feste Karten (Anteile, Median, Histogramme mit der Marke „Ihre Ziehung“ für alle drei Starts), Tabelle der sechs Kombinationen (Wege, Weglängen, durchsuchte Kanten, Mehrkosten), Sweep über die Reichweite.
- **Aufwand:** wie wächst die Zahl der durchsuchten Kanten mit der Karte (10 bis 320 Fahrzeuge bei konstantem mittleren Grad).
- **Feste Lehrbuchkarten** (2 × 2, Pfad aus vier Punkten, lange Kette) und zufällige Karten; **Wo die Annahmen enden:** welches spätere Stück an welcher Schwäche ansetzt.

Das **Optimum** kommt aus der kleinen exakten Referenz der Greedy-Matching-Demo (kürzeste augmentierende Wege mit Potenzialen auf einer ganzzahligen Matrix), die hier nur zum Messen dient; das Verfahren selbst ist Thema der Ungarischen Methode, eines späteren Stücks.

## Modell und Verfahren

- **Karte:** wie in der Wurzel – ganzzahlige Koordinaten, aufgerundete Entfernung als Kosten, Reichweite, Ballung, eigener Zufallsgenerator (SplitMix64 auf Python-Ints statt `numpy.random`), damit jede Zahl auf Windows und Linux dieselbe ist.
- **Verbesserungsweg:** $P=(v_0,o_0,v_1,\dots,v_k,o_k)$ mit freiem $v_0$ und freiem $o_k$, den Kanten $(v_i,o_i)\notin M$ und $(o_i,v_{i+1})\in M$. Umklappen ergibt $|M|+1$. **Satz von Berge:** $M$ ist größtmöglich ⇔ es gibt keinen Verbesserungsweg.
- **Breitensuche:** alle freien Fahrzeuge gleichzeitig als Schicht 0, kürzester Weg. **Tiefensuche (Kuhn):** freie Fahrzeuge der Reihe nach, je Start ein zurückgesetztes „besucht“-Feld für Aufträge; scheitert ein Fahrzeug, scheitert es auch später – ein Durchgang genügt.
- **Nachbarn in Indexreihenfolge:** die Suche kennt die Kosten nicht; das ist die Kostenblindheit, die die Demo misst.
- **Beweis (König):** die von freien Fahrzeugen alternierend erreichbaren Ecken $Z$ liefern die Überdeckung $(V\setminus Z)\cup(O\cap Z)$ mit genau $|M|$ Ecken.
- **Laufzeit:** $O(|V|\cdot|E|)$; gemessen als durchsuchte Kanten.

## Dateien

| Datei | Inhalt |
|---|---|
| `app.py` | Streamlit-Oberfläche |
| `ap_constants.py` | Regler-Grenzen, Presets und Hilfetexte, feste Seed-Mengen |
| `ap_presets.py` | Permalink, Preset- und Zufalls-Seed-Logik (Standardmuster des Portfolios) |
| `ap_scenario.py` | Karten, eigener Zufallsgenerator, feste Lehrbuchkarten (aus der Greedy-Matching-Demo kopiert, dazu die lange Kette) |
| `ap_greedy.py` | Greedy-Regeln und exakte Messlatte (aus der Greedy-Matching-Demo kopiert, ohne Import) |
| `ap_algorithm.py` | Verbesserungswege: Breiten- und Tiefensuche, Umklappen, Beweis |
| `ap_evaluation.py` | Einordnung, Verdict, Verteilung über viele Karten, Aufwand |
| `ap_visualization.py` | Plotly-Abbildungen (Achsen gesperrt für Touch-Geräte; Bögen bei Punkten auf einer Geraden) |
| `tests/` | Algorithmus (Handfälle, Invarianten je Runde, scipy und networkx als Gegenprobe, kürzeste Wege und Beweis unabhängig nachgeprüft), Auswertung, Presets, belegte Zahlen, AppTest-Rauchtests |

Die Kopien der Wurzel werden durch einen Test bewacht: dieselben Karten und Regeln müssen die Zahlen der Greedy-Matching-Demo reproduzieren. Alle Daten sind synthetisch; die Laufzeit braucht nur numpy, pandas, plotly und streamlit (scipy und networkx sind reine Testorakel).

## Lokal starten

```bash
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\streamlit run app.py
```

## Tests ausführen

```bash
venv\Scripts\pip install -r requirements-dev.txt
venv\Scripts\python -m pytest tests -v
```

Die Logik rechnet ausschließlich mit ganzen Zahlen; die im Text genannten Anteile und Mediane sind deshalb auf jeder Plattform identisch.
Die CI (`.github/workflows/tests.yml`) läuft auf Ubuntu mit Python 3.12, bei jedem Push und wöchentlich mit den jeweils neuesten Bibliotheksversionen.
