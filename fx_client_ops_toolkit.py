"""
FX Client Operations Toolkit
----------------------------
Portfolio project by Dhrukumar Valand (simulated data only)

Three problems a client-services team on an FX trading platform faces every day:

1. Trade reconciliation (STP check)
   Trades executed on the platform must arrive correctly in the client's
   Treasury Management System (TMS). The script compares both sides and
   classifies every "break": missing in TMS, notional mismatch,
   value-date mismatch, rate mismatch, duplicates.

2. Client request analytics
   ~1,500 client requests are analysed by category, first-response time,
   resolution time, SLA breaches and escalations to find root causes.

3. Onboarding funnel
   Time per onboarding step for new client organisations to find the bottleneck.

Run: python fx_client_ops_toolkit.py
"""
import numpy as np
import pandas as pd

rng = np.random.default_rng(7)

# ------------------------------------------------------------------
# 1. TRADE RECONCILIATION
# ------------------------------------------------------------------
n = 2_000
pairs = ["EUR/USD", "EUR/GBP", "USD/JPY", "EUR/CHF", "USD/CNH", "EUR/PLN"]
products = ["Spot", "Forward", "Swap", "NDF"]
platform = pd.DataFrame({
    "trade_id": [f"T{100000+i}" for i in range(n)],
    "client": rng.choice([f"Corp_{c:02d}" for c in range(1, 41)], n),
    "pair": rng.choice(pairs, n, p=[.35, .15, .15, .1, .1, .15]),
    "product": rng.choice(products, n, p=[.4, .3, .2, .1]),
    "notional": (rng.integers(50, 5000, n) * 1_000).astype(float),
    "rate": np.round(rng.uniform(0.8, 1.6, n), 5),
    "value_date": pd.Timestamp("2026-09-01") + pd.to_timedelta(rng.integers(2, 90, n), "D"),
})

tms = platform.copy()
idx = rng.permutation(n)
missing = idx[:38]                       # not exported to TMS
notional_err = idx[38:62]                # wrong amount (e.g. manual re-keying)
vdate_err = idx[62:95]                   # wrong value date (holiday calendar)
rate_err = idx[95:107]                   # rate rounded / truncated
tms.loc[notional_err, "notional"] *= rng.choice([0.1, 10, 1.001], len(notional_err))
tms.loc[vdate_err, "value_date"] += pd.Timedelta(days=1)
tms.loc[rate_err, "rate"] = np.round(tms.loc[rate_err, "rate"], 2)
tms = tms.drop(index=missing)
dups = tms.sample(9, random_state=1)     # duplicate imports
tms = pd.concat([tms, dups], ignore_index=True)


def reconcile(plat, tms):
    dup_ids = tms[tms.duplicated("trade_id")]["trade_id"]
    t = tms.drop_duplicates("trade_id")
    m = plat.merge(t, on="trade_id", how="left", suffixes=("_plat", "_tms"), indicator=True)
    breaks = []
    for _, r in m.iterrows():
        if r["_merge"] == "left_only":
            breaks.append((r.trade_id, r.client_plat, "Missing in TMS"))
            continue
        if abs(r.notional_plat - r.notional_tms) > 0.01:
            breaks.append((r.trade_id, r.client_plat, "Notional mismatch"))
        if r.value_date_plat != r.value_date_tms:
            breaks.append((r.trade_id, r.client_plat, "Value date mismatch"))
        if abs(r.rate_plat - r.rate_tms) > 1e-6:
            breaks.append((r.trade_id, r.client_plat, "Rate mismatch"))
    breaks += [(d, None, "Duplicate in TMS") for d in dup_ids]
    return pd.DataFrame(breaks, columns=["trade_id", "client", "break_type"])


# ------------------------------------------------------------------
# 2. CLIENT REQUEST ANALYTICS
# ------------------------------------------------------------------
cats = {  # category: (share, mean resolution hours, escalation prob)
    "User access / password": (.24, 1.5, .02),
    "Onboarding & setup": (.16, 20, .15),
    "Trade query / amendment": (.18, 6, .12),
    "TMS interface / STP": (.14, 30, .35),
    "Settlement instructions": (.12, 10, .10),
    "Regulatory reporting": (.08, 16, .20),
    "Product question": (.08, 3, .03),
}
m_req = 1_500
names = list(cats)
cat = rng.choice(names, m_req, p=[cats[c][0] for c in names])
req = pd.DataFrame({"category": cat})
req["first_response_min"] = rng.gamma(2, 12, m_req).round()
req["resolution_h"] = [rng.gamma(2, cats[c][1] / 2) for c in cat]
req["escalated"] = [rng.random() < cats[c][2] for c in cat]
SLA_H = 24
req["sla_breach"] = req["resolution_h"] > SLA_H

# ------------------------------------------------------------------
# 3. ONBOARDING FUNNEL
# ------------------------------------------------------------------
steps = {"Contract & KYC documents": 6, "Legal entity & user setup": 2,
         "Liquidity provider relationships": 5, "TMS / STP interface test": 8,
         "User training": 1, "Go-live": 1}
onb = pd.DataFrame({s: rng.gamma(2, d / 2, 60) for s, d in steps.items()})

if __name__ == "__main__":
    print("=== 1. Trade reconciliation: platform vs. client TMS ===")
    br = reconcile(platform, tms)
    print(f"Trades on platform: {n:,} | rows in TMS: {len(tms):,}")
    print(f"Breaks found: {len(br)} ({len(br) / n:.1%} of trades)")
    print(br["break_type"].value_counts().to_string())
    top = br.dropna().groupby("client").size().sort_values(ascending=False).head(3)
    print("Clients with most breaks:", ", ".join(f"{c} ({v})" for c, v in top.items()))
    hit = len(set(missing) | set(notional_err) | set(vdate_err) | set(rate_err))
    print(f"Planted errors detected: {br.trade_id.nunique() - 9}/{hit} trades + 9 duplicates")

    print("\n=== 2. Client request analytics (1,500 requests) ===")
    summ = req.groupby("category").agg(
        requests=("category", "size"),
        median_resolution_h=("resolution_h", "median"),
        sla_breach_rate=("sla_breach", "mean"),
        escalation_rate=("escalated", "mean"),
    ).sort_values("requests", ascending=False)
    summ["share_of_breaches"] = req[req.sla_breach].groupby("category").size() / req.sla_breach.sum()
    print(summ.fillna(0).round(2).to_string())
    print(f"\nOverall: median first response {req.first_response_min.median():.0f} min, "
          f"SLA breach rate {req.sla_breach.mean():.1%}, escalation rate {req.escalated.mean():.1%}")
    tms_share = summ.loc["TMS interface / STP", "share_of_breaches"]
    pw = summ.loc["User access / password"]
    print(f"Insight: TMS/STP issues are {summ.loc['TMS interface / STP','requests']/m_req:.0%} of requests "
          f"but {tms_share:.0%} of all SLA breaches.")
    print(f"Insight: {int(pw.requests)} password/access tickets ({pw.requests/m_req:.0%}) "
          f"-> self-service reset could remove ~{pw.requests*0.8:.0f} tickets per period.")

    print("\n=== 3. Onboarding funnel (60 new client organisations, days per step) ===")
    o = onb.median().round(1)
    print(o.to_string())
    print(f"Median total time to go-live: {onb.sum(axis=1).median():.1f} days; "
          f"bottleneck: {o.idxmax()} ({o.max() / o.sum():.0%} of total)")
