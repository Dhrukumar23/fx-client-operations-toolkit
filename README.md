# FX Client Operations Toolkit

Python toolkit for three everyday problems of a client-services team on an FX trading platform. **All data is simulated.**

## 1. Trade reconciliation (STP check)
Trades executed on the platform must arrive correctly in the client's Treasury Management System (TMS).
The script compares 2,000 platform trades with the TMS export and classifies every break:

| Break type | Count |
|---|---|
| Missing in TMS | 38 |
| Value date mismatch | 33 |
| Notional mismatch | 24 |
| Rate mismatch | 12 |
| Duplicate in TMS | 9 |

**Result:** 116 breaks (5.8% of trades) – 100% of the planted errors detected.

## 2. Client request analytics
1,500 client requests analysed by category, first-response time, resolution time, SLA breaches (24h) and escalations.

- TMS interface / STP issues are **14% of requests but 52% of SLA breaches** → highest-value area for root-cause work.
- **25% of tickets are password / access requests** → a self-service reset could remove ~300 tickets per period.
- Overall: median first response 20 min, SLA breach rate 14.7%, escalation rate 12.7%.

## 3. Onboarding funnel
Six onboarding steps measured for 60 new client organisations.
Median time to go-live: **24.4 days**; bottleneck: **TMS / STP interface test (37% of total time)**.

## Run
```bash
pip install -r requirements.txt
python fx_client_ops_toolkit.py
```
Full output: [`fx_output.txt`](fx_output.txt)

*Author: Dhrukumar Valand*
