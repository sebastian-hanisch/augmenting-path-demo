"""Verbesserungswege: Handfälle, Invarianten je Runde, scipy und networkx als unabhängige Prüfer, Beweis der Erschöpfung (Knotenüberdeckung),
dazu die aus der Greedy-Matching-Demo kopierten Bausteine (Zufallsgenerator, feste Karten, Greedy-Regeln, exakte Messlatte).

Verglichen werden immer nur Paarzahlen und Kosten - nie Kantenmengen des Optimums."""

import itertools

import networkx as nx
import numpy as np
import pytest
from scipy.optimize import linear_sum_assignment
from scipy.sparse import csr_matrix
from scipy.sparse.csgraph import maximum_bipartite_matching

from ap_algorithm import SEARCH_BFS, SEARCH_DFS, SEARCHES, STARTS, augment, edge_count, has_augmenting_path, start_pairs
from ap_greedy import RULES, is_maximal, optimum, run_rule
from ap_scenario import SplitMix64, from_points, generate, long_chain, p4_chain, steal_2x2, travel_cost


# --- kopierte Bausteine der Wurzel (Wache gegen einen fehlerhaften Kopiervorgang) ------------------------------------------------------------------

def test_splitmix64_reference_vector():
    rng = SplitMix64(0)
    assert [rng.next() for _ in range(2)] == [0xE220A8397B1DCDAF, 0x6E789E6AA1B965F4]


def test_travel_cost_and_fixed_maps_of_the_root():
    assert travel_cost(3, 4) == (5, 25) and travel_cost(1, 1) == (2, 2) and travel_cost(100, 100) == (142, 20000)
    sc = steal_2x2()
    assert sc.cost.tolist() == [[4, 5], [5, 14]]
    for rule in RULES:
        g = run_rule(sc, rule)
        assert (g.count, g.cost) == (2, 18)
    assert (optimum(sc).count, optimum(sc).cost) == (2, 10)
    assert all(run_rule(p4_chain(1), r).count == 1 for r in RULES) and optimum(p4_chain(1)).count == 2


def test_the_root_numbers_are_reproduced_on_the_shared_maps():
    """Wache gegen einen fehlerhaften Kopiervorgang: dieselben Karten und Regeln geben die Zahlen der Greedy-Matching-Demo (Preset 'Mittlere Reichweite', Seed 2)."""
    sc = generate(20, 20, 40, 0, 2)
    g, o = run_rule(sc, "edge"), optimum(sc)
    assert (g.count, g.cost, o.count, o.cost) == (17, 232, 20, 316)


def test_long_chain_geometry():
    sc = long_chain(6)
    assert (sc.n, sc.m, edge_count(sc)) == (7, 7, 13) and sorted({int(c) for c in sc.cost[sc.feasible]}) == [2, 10]
    for rule in RULES:
        assert run_rule(sc, rule).count == 6
    assert optimum(sc).count == 7


# --- Handfälle -----------------------------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("search", SEARCHES)
def test_p4_from_greedy_needs_one_path_of_three_edges(search):
    sc = p4_chain(1)
    res = augment(sc, start_pairs(sc, "edge"), search)
    assert res.start == ((1, 0),) and res.pairs == ((0, 0), (1, 1)) and res.cost == 20
    (rnd,) = res.rounds
    assert rnd.path == ((0, 0, "add"), (1, 0, "drop"), (1, 1, "add")) and rnd.length == 3 and rnd.pairs_after == 2
    assert res.states == (((1, 0),), ((0, 0), (1, 1))) and res.final_scanned == 0


def test_p4_bfs_scans_three_edges():
    sc = p4_chain(1)
    res = augment(sc, start_pairs(sc, "edge"), SEARCH_BFS)
    assert res.rounds[0].scanned == 3 and res.scanned_total == 3


@pytest.mark.parametrize("search", SEARCHES)
def test_long_chain_one_path_through_everything(search):
    sc = long_chain(6)
    res = augment(sc, start_pairs(sc, "edge"), search)
    assert len(res.rounds) == 1 and res.rounds[0].length == 13 and res.count == 7 and res.cost == 70


def test_long_chain_from_empty_takes_seven_short_rounds():
    res = augment(long_chain(6), (), SEARCH_BFS)
    assert [r.length for r in res.rounds] == [1] * 7 and res.count == 7


@pytest.mark.parametrize("search", SEARCHES)
def test_nothing_to_improve_when_greedy_is_maximum(search):
    sc = steal_2x2()
    res = augment(sc, start_pairs(sc, "edge"), search)
    assert res.rounds == () and res.pairs == res.start and res.cost == 18 and len(res.states) == 1     # 18 statt 10: Verbesserungswege sehen die Kosten nicht


