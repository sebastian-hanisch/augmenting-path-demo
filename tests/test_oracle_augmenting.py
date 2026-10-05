"""Orakel-Regressionstest (Verbesserungswege): beliebige, gleichstandsreiche Kostenmatrizen gegen Brute Force und networkx.

Unabhängig vom Code der Demo: die größtmögliche Paarzahl und das kostenminimale Optimum kommen aus Aufzählung aller Matchings bzw.
aus networkx; jede Runde wird einzeln nachgeprüft (gewählte Kanten nicht im Matching, freigegebene im Matching, Endpunkte frei,
Weg einfach, Ergebnis ein Matching mit einem Paar mehr); die Greedy-Regeln und die Knotenüberdeckung werden neu gerechnet."""

import random

import numpy as np
import pytest

from ap_algorithm import SEARCHES, STARTS, augment, has_augmenting_path, start_pairs
from ap_greedy import optimum, run_rule
from ap_scenario import Scenario


def _scenario(rng):
    n, m = rng.randint(1, 6), rng.randint(1, 6)
    cmax = rng.choice([0, 1, 3, 10, 40])
    p = rng.choice([0.3, 0.6, 1.0])
    cost = np.array([[rng.randint(0, cmax) for _ in range(m)] for _ in range(n)], dtype=np.int64)
    feas = np.array([[rng.random() < p for _ in range(m)] for _ in range(n)], dtype=bool)
    return Scenario(((0, 0),) * n, ((0, 0),) * m, 0, cost, feas)


def _brute(sc):
    best = (-1, 0)

    def rec(i, used, cnt, c):
        nonlocal best
        if i == sc.n:
            if cnt > best[0] or (cnt == best[0] and c < best[1]):
                best = (cnt, c)
            return
        rec(i + 1, used, cnt, c)
        for j in range(sc.m):
            if sc.feasible[i, j] and not (used >> j) & 1:
                rec(i + 1, used | (1 << j), cnt + 1, c + int(sc.cost[i, j]))

    rec(0, 0, 0, 0)
    return best


def _greedy_edge(sc):
    edges = sorted((int(sc.cost[i, j]), i, j) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j])
    uv, uo, out = set(), set(), []
    for _c, i, j in edges:
        if i not in uv and j not in uo:
            uv.add(i)
            uo.add(j)
            out.append((i, j))
    return out


def _greedy_order(sc):
    uv, out = set(), []
    for j in range(sc.m):
        cands = [(int(sc.cost[i, j]), i) for i in range(sc.n) if i not in uv and sc.feasible[i, j]]
        if cands:
            _c, i = min(cands)
            uv.add(i)
            out.append((i, j))
    return out


def test_rounds_paths_cover_and_optimum_against_independent_oracles_on_tie_heavy_matrices():
    nx = pytest.importorskip("networkx")
    rng = random.Random(4242)
    for _ in range(100):
        sc = _scenario(rng)
        opt = _brute(sc)
        o = optimum(sc)
        assert (o.count, o.cost) == opt
        assert list(run_rule(sc, "edge").pairs) == _greedy_edge(sc) and list(run_rule(sc, "order").pairs) == _greedy_order(sc)
        g = nx.Graph()
        g.add_nodes_from([("v", i) for i in range(sc.n)])
        g.add_nodes_from([("o", j) for j in range(sc.m)])
        g.add_edges_from([(("v", i), ("o", j)) for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j]])
        assert len(nx.bipartite.maximum_matching(g, top_nodes=[("v", i) for i in range(sc.n)])) // 2 == opt[0]
        for start in STARTS:
            sp = start_pairs(sc, start)
            for search in SEARCHES:
                res = augment(sc, sp, search)
                assert res.count == opt[0] and not has_augmenting_path(sc, res.pairs)
                cur = dict(sp)
                for rd in res.rounds:
                    adds = [(i, j) for i, j, kind in rd.path if kind == "add"]
                    drops = [(i, j) for i, j, kind in rd.path if kind == "drop"]
                    assert len(adds) == len(drops) + 1 and rd.length == len(rd.path)
                    assert all(cur.get(i) != j and sc.feasible[i, j] for i, j in adds)
                    assert all(cur.get(i) == j for i, j in drops)
                    assert rd.path[0][0] not in cur and rd.path[-1][1] not in cur.values()
                    assert len({i for i, _ in adds}) == len(adds) and len({j for _, j in adds}) == len(adds)
                    for i, _j in drops:
                        del cur[i]
                    cur.update(adds)
                    assert len(set(cur.values())) == len(cur) == rd.pairs_after
                assert sorted(cur.items()) == list(res.pairs)
                cover_v, cover_o = set(res.cover_v), set(res.cover_o)
                assert len(cover_v) + len(cover_o) == res.count
                assert all(i in cover_v or j in cover_o for i in range(sc.n) for j in range(sc.m) if sc.feasible[i, j])
