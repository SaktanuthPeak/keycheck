"""Pipeline metrics over scenario items (Spec §9.1–9.2, plan Q2 table). Pure Python; no model code."""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np


def _div(a, b):
    return a / b if b else float("nan")


def _prf(tp, fp, fn):
    p, r = _div(tp, tp + fp), _div(tp, tp + fn)
    f1 = 2 * p * r / (p + r) if (tp + fp) and (tp + fn) and (p + r) > 0 else float("nan")
    return p, r, f1


def attach_assignment_check(result: dict, ev, item: dict) -> dict:
    """Mark whether each matched detection sits on the ground-truth key of its slot (slot assignment accuracy)."""
    gt = item["gt_boxes_u"][item["point_set"]] if item["point_set"] in item["gt_boxes_u"] else item["gt_boxes_u"]["gt"]
    for sid, s in result.get("slots", {}).items():
        if s["det"] is None:
            continue
        if sid not in gt:
            s["assign_ok"] = None
            continue
        c = ev.centers[s["det"]]
        b = gt[sid]
        s["assign_ok"] = bool(b[0] <= c[0] <= b[2] and b[1] <= c[1] <= b[3])
    return result


def slot_truth(item: dict, layout) -> dict:
    return {sid: ("missing" if sid not in item["observed"] else ("correct" if item["observed"][sid] == layout.labels[layout.index(sid)] else "incorrect"))
            for sid in layout.slot_ids}