def test_costs_are_not_repaired():
    """Auf 2x2 bleibt es bei 18 Minuten, obwohl das Optimum 10 kostet; vom leeren Start entscheidet die Indexreihenfolge."""
    sc = steal_2x2()
    empty = augment(sc, (), SEARCH_BFS)
    assert empty.count == 2 and empty.cost == 4 + 14      # F1 nimmt A1 (der erste Auftrag in Reichweite), F2 den Rest: dieselben 18


def test_no_feasible_edge():
    sc = from_points([(0, 0)], [(90, 90)], reach=10)
    for start in STARTS:
        res = augment(sc, start_pairs(sc, start), SEARCH_BFS)
        assert res.count == 0 and res.rounds == () and res.cost == 0


def test_invalid_start_pairs_are_rejected():
    sc = p4_chain(1)
    with pytest.raises(AssertionError):
        augment(sc, ((0, 0), (0, 1)), SEARCH_BFS)


# --- Invarianten auf Zufallskarten -------------------------------------------------------------------------------------------------------

def _cases(n_cases=120):
    for s in range(n_cases):
        n, m = 3 + s % 9, 3 + (s * 5) % 9
        yield generate(n, m, 15 + (s * 13) % 130, (s * 25) % 101, s)


def _valid(sc, pairs):
    vs, os_ = [i for i, _ in pairs], [j for _, j in pairs]
    return len(set(vs)) == len(vs) and len(set(os_)) == len(os_) and all(sc.feasible[i, j] for i, j in pairs)


def _independent_no_path(sc, pairs):
    """Unabhängige Prüfung ohne den Code der Demo: rekursives Kuhn von jedem freien Fahrzeug aus."""
    match_o = {j: i for i, j in pairs}
    matched_v = {i for i, _ in pairs}

    def try_(i, seen):
        for j in range(sc.m):
            if sc.feasible[i, j] and j not in seen:
                seen.add(j)
                if j not in match_o or try_(match_o[j], seen):
                    return True
        return False

    return not any(try_(i, set()) for i in range(sc.n) if i not in matched_v)


def test_every_round_adds_exactly_one_pair_and_keeps_a_matching():
    for sc in _cases(60):
        for start in STARTS:
            for search in SEARCHES:
                res = augment(sc, start_pairs(sc, start), search)
                counts = [len(s) for s in res.states]
                assert counts == list(range(counts[0], counts[0] + len(res.rounds) + 1))
                assert all(_valid(sc, s) for s in res.states) and res.states[-1] == res.pairs
                for k, rnd in enumerate(res.rounds):
                    kinds = [kind for _i, _j, kind in rnd.path]
                    assert kinds == ["add", "drop"] * (len(kinds) // 2) + ["add"] and rnd.length == len(kinds) == 2 * kinds.count("drop") + 1
                    state = set(res.states[k])
                    free_v = {i for i in range(sc.n)} - {i for i, _ in state}
                    free_o = {j for j in range(sc.m)} - {j for _, j in state}
                    adds = [(i, j) for i, j, kind in rnd.path if kind == "add"]
                    drops = [(i, j) for i, j, kind in rnd.path if kind == "drop"]
                    assert adds[0][0] in free_v and adds[-1][1] in free_o and all(p in state for p in drops) and not any(p in state for p in adds)
                    assert set(res.states[k + 1]) == (state - set(drops)) | set(adds)


def test_pair_count_equals_the_maximum_from_every_start_with_both_searches():
    for sc in _cases(200):
        ref = int((maximum_bipartite_matching(csr_matrix(sc.feasible.astype(np.int8)), perm_type="column") >= 0).sum())
        assert optimum(sc).count == ref
        for start in STARTS:
            for search in SEARCHES:
                assert augment(sc, start_pairs(sc, start), search, record=False).count == ref


def test_pair_count_matches_networkx_hopcroft_karp():
    for sc in _cases(60):
        g = nx.Graph()
        top = [("v", i) for i in range(sc.n)]
        g.add_nodes_from(top, bipartite=0)
        g.add_nodes_from([("o", j) for j in range(sc.m)], bipartite=1)
        g.add_edges_from((("v", i), ("o", j)) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j])
        ref = len(nx.bipartite.hopcroft_karp_matching(g, top_nodes=top)) // 2
        assert augment(sc, (), SEARCH_BFS, record=False).count == ref


def test_from_greedy_needs_exactly_opt_minus_greedy_rounds():
    for sc in _cases(200):
        o = optimum(sc)
        for rule in RULES:
            g = run_rule(sc, rule)
            for search in SEARCHES:
                assert len(augment(sc, g.pairs, search, record=False).rounds) == o.count - g.count


def test_from_empty_needs_one_round_per_pair():
    for sc in _cases(80):
        res = augment(sc, (), SEARCH_BFS, record=False)
        assert len(res.rounds) == res.count


