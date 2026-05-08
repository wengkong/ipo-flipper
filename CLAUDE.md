# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the App

```bash
pip install -r requirements.txt
streamlit run app.py
# Opens at http://localhost:8501
```

## Architecture

Two-file design with strict separation of concerns:

- **`strategies.py`** — Pure Python calculation functions. No Streamlit imports. Each strategy function returns `(batches: list[dict], summary: dict)`. The shared `_sell_price(ipo_price, gain_pct)` rounds up to the nearest cent using `math.ceil`.
- **`app.py`** — Streamlit UI only. Reads global IPO parameters (price, shares) from the sidebar, renders one tab per strategy, and draws a comparison table at the bottom.

## Sell Price Formula

Matches the Excel `CEILING` formula:
```python
math.ceil(ipo_price * (1 + gain_pct / 100) * 100) / 100
```

## Strategies

Tabs are listed alphabetically.

| Strategy | Key logic |
|---|---|
| All-In at Peak | Single batch holding every share, sells at one peak gain target |
| Asymmetric Ladder | User-defined share weights per batch, user-defined gain % per batch |
| Inverse Pyramid | Descending share weights `(N-i)`, evenly spaced gain targets |
| Split Equally | N equal-share batches, user-defined gain % per batch |
| Trailing Stop | All batches sell at `ceil(peak_price × (1 − trail_pct/100) × 100)/100` |

## Verification

```bash
python -c "
import strategies as s
batches, summary = s.split_equally(0.88, 4000, [30, 40])
assert summary['total_gain'] == 1260.0
batches, summary = s.asymmetric_ladder(0.88, 4000, [500,1000,2000,500], [20,30,40,55])
assert summary['total_gain'] == 1325.0
print('OK')
"
```
