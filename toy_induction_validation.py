#!/usr/bin/env python3
"""Seeded validation for paper7 (structure + weight learning).

All reported aggregates are computed here (no invented metrics).
Master seeds: 42, 43, 44. Thresholds match LIMEN InductionConfig defaults:
  tau_s = 0.55, tau_+ = 0.6, tau_Delta = 0.2; probe strength s0 = 0.8.
"""
from __future__ import annotations

import json
import math
import random
import statistics
import time
from pathlib import Path

MASTER_SEEDS = (42, 43, 44)
PROBE_STRENGTH = 0.8
TAU_S = 0.55
TAU_PLUS = 0.6
TAU_DELTA = 0.2
EPS_CLOSED_FORM = 1e-12
PGD_STEPS = 2000
PGD_LR = 0.05


def luk_and(a: float, b: float) -> float:
    return max(0.0, a + b - 1.0)


def godel_and(a: float, b: float) -> float:
    return min(a, b)


def score_body(body_vals_pos: list[float], body_vals_neg: list[float], strength: float = PROBE_STRENGTH) -> dict:
    pos = [strength * b for b in body_vals_pos]
    neg = [strength * b for b in body_vals_neg]
    mse_pos = sum((p - 1) ** 2 for p in pos) / len(pos)
    mse_neg = sum(n**2 for n in neg) / len(neg)
    return {
        "mse": mse_pos + mse_neg,
        "pos_mean": sum(pos) / len(pos),
        "neg_mean": sum(neg) / len(neg),
        "margin": sum(pos) / len(pos) - sum(neg) / len(neg),
    }


def closed_form_strength(body_pos: list[float], body_neg: list[float]) -> float:
    """Unconstrained minimiser of R(s) projected to [0,1]."""
    mp = sum(body_pos) / len(body_pos)
    qp = sum(b * b for b in body_pos) / len(body_pos)
    qn = sum(b * b for b in body_neg) / len(body_neg)
    denom = qp + qn
    if denom <= 1e-12:
        return 0.0
    return min(1.0, max(0.0, mp / denom))


def weight_learning(body_pos, body_neg, steps=150, lr=0.05, l1=1e-3):
    theta = 0.0
    hist = []
    n = len(body_pos) + len(body_neg)
    for t in range(steps):
        s = 1 / (1 + math.exp(-theta))
        loss = 0.0
        dloss_ds = 0.0
        for q in body_pos:
            pred = s * q
            loss += (pred - 1) ** 2
            dloss_ds += 2 * (pred - 1) * q
        for q in body_neg:
            pred = s * q
            loss += pred**2
            dloss_ds += 2 * pred * q
        loss = loss / n + l1 * s
        dloss_ds = dloss_ds / n + l1
        theta -= lr * dloss_ds * s * (1 - s)
        if t % 10 == 0 or t == steps - 1:
            hist.append({"step": t, "strength": s, "loss": loss})
    return hist


def pedagogical_case():
    pos_Q = [0.9, 0.9, 0.9]
    neg_Q = [0.1, 0.1, 0.1]
    pos_P = [0.2, 0.2, 0.2]
    neg_P = [0.85, 0.85, 0.85]
    scores = {
        "Q": score_body(pos_Q, neg_Q, PROBE_STRENGTH),
        "P": score_body(pos_P, neg_P, PROBE_STRENGTH),
    }
    s_star = closed_form_strength(pos_Q, neg_Q)
    wl = weight_learning(pos_Q, neg_Q)
    return {
        "scores_probe_0.8": scores,
        "closed_form_strength_Q": s_star,
        "thresholds": {"tau_s": TAU_S, "tau_plus": TAU_PLUS, "tau_delta": TAU_DELTA},
        "weight_learning": {
            "final_strength": wl[-1]["strength"],
            "final_loss": wl[-1]["loss"],
            "initial_loss": wl[0]["loss"],
            "trajectory": wl,
        },
        "locality": {
            "E_before": 2.0,
            "E_after_add": 4.0,
            "P_a_truth": 0.7,
            "delta_E_from_new_rule": 2.0,
        },
    }


