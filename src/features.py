"""Feature engineering — toàn bộ alpha factor từ Ngày 4 (7 factor gốc) và Ngày 5 (RSI-regime + ensemble).

Factor Ngày 4:
    Momentum_12_1, MeanReversion_Z, VolumeRatio, AlphaA_RetCorr, AlphaB_TSRankVol,
    AlphaC_TrendCond, ZLEMA_Reversion

Factor Ngày 5 (mở rộng từ AlphaC_TrendCond, dùng RSI):
    AlphaD_NoRegime, AlphaD4_RegimeSwitch, AlphaD5_SoftRegime,
    Ensemble_C_D4, Ensemble_C_D5
"""
from __future__ import annotations

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Helper functions (kiểu Alpha101 / WorldQuant)
# ---------------------------------------------------------------------------

def rank(df: pd.DataFrame) -> pd.DataFrame:
    """Cross-sectional percentile rank (0-1), theo từng ngày."""
    return df.rank(axis=1, pct=True)


def delta(df: pd.DataFrame, d: int) -> pd.DataFrame:
    return df.diff(d)


def delay(df: pd.DataFrame, d: int) -> pd.DataFrame:
    return df.shift(d)


def ts_sum(df: pd.DataFrame, d: int) -> pd.DataFrame:
    return df.rolling(d).sum()


def ts_min(df: pd.DataFrame, d: int) -> pd.DataFrame:
    return df.rolling(d).min()


def ts_max(df: pd.DataFrame, d: int) -> pd.DataFrame:
    return df.rolling(d).max()


def ts_rank(df: pd.DataFrame, d: int) -> pd.DataFrame:
    """Time-series percentile rank của giá trị mới nhất trong window d, theo từng cột."""
    return df.rolling(d).apply(lambda x: pd.Series(x).rank(pct=True).iloc[-1], raw=False)


def correlation(df1: pd.DataFrame, df2: pd.DataFrame, d: int) -> pd.DataFrame:
    return df1.rolling(d).corr(df2)


def zlema(series: pd.Series, period: int = 20) -> pd.Series:
    lag = (period - 1) // 2
    adjusted = series + (series - series.shift(lag))
    return adjusted.ewm(span=period, adjust=False).mean()


def calc_rsi(price_df: pd.DataFrame, window: int = 14) -> pd.DataFrame:
    """RSI với Wilder's smoothing, vectorized theo cột."""
    delta_p = price_df.diff()
    gain = delta_p.clip(lower=0)
    loss = -delta_p.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / window, min_periods=window, adjust=False).mean()
    rs = avg_gain / avg_loss
    return 100 - 100 / (1 + rs)


# ---------------------------------------------------------------------------
# Ngày 4 — 7 factor gốc
# ---------------------------------------------------------------------------

