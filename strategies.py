import math


def _ceil_cent(price: float) -> float:
    return math.ceil(price * 100) / 100


def _sell_price(ipo_price: float, gain_pct: float) -> float:
    return _ceil_cent(ipo_price * (1 + gain_pct / 100))


def _batch_row(i: int, shares: float, gain_pct: float, ipo_price: float) -> dict:
    sp = _sell_price(ipo_price, gain_pct)
    gross = round(sp * shares, 2)
    gain = round((sp - ipo_price) * shares, 2)
    return {
        "Batch": i,
        "Shares": int(shares),
        "Gain %": gain_pct,
        "Sell Price": sp,
        "Gross Proceeds": gross,
        "Gain": gain,
    }


def _summary(batches: list[dict], ipo_price: float, total_shares: int) -> dict:
    total_gain = round(sum(b["Gain"] for b in batches), 2)
    total_proceeds = round(sum(b["Gross Proceeds"] for b in batches), 2)
    total_cost = round(ipo_price * total_shares, 2)
    roi = round(total_gain / total_cost * 100, 2) if total_cost else 0
    return {
        "total_gain": total_gain,
        "total_proceeds": total_proceeds,
        "total_cost": total_cost,
        "roi_pct": roi,
    }


def split_equally(ipo_price: float, total_shares: int, gain_targets: list[float]):
    n = len(gain_targets)
    shares_each = total_shares / n
    batches = [_batch_row(i + 1, shares_each, g, ipo_price) for i, g in enumerate(gain_targets)]
    return batches, _summary(batches, ipo_price, total_shares)


def asymmetric_ladder(ipo_price: float, total_shares: int, weights: list[float], gain_targets: list[float]):
    total_weight = sum(weights)
    shares_list = [round(w / total_weight * total_shares) for w in weights]
    # Fix rounding so shares sum exactly to total_shares
    diff = total_shares - sum(shares_list)
    shares_list[-1] += diff
    batches = [_batch_row(i + 1, s, g, ipo_price) for i, (s, g) in enumerate(zip(shares_list, gain_targets))]
    return batches, _summary(batches, ipo_price, total_shares)


def inverse_pyramid(ipo_price: float, total_shares: int, n: int, min_gain: float, max_gain: float):
    # More shares at lower gain targets (w_i = N - i, descending)
    raw_weights = [n - i for i in range(n)]
    total_weight = sum(raw_weights)
    shares_list = [round(w / total_weight * total_shares) for w in raw_weights]
    diff = total_shares - sum(shares_list)
    shares_list[-1] += diff

    if n == 1:
        targets = [min_gain]
    else:
        step = (max_gain - min_gain) / (n - 1)
        targets = [round(min_gain + i * step, 2) for i in range(n)]

    batches = [_batch_row(i + 1, s, g, ipo_price) for i, (s, g) in enumerate(zip(shares_list, targets))]
    return batches, _summary(batches, ipo_price, total_shares)


def trailing_stop(
    ipo_price: float,
    total_shares: int,
    weights: list[float],
    peak_gain_pct: float,
    trail_pct: float,
):
    peak_price = ipo_price * (1 + peak_gain_pct / 100)
    stop_price = _ceil_cent(peak_price * (1 - trail_pct / 100))
    # Effective gain % relative to IPO price
    effective_gain_pct = round((stop_price / ipo_price - 1) * 100, 2)

    total_weight = sum(weights)
    shares_list = [round(w / total_weight * total_shares) for w in weights]
    diff = total_shares - sum(shares_list)
    shares_list[-1] += diff

    batches = []
    for i, s in enumerate(shares_list):
        gross = round(stop_price * s, 2)
        gain = round((stop_price - ipo_price) * s, 2)
        batches.append({
            "Batch": i + 1,
            "Shares": int(s),
            "Gain %": effective_gain_pct,
            "Sell Price": stop_price,
            "Gross Proceeds": gross,
            "Gain": gain,
        })

    return batches, _summary(batches, ipo_price, total_shares)