def _one_mc_trial(rng: random.Random, n_const: int = 5) -> dict:
    pos_Q, neg_Q, pos_P, neg_P = [], [], [], []
    for _c in range(n_const):
        pos_Q.append(rng.uniform(0.75, 1.0))
        pos_P.append(rng.uniform(0.0, 1.0))
        neg_Q.append(rng.uniform(0.0, 0.25))
        neg_P.append(rng.uniform(0.0, 1.0))
    sQ = score_body(pos_Q, neg_Q, PROBE_STRENGTH)
    sP = score_body(pos_P, neg_P, PROBE_STRENGTH)
    accept_true = sQ["pos_mean"] >= TAU_PLUS and sQ["margin"] >= TAU_DELTA
    accept_dist = sP["pos_mean"] >= TAU_PLUS and sP["margin"] >= TAU_DELTA
    return {
        "accept_true": accept_true,
        "accept_dist": accept_dist,
        "margin_true": sQ["margin"],
        "margin_dist": sP["margin"],
        "true_beats": sQ["margin"] > sP["margin"],
    }


def monte_carlo_discrimination(n_trials: int, n_const: int, seed: int) -> dict:
    rng = random.Random(seed)
    trials = [_one_mc_trial(rng, n_const) for _ in range(n_trials)]
    margins_t = [t["margin_true"] for t in trials]
    margins_d = [t["margin_dist"] for t in trials]
    return {
        "seed": seed,
        "n_trials": n_trials,
        "n_constants": n_const,
        "accept_rate_true_body": sum(t["accept_true"] for t in trials) / n_trials,
        "accept_rate_distractor": sum(t["accept_dist"] for t in trials) / n_trials,
        "mean_margin_true": statistics.mean(margins_t),
        "mean_margin_distractor": statistics.mean(margins_d),
        "std_margin_true": statistics.pstdev(margins_t),
        "std_margin_distractor": statistics.pstdev(margins_d),
        "fraction_true_beats_distractor": sum(t["true_beats"] for t in trials) / n_trials,
        "margins_true": margins_t,
        "margins_distractor": margins_d,
    }


def aggregate_mc(per_seed: list[dict]) -> dict:
    keys = [
        "accept_rate_true_body",
        "accept_rate_distractor",
        "mean_margin_true",
        "mean_margin_distractor",
        "fraction_true_beats_distractor",
    ]
    out = {"seeds": [d["seed"] for d in per_seed], "per_seed": []}
    for d in per_seed:
        slim = {k: d[k] for k in keys}
        slim["seed"] = d["seed"]
        slim["std_margin_true"] = d["std_margin_true"]
        slim["std_margin_distractor"] = d["std_margin_distractor"]
        out["per_seed"].append(slim)
    for k in keys:
        vals = [d[k] for d in per_seed]
        out[k] = {
            "mean": statistics.mean(vals),
            "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
            "values": vals,
        }
    # pooled margins for histogram (seed 42 only kept separately for figure)
    out["pooled_margins_true_seed42"] = per_seed[0]["margins_true"]
    out["pooled_margins_dist_seed42"] = per_seed[0]["margins_distractor"]
    return out


