"""Deflated Sharpe Ratio (Bailey & López de Prado, 2014) — Ngày 8.

Coi chuỗi IC hàng ngày của một factor như "return" của một chiến lược (nhất quán với cách
IC IR đã được dùng như Sharpe ratio của tín hiệu xuyên suốt project). DSR trả lời: "xác suất
Sharpe THẬT lớn hơn mức Sharpe cao nhất kỳ vọng đạt được thuần túy do may rủi, nếu đã thử N
chiến lược độc lập" — gộp 2 điều chỉnh mà t-stat/Sharpe thô bỏ sót:

    1. Non-normality: skewness/kurtosis thật của chuỗi return/IC (không giả định normal).
    2. Multiple testing (selection bias): benchmark so sánh là SR_0* (Sharpe max kỳ vọng dưới
       null với N trials), không phải 0.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import norm

EULER_MASCHERONI = 0.5772156649015329


def sharpe_std_error(sr: float, skew: float, kurt: float, n_obs: int) -> float:
    """SE(SR_hat): sai số chuẩn của Sharpe ratio, điều chỉnh skewness/kurtosis
    (Bailey & López de Prado, 2012).

        SE(SR) = sqrt( (1 - skew*SR + (kurt-1)/4 * SR^2) / (T-1) )

    `kurt` là kurtosis kiểu Pearson (normal=3), KHÔNG phải excess kurtosis.
    Nếu skew=0, kurt=3 (chuỗi normal): rút gọn về SE(SR) = sqrt((1+SR^2/2)/(T-1))
    — công thức Sharpe SE cổ điển.
    """
    return np.sqrt((1 - skew * sr + (kurt - 1) / 4 * sr ** 2) / (n_obs - 1))


def expected_max_sharpe(sr_trials: np.ndarray, n_trials: int) -> float:
    """SR_0*: kỳ vọng Sharpe TỐI ĐA quan sát được thuần túy do may rủi nếu thử n_trials
    chiến lược độc lập mà KHÔNG chiến lược nào có skill thật (null hypothesis).

        SR_0* = sqrt(Var[SR_n]) * [ (1-γ)*Z^-1(1 - 1/N) + γ*Z^-1(1 - 1/(N*e)) ]

    Var[SR_n]: phương sai thực nghiệm của các Sharpe quan sát được trên N trial đã chạy
    (dùng làm proxy khi không biết phân phối null thật). N càng lớn -> SR_0* càng cao.
    """
    var_sr = np.var(sr_trials, ddof=1)
    sr_std = np.sqrt(var_sr)
    return sr_std * (
        (1 - EULER_MASCHERONI) * norm.ppf(1 - 1 / n_trials)
        + EULER_MASCHERONI * norm.ppf(1 - 1 / (n_trials * np.e))
    )


def probabilistic_sharpe_ratio(returns: pd.Series, sr_benchmark: float = 0.0) -> dict:
    """PSR(SR*): xác suất Sharpe THẬT > benchmark SR*, điều chỉnh skew/kurtosis, CHƯA điều
    chỉnh multiple testing (single trial). Bước trung gian giữa t-stat thô và DSR đầy đủ.
    """
    n_obs = len(returns)
    sr_hat = returns.mean() / returns.std()
    skew = returns.skew()
    kurt = returns.kurtosis() + 3  # pandas .kurtosis() trả EXCESS kurtosis -> +3 về Pearson

    se_sr = sharpe_std_error(sr_hat, skew, kurt, n_obs)
    z = (sr_hat - sr_benchmark) / se_sr
    return {
        "SR_hat": sr_hat, "Skewness": skew, "Kurtosis": kurt,
        "SE(SR_hat)": se_sr, "Z-score": z, "PSR": norm.cdf(z), "N_obs": n_obs,
    }


def deflated_sharpe_ratio(returns: pd.Series, sr_trials: np.ndarray, n_trials: int) -> dict:
    """DSR = PSR(SR_0*): thay benchmark 0 bằng SR_0* (Sharpe max kỳ vọng dưới null, N trials).

    DSR ~ 1    -> Sharpe quan sát vượt xa mức "may rủi kỳ vọng" trong N lần thử -> skill đáng tin.
    DSR ~ 0.5  -> không phân biệt được với kết quả ngẫu nhiên tốt nhất trong N lần thử.
    DSR ~ 0    -> tệ hơn cả mức may rủi kỳ vọng.
    """
    n_obs = len(returns)
    sr_hat = returns.mean() / returns.std()
    skew = returns.skew()
    kurt = returns.kurtosis() + 3

    sr_0 = expected_max_sharpe(sr_trials, n_trials)
    se_sr = sharpe_std_error(sr_hat, skew, kurt, n_obs)
    z = (sr_hat - sr_0) / se_sr

    return {
        "SR_hat": sr_hat, "Skewness": skew, "Kurtosis": kurt,
        "SR_0_star": sr_0, "SE(SR_hat)": se_sr, "Z-score": z,
        "DSR": norm.cdf(z), "N_obs": n_obs, "N_trials": n_trials,
    }


def dsr_summary_table(ic_series_dict: dict[str, pd.Series], n_trials: int | None = None) -> pd.DataFrame:
    """DSR cho nhiều factor cùng lúc, dùng chính Sharpe (IC IR) của cả nhóm để ước lượng SR_0*.

    n_trials mặc định = số factor trong ic_series_dict (đúng số trial thực tế đã test).
    Yêu cầu các Series trong ic_series_dict đã align cùng tập ngày quan sát (xem
    ic_analysis.align_common_obs) để SR_0* được ước lượng công bằng.
    """
    n_trials = n_trials or len(ic_series_dict)
    sr_trials = np.array([s.mean() / s.std() for s in ic_series_dict.values()])

    results = {
        name: deflated_sharpe_ratio(s, sr_trials=sr_trials, n_trials=n_trials)
        for name, s in ic_series_dict.items()
    }
    return pd.DataFrame(results).T.round(4).sort_values("DSR", ascending=False)


def compare_sharpe_measures(ic_summary: pd.DataFrame, dsr_table: pd.DataFrame) -> pd.DataFrame:
    """Bảng so sánh 3 con số: Sharpe thô (IC IR) vs t-stat (chưa chỉnh N trials) vs DSR.

    ic_summary: output của ic_analysis.ic_summary_table() — cần cột "IC IR", "t-stat".
    dsr_table: output của dsr_summary_table() — cần cột "Z-score", "DSR".
    """
    return pd.DataFrame({
        "Sharpe_tho (IC_IR)": ic_summary["IC IR"],
        "t_stat (chua chinh N trials)": ic_summary["t-stat"],
        "DSR_Zscore": dsr_table["Z-score"],
        "DSR (0-1)": dsr_table["DSR"],
    }).round(4).sort_values("DSR (0-1)", ascending=False)


if __name__ == "__main__":
    # Sanity check: DSR trên chuỗi random thuần phải cho DSR ~ 0.5 (không có skill thật)
    rng = np.random.default_rng(0)
    fake_returns = pd.Series(rng.normal(0, 1, 250))
    fake_trials = rng.normal(0, 0.15, 12)
    print(deflated_sharpe_ratio(fake_returns, sr_trials=fake_trials, n_trials=12))