def evaluate_scenario(name: str, items: list[dict], results: list[dict], layouts: dict) -> dict:
    """items/results are parallel lists. Returns a flat metrics dict for one scenario."""
    n = len(items)
    rej = [r["status"] == "rejected" for r in results]
    out: dict = {"scenario": name, "n_items": n, "rejected": int(sum(rej)), "rejection_rate": _div(sum(rej), n)}
    if name == "S4a":
        out["layout_mismatch_rate"] = _div(sum(1 for r in results if r["error_code"] == "LAYOUT_MISMATCH"), n)
        return out
    if name == "S4c":
        safe = [r["status"] == "rejected" or r["summary"]["incorrect"] == 0 for r in results]
        out["safe_rate"] = _div(sum(safe), n)
        out["false_alarm_rate"] = _div(sum(1 for r in results if r["status"] == "completed" and r["summary"]["incorrect"] > 0), n)
        return out
    tp = fp = fn = 0
    n_completed = n_all_ok = n_false_alarm = 0
    cov, unc = [], []
    lab_ok = lab_n = 0
    assign_ok = assign_n = 0
    sug_tp = sug_fp = sug_fn = 0
    miss_unc = miss_n = miss_claim = 0
    per_kind: dict = defaultdict(lambda: [0, 0, 0])
    conf: Counter = Counter()
    fp_ex, fn_ex = [], []
    for it, r in zip(items, results):
        lay = layouts[it["layout_id"]]
        truth = slot_truth(it, lay)
        n_true_inc = sum(v == "incorrect" for v in truth.values())
        if r["status"] == "rejected":
            fn += n_true_inc
            per_kind[it.get("swap_kind", "-")][2] += n_true_inc
            sug_fn += len(it["expect"]["suggestions"])
            continue
        n_completed += 1
        s = r["slots"]
        decided = [x for x in s.values() if x["status"] in ("correct", "incorrect")]
        cov.append(_div(len(decided), len(s)))
        unc.append(_div(r["summary"]["uncertain"], len(s)))
        item_fp = False
        full_ok = True
        for sid, st in truth.items():
            x = s[sid]
            if st == "missing":
                miss_n += 1
                miss_unc += x["status"] == "uncertain"
                miss_claim += x["status"] in ("correct", "incorrect")
                continue
            if x["status"] != st:
                full_ok = False
            if x["status"] == "incorrect" and st == "incorrect":
                tp += 1; per_kind[it.get("swap_kind", "-")][0] += 1
                lab_n += 1; lab_ok += x["observed_label"] == it["observed"][sid]
            elif x["status"] == "incorrect" and st == "correct":
                fp += 1; per_kind[it.get("swap_kind", "-")][1] += 1; item_fp = True
                if len(fp_ex) < 20:
                    fp_ex.append({"id": it["id"], "slot": sid, "expected": x["expected_label"], "observed": x["observed_label"], "true": it["observed"][sid]})
            elif st == "incorrect" and x["status"] != "incorrect":
                fn += 1; per_kind[it.get("swap_kind", "-")][2] += 1
                if len(fn_ex) < 20:
                    fn_ex.append({"id": it["id"], "slot": sid, "status": x["status"], "reason": x["reason"], "true": it["observed"][sid]})
            if x["status"] in ("correct", "incorrect") and sid in it["observed"]:
                conf[(it["observed"][sid], x["observed_label"])] += 1
            if x.get("assign_ok") is not None:
                assign_n += 1; assign_ok += bool(x["assign_ok"])
        full_ok = full_ok and r["summary"]["uncertain"] == len([1 for v in truth.values() if v == "missing"])
        n_all_ok += full_ok
        n_false_alarm += item_fp
        pred = {tuple(sorted(sg["slots"])) for sg in r["suggestions"]}
        exp = {tuple(sorted(sg["slots"])) for sg in it["expect"]["suggestions"]}
        sug_tp += len(pred & exp); sug_fp += len(pred - exp); sug_fn += len(exp - pred)
    p, rc, f1 = _prf(tp, fp, fn)
    out.update(completed=n_completed, incorrect_precision=p, incorrect_recall=rc, incorrect_f1=f1, tp=tp, fp=fp, fn=fn,
               false_alarm_image_rate=_div(n_false_alarm, n_completed), strict_full_board=_div(n_all_ok, n_completed),
               coverage=float(np.nanmean(cov)) if cov else float("nan"), uncertain_rate=float(np.nanmean(unc)) if unc else float("nan"),
               observed_label_acc=_div(lab_ok, lab_n), slot_assignment_acc=_div(assign_ok, assign_n),
               suggestion_precision=_prf(sug_tp, sug_fp, sug_fn)[0], suggestion_recall=_prf(sug_tp, sug_fp, sug_fn)[1],
               missing_slot_uncertain_rate=_div(miss_unc, miss_n), missing_slot_false_claim_rate=_div(miss_claim, miss_n),
               per_kind={k: dict(zip(("tp", "fp", "fn"), v), recall=_div(v[0], v[0] + v[2])) for k, v in per_kind.items() if k != "-"},
               fp_examples=fp_ex, fn_examples=fn_ex, confusion=[[a, b, c] for (a, b), c in conf.most_common(40)])
    return out


def split_by(items, results, key):
    groups = defaultdict(lambda: ([], []))
    for it, r in zip(items, results):
        g = key(it)
        groups[g][0].append(it); groups[g][1].append(r)
    return groups


def full_report(scen_items: dict, scen_results: dict, layouts: dict) -> dict:
    """Overall metrics per scenario + breakdown by seen/unseen brand and point set."""
    rep = {"overall": {}, "by_brand_type": {}, "by_point_set": {}}
    for name, items in scen_items.items():
        if not items:
            continue
        res = scen_results[name]
        rep["overall"][name] = evaluate_scenario(name, items, res, layouts)
        for g, (it, rs) in split_by(items, res, lambda i: "seen_brand" if i["seen_brand"] else "heldout_brand").items():
            rep["by_brand_type"].setdefault(g, {})[name] = evaluate_scenario(name, it, rs, layouts)
        for g, (it, rs) in split_by(items, res, lambda i: i["point_set"]).items():
            rep["by_point_set"].setdefault(g, {})[name] = evaluate_scenario(name, it, rs, layouts)
    return rep
