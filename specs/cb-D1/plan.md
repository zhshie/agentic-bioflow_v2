# cb-D1: su._number rejects NaN and Infinity

- Goal: a rates file that holds NaN or Infinity (json.load accepts both literals) must never turn into a NaN/inf SU, a NaN/inf money value or a 0 dollar value in su.py. They are treated as "not a number" like a missing value, so the answer is None with the reason.
- Source: cloud-burn tasks.json D1.
- Files: platform/abf_platform/su.py, platform/tests/test_su_finite.py (plus this plan and ledger.md).
- Approach: su.load_rates and su._number delegate to cloud_cost.load_rates / cloud_cost._number (the finite-checking copies, sister module). cloud_cost imports su at module top, so a top-level import in su.py would be circular (breaks when cloud_cost is imported first); the delegation therefore imports cloud_cost inside the function. su.load_rates keeps its own default (su.RATES_PATH read at call time, tests monkeypatch it), passing it explicitly to cloud_cost.load_rates, whose own default is the cloud rates file. month_total is not touched.
- RED tests (test_su_finite.py): _number on nan/inf/-inf; NaN and Infinity rate files through load_rates + su_of_tasks (top-level and site twd_per_su, factor, cpus, realtime); usd_rate / usd_of with Infinity and NaN; finite parity (same results as before for finite rates, default load_rates reads su_rates.json).
- Done: new tests green, test_estimate_su / test_su_* / test_cloud_* green, full run_all green, scope guard clean.
- Environment: venv /tmp/cb/venv, pip install -e platform; Linux.
- Not doing: month_total, cloud_cost.py, any HOT/FORBIDDEN file; no behaviour change for finite rates.
