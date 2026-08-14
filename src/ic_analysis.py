"""IC analysis — Information Coefficient, IC IR, t-stat, và multiple testing correction (Ngày 4-5)."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm, spearmanr


def forward_return(price_df: pd.DataFrame, n_fwd: int = 5) -> pd.DataFrame:
    """Forward return N ngày, dùng làm target để đánh giá factor."""
    return price_df.shift(-n_fwd) / price_df - 1


def calc_ic(factor_df: pd.DataFrame, fwd_ret_df: pd.DataFrame, min_valid: int = 5) -> pd.Series:
    """Cross-sectional Spearman IC giữa factor và forward return, theo từng ngày.

    min_valid: số mã tối thiểu có dữ liệu hợp lệ trong ngày để correlation có ý nghĩa.
    """
    ic = {}
    for date in factor_df.index:
        f, r = factor_df.loc[date], fwd_ret_df.loc[date]
        valid = f.notna() & r.notna()
        if valid.sum() >= min_valid:
            ic[date] = spearmanr(f[valid], r[valid])[0]
    return pd.Series(ic).dropna()


def ic_stats(ic_series: pd.Series) -> dict[str, float]:
    return {
        "Mean IC": ic_series.mean(),
        "Std IC": ic_series.std(),
        "IC IR": ic_series.mean() / ic_series.std(),
        "t-stat": ic_series.mean() / ic_series.std() * np.sqrt(len(ic_series)),
        "Hit Rate": (ic_series > 0).mean(),
        "N Obs": len(ic_series),
    }


def ic_summary_table(ic_series_dict: dict[str, pd.Series]) -> pd.DataFrame:
    """Bảng tổng hợp Mean IC / Std IC / IC IR / t-stat / Hit Rate / N Obs cho nhiều factor."""
    return pd.DataFrame({name: ic_stats(s) for name, s in ic_series_dict.items()}).T.round(4)


def align_common_obs(ic_series_dict: dict[str, pd.Series]) -> dict[str, pd.Series]:
    """Cắt toàn bộ IC series về cùng tập ngày quan sát (giao của index).

    Cần thiết vì các factor có lookback khác nhau (VD: momentum 12-1 cần ~252 phiên,
    RSI-based chỉ cần ~100 phiên) -> so sánh trực tiếp Mean IC/t-stat sẽ không công bằng
    nếu không align, do mỗi factor được test trên một giai đoạn thị trường khác nhau.
    """
    common_idx = None
    for s in ic_series_dict.values():
        common_idx = s.index if common_idx is None else common_idx.intersection(s.index)
    return {name: s.loc[common_idx] for name, s in ic_series_dict.items()}


def multiple_testing_correction(compare_table: pd.DataFrame, alpha: float = 0.05) -> pd.DataFrame:
    """Bonferroni & Benjamini-Hochberg (FDR) correction cho p-value suy ra từ t-stat.

    Lý do cần: so sánh nhiều factor cùng lúc trên cùng dữ liệu làm p-value riêng lẻ bị lạc quan
    (data snooping / multiple comparisons problem).
    """
    n_tests = len(compare_table)
    p_values = pd.Series(
        {name: 2 * (1 - norm.cdf(abs(row["t-stat"]))) for name, row in compare_table.iterrows()}
    )

    bonferroni_threshold = alpha / n_tests
    sig_bonferroni = p_values < bonferroni_threshold

    sorted_p = p_values.sort_values()
    bh_threshold = pd.Series([(i + 1) / n_tests * alpha for i in range(n_tests)], index=sorted_p.index)
    sig_bh = sorted_p <= bh_threshold
    cutoff_p = sorted_p[sig_bh].max() if sig_bh.any() else 0
    sig_bh_final = p_values <= cutoff_p

    return pd.DataFrame({
        "p-value": p_values,
        "Significant (raw, α=0.05)": p_values < alpha,
        f"Significant (Bonferroni, α={bonferroni_threshold:.4f})": sig_bonferroni,
        "Significant (BH/FDR)": sig_bh_final,
    }).round(4).sort_values("p-value")