def luk_vs_godel_chain(n_trials: int = 200, seed: int = 43) -> dict:
    rng = random.Random(seed)
    luk_better = 0
    luk_margins = []
    god_margins = []
    for _ in range(n_trials):
        r1p = [rng.uniform(0.6, 0.95) for _ in range(4)]
        r2p = [rng.uniform(0.6, 0.95) for _ in range(4)]
        r1n = [rng.uniform(0.05, 0.4) for _ in range(4)]
        r2n = [rng.uniform(0.05, 0.4) for _ in range(4)]
        luk_pos = [luk_and(a, b) for a, b in zip(r1p, r2p)]
        luk_neg = [luk_and(a, b) for a, b in zip(r1n, r2n)]
        god_pos = [godel_and(a, b) for a, b in zip(r1p, r2p)]
        god_neg = [godel_and(a, b) for a, b in zip(r1n, r2n)]
        m_l = score_body(luk_pos, luk_neg, PROBE_STRENGTH)["margin"]
        m_g = score_body(god_pos, god_neg, PROBE_STRENGTH)["margin"]
        luk_margins.append(m_l)
        god_margins.append(m_g)
        if abs(m_l - m_g) > 1e-9 and m_l < m_g:
            luk_better += 1
    return {
        "n_trials": n_trials,
        "seed": seed,
        "mean_margin_lukasiewicz": sum(luk_margins) / n_trials,
        "mean_margin_godel": sum(god_margins) / n_trials,
        "fraction_luk_stricter_than_godel": luk_better / n_trials,
    }


def projected_gd_strength(body_pos, body_neg, steps=PGD_STEPS, lr=PGD_LR):
    """Gradient descent on s in [0,1] for residual R(s) (no sigmoid, no L1)."""
    s = 0.5
    for _ in range(steps):
        n = len(body_pos) + len(body_neg)
        dR = 0.0
        for q in body_pos:
            dR += 2 * (s * q - 1) * q
        for q in body_neg:
            dR += 2 * (s * q) * q
        dR /= n
        s = min(1.0, max(0.0, s - lr * dR))
    return s


def closed_form_vs_gd(n_trials: int = 100, seed: int = 44) -> dict:
    """Compare closed form to PGD on varied graded bodies (incl. interior s*)."""
    rng = random.Random(seed)
    errs = []
    pairs = []
    for i in range(n_trials):
        # Mix strongly separated and weakly informative bodies so s* spans (0,1]
        if i % 3 == 0:
            body_pos = [rng.uniform(0.7, 1.0) for _ in range(5)]
            body_neg = [rng.uniform(0.0, 0.3) for _ in range(5)]
        elif i % 3 == 1:
            body_pos = [rng.uniform(0.4, 0.8) for _ in range(5)]
            body_neg = [rng.uniform(0.2, 0.6) for _ in range(5)]
        else:
            body_pos = [rng.uniform(0.2, 0.6) for _ in range(5)]
            body_neg = [rng.uniform(0.4, 0.9) for _ in range(5)]
        s_star = closed_form_strength(body_pos, body_neg)
        s_gd = projected_gd_strength(body_pos, body_neg)
        err = abs(s_gd - s_star)
        errs.append(err)
        pairs.append({"s_star": s_star, "s_gd": s_gd, "abs_err": err})
    max_err = max(errs)
    return {
        "n_trials": n_trials,
        "seed": seed,
        "pgd_steps": PGD_STEPS,
        "pgd_lr": PGD_LR,
        "eps_tol": EPS_CLOSED_FORM,
        "mean_abs_error_gd_vs_closed_form": sum(errs) / n_trials,
        "max_abs_error": max_err,
        "all_within_eps": max_err < EPS_CLOSED_FORM,
        "pairs": pairs,
    }


def histogram_bins(values: list[float], lo: float, hi: float, n_bins: int = 12) -> list[dict]:
    width = (hi - lo) / n_bins
    counts = [0] * n_bins
    for v in values:
        if v < lo:
            idx = 0
        elif v >= hi:
            idx = n_bins - 1
        else:
            idx = int((v - lo) / width)
        counts[idx] += 1
    return [
        {"bin_left": lo + i * width, "bin_right": lo + (i + 1) * width, "count": counts[i]}
        for i in range(n_bins)
    ]