def build_day4_factors(price_df: pd.DataFrame, open_df: pd.DataFrame, volume_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """7 factor gốc: Momentum, MeanReversion_Z, VolumeRatio, AlphaA/B/C, ZLEMA."""
    returns = price_df.pct_change()
    adv20 = volume_df.rolling(20).mean()

    # 1. Momentum 12-1: return 12 tháng, bỏ tháng gần nhất
    mom_12_1 = price_df.shift(21) / price_df.shift(252) - 1

    # 2. Mean-reversion: z-score của return 5 ngày so với phân phối 20 phiên gần nhất
    ret_5d = price_df.pct_change(5)
    reversion_z = (ret_5d - ret_5d.rolling(20).mean()) / ret_5d.rolling(20).std()

    # 3. Volume ratio: volume hôm nay / volume trung bình 20 phiên
    volume_ratio = volume_df / adv20

    # 4. Alpha A: momentum ngắn hạn 3 ngày đảo dấu, nhân với đồng biến open-volume 10 ngày
    alpha_a = (-1 * rank(delta(returns, 3))) * correlation(open_df, volume_df, 10)

    # 5. Alpha B: vị trí giá 10 phiên, độ cong giá, bất thường volume 5 phiên
    alpha_b = ((-1 * rank(ts_rank(price_df, 10)))
               * rank(delta(delta(price_df, 1), 1))
               * rank(ts_rank(volume_df / adv20, 5)))

    # 6. Alpha C: ternary theo chế độ thị trường (trend rõ vs sideway)
    trend_cond = (delta(ts_sum(price_df, 100) / 100, 100) / delay(price_df, 100)) <= 0.05
    alpha_c = pd.DataFrame(
        np.where(trend_cond, -1 * (price_df - ts_min(price_df, 100)), -1 * delta(price_df, 3)),
        index=price_df.index, columns=price_df.columns,
    )

    # 7. ZLEMA mean-reversion: giá lệch khỏi ZLEMA-20 bao nhiêu %
    zlema_df = price_df.apply(zlema)
    alpha_zlema = -(price_df - zlema_df) / zlema_df

    return {
        "Momentum_12_1": mom_12_1,
        "MeanReversion_Z": reversion_z,
        "VolumeRatio": volume_ratio,
        "AlphaA_RetCorr": alpha_a,
        "AlphaB_TSRankVol": alpha_b,
        "AlphaC_TrendCond": alpha_c,
        "ZLEMA_Reversion": alpha_zlema,
    }


# ---------------------------------------------------------------------------
# Ngày 5 — RSI-regime factors + ensemble với Alpha C
# ---------------------------------------------------------------------------

SLOPE_WINDOW = 5  # horizon tính slope RSI


def build_day5_factors(price_df: pd.DataFrame, alpha_c: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """AlphaD (pure), AlphaD4 (regime switch cứng), AlphaD5 (soft regime), Ensemble C+D4, Ensemble C+D5.

    Yêu cầu alpha_c đã được tính từ build_day4_factors() để đảm bảo dùng cùng công thức.
    """
    rsi_df = calc_rsi(price_df, window=14)
    rsi_slope = (rsi_df - rsi_df.shift(SLOPE_WINDOW)) / SLOPE_WINDOW

    # AlphaD (No Regime): pure trend-following theo slope RSI
    alpha_d = pd.DataFrame(np.sign(rsi_slope), index=rsi_df.index, columns=rsi_df.columns)

    # AlphaD4 (Regime Switch): override reversal khi RSI chạm cực trị 100 ngày, fallback theo slope
    rsi_high_100 = rsi_df >= ts_max(rsi_df, 100)
    rsi_low_100 = rsi_df <= ts_min(rsi_df, 100)
    alpha_d4 = pd.DataFrame(
        np.select([rsi_high_100.values, rsi_low_100.values], [-1, 1], default=alpha_d.values),
        index=rsi_df.index, columns=rsi_df.columns,
    )

    # AlphaD5 (Soft Regime Blend): trộn liên tục theo cường độ trend + percentile RSI trong 100 ngày
    trend_strength = (delta(ts_sum(price_df, 100) / 100, 100) / delay(price_df, 100)).abs()
    trend_weight = np.tanh(trend_strength / 0.05)

    rsi_range_100 = ts_max(rsi_df, 100) - ts_min(rsi_df, 100)
    rsi_pct_pos = (rsi_df - ts_min(rsi_df, 100)) / rsi_range_100
    extreme_high = rsi_pct_pos >= 0.9
    extreme_low = rsi_pct_pos <= 0.1

    slope_signal_continuous = np.tanh(rsi_slope / 2)
    blended_signal = trend_weight * slope_signal_continuous

    alpha_d5 = pd.DataFrame(
        np.select([extreme_high.values, extreme_low.values], [-1, 1], default=blended_signal.values),
        index=rsi_df.index, columns=rsi_df.columns,
    )

    # Ensemble: Alpha C (rank-scaled về [-1,1]) trung bình 50/50 với D4 / D5
    alpha_c_scaled = 2 * rank(alpha_c) - 1
    ensemble_c_d4 = (alpha_c_scaled + alpha_d4) / 2
    ensemble_c_d5 = (alpha_c_scaled + alpha_d5) / 2

    return {
        "AlphaD_NoRegime": alpha_d,
        "AlphaD4_RegimeSwitch": alpha_d4,
        "AlphaD5_SoftRegime": alpha_d5,
        "Ensemble_C_D4": ensemble_c_d4,
        "Ensemble_C_D5": ensemble_c_d5,
    }


def build_all_factors(price_df: pd.DataFrame, open_df: pd.DataFrame, volume_df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """Toàn bộ factor Ngày 4 + Ngày 5, trả về 1 dict duy nhất."""
    day4 = build_day4_factors(price_df, open_df, volume_df)
    day5 = build_day5_factors(price_df, day4["AlphaC_TrendCond"])
    return {**day4, **day5}