def test_after_the_last_round_there_is_no_improving_path():
    """Unabhängige Nachprüfung (Berge): nach dem Ende gibt es keinen Verbesserungsweg mehr; vorher (Greedy unter dem Maximum) gibt es einen."""
    for sc in _cases(120):
        o = optimum(sc)
        for start in STARTS:
            for search in SEARCHES:
                res = augment(sc, start_pairs(sc, start), search, record=False)
                assert _independent_no_path(sc, res.pairs) and not has_augmenting_path(sc, res.pairs)
        g = run_rule(sc, "edge")
        assert has_augmenting_path(sc, g.pairs) == (g.count < o.count)


def test_the_cover_is_a_vertex_cover_of_the_size_of_the_matching():
    """König: die Überdeckung aus der erfolglosen Suche berührt jede mögliche Kante und hat genau so viele Ecken wie Paare - der Beweis der Erschöpfung."""
    for sc in _cases(150):
        for start in STARTS:
            for search in SEARCHES:
                res = augment(sc, start_pairs(sc, start), search, record=False)
                assert all(i in res.cover_v or j in res.cover_o for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j])
                assert len(res.cover_v) + len(res.cover_o) == res.count


def _shortest_path_length(sc, pairs):
    """Länge des kürzesten Verbesserungswegs über networkx (Suche im Restgraphen), unabhängig vom Code der Demo."""
    match_v = {i: j for i, j in pairs}
    match_o = {j: i for i, j in pairs}
    g = nx.DiGraph()
    g.add_nodes_from([("v", i) for i in range(sc.n)] + [("o", j) for j in range(sc.m)])
    for i in range(sc.n):
        for j in range(sc.m):
            if sc.feasible[i, j]:
                if match_v.get(i) == j:
                    g.add_edge(("o", j), ("v", i))
                else:
                    g.add_edge(("v", i), ("o", j))
    sources = [("v", i) for i in range(sc.n) if i not in match_v]
    if not sources:
        return None
    best = None
    dist = nx.multi_source_dijkstra_path_length(g, sources)
    for j in range(sc.m):
        if j not in match_o and ("o", j) in dist:
            best = dist[("o", j)] if best is None else min(best, dist[("o", j)])
    return best


def test_breadth_first_paths_are_shortest_paths():
    for sc in _cases(120):
        for start in STARTS:
            res = augment(sc, start_pairs(sc, start), SEARCH_BFS)
            for k, rnd in enumerate(res.rounds):
                assert rnd.length == _shortest_path_length(sc, res.states[k])


def test_depth_first_paths_are_never_shorter_than_breadth_first_paths_in_the_first_round():
    for sc in _cases(120):
        bfs, dfs = augment(sc, start_pairs(sc, "edge"), SEARCH_BFS), augment(sc, start_pairs(sc, "edge"), SEARCH_DFS)
        if bfs.rounds:
            assert dfs.rounds[0].length >= bfs.rounds[0].length


def test_scanned_edges_are_deterministic_and_bounded():
    for sc in _cases(60):
        e = edge_count(sc)
        a, b = augment(sc, start_pairs(sc, "edge"), SEARCH_BFS), augment(sc, start_pairs(sc, "edge"), SEARCH_BFS)
        assert a.scanned_total == b.scanned_total and all(r.scanned <= e for r in a.rounds) and a.final_scanned <= e


# --- exakte Messlatte (kopiert) ---------------------------------------------------------------------------------------------------------------

def test_optimum_matches_scipy_and_the_half_guarantee_holds():
    for sc in _cases(150):
        big = int(sc.cost.max()) * min(sc.n, sc.m) + 1
        rows, cols = linear_sum_assignment(np.where(sc.feasible, big - sc.cost, 0), maximize=True)
        pairs = [(i, j) for i, j in zip(rows, cols) if sc.feasible[i, j]]
        o = optimum(sc)
        assert (o.count, o.cost) == (len(pairs), int(sum(sc.cost[i, j] for i, j in pairs)))
        for rule in RULES:
            g = run_rule(sc, rule)
            assert is_maximal(sc, g.pairs) and 2 * g.count >= o.count


def _brute_force(sc):
    best = (0, 0)

    def rec(j, used, count, cost):
        nonlocal best
        if j == sc.m:
            best = max(best, (count, -cost))
            return
        rec(j + 1, used, count, cost)
        for i in range(sc.n):
            if i not in used and sc.feasible[i, j]:
                rec(j + 1, used | {i}, count + 1, cost + int(sc.cost[i, j]))

    rec(0, frozenset(), 0, 0)
    return best


def test_optimum_matches_brute_force_on_small_maps():
    for s in range(80):
        sc = generate(1 + s % 6, 1 + (s * 5) % 6, 20 + (s * 11) % 120, (s * 25) % 101, 1000 + s)
        assert optimum(sc).key() == _brute_force(sc)