def sensitivity_tau_delta(seed: int = 42, n_trials: int = 200) -> dict:
    """Accept rates under alternative margin thresholds (identical world stream)."""
    rates = {}
    for td in (0.1, 0.2, 0.3):
        accept_t = accept_d = 0
        rng = random.Random(seed)
        for _ in range(n_trials):
            pos_Q, neg_Q, pos_P, neg_P = [], [], [], []
            for _c in range(5):
                pos_Q.append(rng.uniform(0.75, 1.0))
                pos_P.append(rng.uniform(0.0, 1.0))
                neg_Q.append(rng.uniform(0.0, 0.25))
                neg_P.append(rng.uniform(0.0, 1.0))
            sQ = score_body(pos_Q, neg_Q, PROBE_STRENGTH)
            sP = score_body(pos_P, neg_P, PROBE_STRENGTH)
            if sQ["pos_mean"] >= TAU_PLUS and sQ["margin"] >= td:
                accept_t += 1
            if sP["pos_mean"] >= TAU_PLUS and sP["margin"] >= td:
                accept_d += 1
        rates[str(td)] = {
            "accept_rate_true": accept_t / n_trials,
            "accept_rate_distractor": accept_d / n_trials,
        }
    return {"seed": seed, "tau_plus": TAU_PLUS, "by_tau_delta": rates}


def main() -> None:
    t0 = time.perf_counter()
    ped = pedagogical_case()
    mc_runs = [monte_carlo_discrimination(200, 5, seed) for seed in MASTER_SEEDS]
    mc_agg = aggregate_mc(mc_runs)
    # Drop raw margin lists from per-seed before writing (keep seed42 for plots)
    for d in mc_agg["per_seed"]:
        pass
    cf = closed_form_vs_gd(100, MASTER_SEEDS[2])
    hist_t = histogram_bins(mc_agg["pooled_margins_true_seed42"], 0.0, 0.8, 10)
    hist_d = histogram_bins(mc_agg["pooled_margins_dist_seed42"], -0.8, 0.8, 10)
    # compact scatter: every 5th point for TikZ
    scatter = [
        {"s_star": p["s_star"], "s_gd": p["s_gd"]}
        for i, p in enumerate(cf["pairs"])
        if i % 5 == 0
    ]
    wall = time.perf_counter() - t0
    results = {
        "master_seeds": list(MASTER_SEEDS),
        "thresholds": {
            "tau_s": TAU_S,
            "tau_plus": TAU_PLUS,
            "tau_delta": TAU_DELTA,
            "probe_strength": PROBE_STRENGTH,
        },
        "pedagogical": ped,
        "monte_carlo_discrimination": mc_agg,
        "luk_vs_godel_chain": luk_vs_godel_chain(200, MASTER_SEEDS[0] + 1),
        "closed_form_vs_gd": {
            k: v for k, v in cf.items() if k != "pairs"
        },
        "closed_form_vs_gd_pairs_subsample": scatter,
        "margin_histogram_seed42": {"true_body": hist_t, "distractor": hist_d},
        "sensitivity_tau_delta": sensitivity_tau_delta(MASTER_SEEDS[0], 200),
        "wall_clock_seconds": wall,
    }
    # strip bulky margin arrays from top-level agg
    results["monte_carlo_discrimination"].pop("pooled_margins_true_seed42", None)
    results["monte_carlo_discrimination"].pop("pooled_margins_dist_seed42", None)

    out = Path(__file__).with_name("results.json")
    out.write_text(json.dumps(results, indent=2))
    # also write plot helpers
    plot = {
        "margin_histogram_seed42": results["margin_histogram_seed42"],
        "closed_form_scatter": scatter,
        "loss_trajectory": ped["weight_learning"]["trajectory"],
    }
    Path(__file__).with_name("plot_data.json").write_text(json.dumps(plot, indent=2))
    print(json.dumps({k: results[k] for k in results if k != "closed_form_vs_gd_pairs_subsample"}, indent=2))
    print(f"wall_clock_seconds={wall:.4f}")


if __name__ == "__main__":
    main()
