"""Monte Carlo simulation cho return có tương quan, dựa trên Cholesky decomposition (Ngày 6).

Pipeline: covariance matrix -> kiểm tra PSD/PD -> (shrinkage nếu cần) -> Cholesky -> sinh return mô phỏng.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

TOL = 1e-8  # dung sai floating-point cho kiểm tra eigenvalue >= 0


def check_psd(cov: pd.DataFrame) -> tuple[bool, np.ndarray]:
    """Kiểm tra Positive Semi-Definite: mọi eigenvalue >= 0 (cho phép bằng 0)."""
    eigvals = np.linalg.eigvalsh(cov.values)
    return bool(np.all(eigvals >= -TOL)), eigvals


def check_pd_cholesky(cov: pd.DataFrame) -> np.ndarray | None:
    """Kiểm tra Positive Definite bằng Cholesky. Trả về L nếu thành công, None nếu thất bại."""
    try:
        return np.linalg.cholesky(cov.values)
    except np.linalg.LinAlgError:
        return None


def check_min_observations(returns: pd.DataFrame) -> pd.Series:
    """Điều kiện cần cho PD: số quan sát T mỗi mã phải >= N (số tài sản), nếu không cov_matrix rank-deficient."""
    return returns.count().sort_values()


def shrink_cov(cov: pd.DataFrame, alpha: float = 0.3) -> pd.DataFrame:
    """Linear shrinkage (kiểu Ledoit-Wolf rút gọn) để khôi phục PD khi sample covariance không PD.

    shrunk = (1 - alpha) * sample_cov + alpha * target
    target = ma trận đường chéo với phương sai trung bình toàn bộ tài sản.
    alpha càng lớn -> càng an toàn (PD) nhưng càng mất thông tin tương quan gốc.
    """
    n = cov.shape[0]
    avg_var = np.trace(cov.values) / n
    target = np.eye(n) * avg_var
    shrunk = (1 - alpha) * cov.values + alpha * target
    return pd.DataFrame(shrunk, index=cov.index, columns=cov.columns)


def get_pd_cholesky(cov: pd.DataFrame, max_alpha: float = 0.9, alpha_step: float = 0.1) -> tuple[np.ndarray, float]:
    """Lấy Cholesky factor L hợp lệ, tự động shrink dần nếu cov gốc không PD.

    Trả về (L, alpha_used). alpha_used = 0 nghĩa là cov gốc đã PD, không cần shrink.
    """
    L = check_pd_cholesky(cov)
    if L is not None:
        return L, 0.0

    alpha = alpha_step
    while alpha <= max_alpha:
        L = check_pd_cholesky(shrink_cov(cov, alpha))
        if L is not None:
            return L, alpha
        alpha += alpha_step

    raise ValueError(f"Không thể khôi phục PD ngay cả với alpha={max_alpha}. Kiểm tra lại dữ liệu (T vs N).")


def simulate_correlated_returns(
    returns: pd.DataFrame,
    n_sims: int = 10_000,
    seed: int = 42,
) -> pd.DataFrame:
    """Sinh return mô phỏng có tương quan theo covariance matrix của `returns`, dùng Cholesky.

    Tự động shrink covariance nếu không PD (VD: T < N hoặc đa cộng tuyến).
    """
    cov_matrix = returns.cov()
    symbols = returns.columns.tolist()
    n_assets = len(symbols)

    L, alpha_used = get_pd_cholesky(cov_matrix)
    if alpha_used > 0:
        print(f"⚠ Covariance gốc không PD -> đã áp dụng shrinkage alpha={alpha_used:.1f}")

    rng = np.random.default_rng(seed)
    z = rng.standard_normal((n_sims, n_assets))
    correlated_shocks = z @ L.T  # Cov(correlated_shocks) ≈ cov_matrix (hoặc bản đã shrink)

    mean_returns = returns.mean().values
    simulated = mean_returns + correlated_shocks
    return pd.DataFrame(simulated, columns=symbols)
