# Alpha Factor Research

## Mục tiêu

Xây dựng và kiểm định một tập hợp alpha factor (momentum, mean-reversion, volume, RSI-regime) trên nhóm cổ phiếu VN30, kiểm tra xem factor nào có sức mạnh dự báo (Information Coefficient) đáng tin cậy sau khi hiệu chỉnh cho multiple testing, và liệu kết hợp (ensemble) các factor có cải thiện độ ổn định của tín hiệu hay không.

## Dataset

- **Nguồn:** vnstock (`Quote(source="KBS")`)
- **Khoảng thời gian:** 2024-01-01 → 2025-12-31 (2024 dùng làm warm-up cho các factor cần lookback dài, VD momentum 12-1 và Alpha C 100 ngày)
- **Universe:** 30 mã VN30 hiện tại (`VN30_UNIVERSE` trong `src/data_loader.py`) — mở rộng từ universe 10 mã ban đầu (Ngày 4-5)
- **Tần suất:** dữ liệu ngày (`interval="d"`)
- **Xem thêm rủi ro dữ liệu (survivorship bias, outlier, warm-up bias):** [`reports/data_audit.md`](reports/data_audit.md)

## Phương pháp

```
data_loader.py          →   features.py              →   ic_analysis.py
(load OHLCV, universe        (12 alpha factor:              (Spearman IC theo ngày,
 30 mã, data quality           Ngày 4: 7 factor gốc            IC IR, t-stat, hit rate,
 check biến động > 7%)         Ngày 5: RSI-regime +            common-obs alignment,
                                ensemble với Alpha C)           Bonferroni/FDR correction)

                         simulate_correlated_returns.py
                         (covariance matrix → PSD/PD check →
                          shrinkage nếu cần → Cholesky →
                          Monte Carlo return có tương quan, Ngày 6)
```

**Danh sách factor (12 factor, `src/features.py`):**

| Nhóm   | Factor                 | Ý tưởng                                                              |
| ------ | ---------------------- | -------------------------------------------------------------------- |
| Ngày 4 | `Momentum_12_1`        | Return 12 tháng, bỏ tháng gần nhất                                   |
| Ngày 4 | `MeanReversion_Z`      | Z-score return 5 ngày so với phân phối 20 phiên                      |
| Ngày 4 | `VolumeRatio`          | Volume hôm nay / trung bình 20 phiên                                 |
| Ngày 4 | `AlphaA_RetCorr`       | Đảo chiều return 3 ngày × đồng biến open-volume                      |
| Ngày 4 | `AlphaB_TSRankVol`     | Vị trí giá + độ cong giá + bất thường volume                         |
| Ngày 4 | `AlphaC_TrendCond`     | Ternary: sideway → khoảng cách đáy 100d; trend → momentum 3d đảo dấu |
| Ngày 4 | `ZLEMA_Reversion`      | Lệch giá so với ZLEMA-20                                             |
| Ngày 5 | `AlphaD_NoRegime`      | Trend-following thuần theo slope RSI                                 |
| Ngày 5 | `AlphaD4_RegimeSwitch` | Slope RSI + override reversal khi RSI chạm cực trị 100d              |
| Ngày 5 | `AlphaD5_SoftRegime`   | Blend liên tục trend-following/mean-reversion theo percentile RSI    |
| Ngày 5 | `Ensemble_C_D4`        | 50/50 Alpha C (rank-scaled) + Alpha D4                               |
| Ngày 5 | `Ensemble_C_D5`        | 50/50 Alpha C (rank-scaled) + Alpha D5                               |

## Kết quả chính

Đã chạy lại trên universe **30 mã VN30**, 2024-01-01 → 2025-12-31, 235 quan sát chung (common obs). Kết quả **đảo ngược hoàn toàn** so với nghiên cứu ban đầu trên 10 mã (Ngày 5) — xem phân tích chi tiết ở [`reports/data_audit.md`](reports/data_audit.md).

| Metric                    | AlphaC_TrendCond | Ensemble_C_D4 | Ensemble_C_D5 | VolumeRatio | AlphaB_TSRankVol | ZLEMA_Reversion |
| ------------------------- | ---------------- | ------------- | ------------- | ----------- | ---------------- | --------------- |
| Mean IC                   | -0.0094          | -0.0094       | -0.0130       | +0.0329     | -0.0360          | -0.0385         |
| IC IR                     | -0.0423          | -0.0444       | -0.0559       | +0.1656     | -0.1707          | -0.1662         |
| t-stat                    | -0.648           | -0.680        | -0.856        | 2.538       | -2.617           | -2.548          |
| Hit Rate                  | 0.4766           | 0.5064        | 0.4511        | 0.6000      | 0.4340           | 0.4128          |
| Sig. raw (α=0.05)         | ✗                | ✗             | ✗             | ✓           | ✓                | ✓               |
| Sig. Bonferroni (12 test) | ✗                | ✗             | ✗             | ✗           | ✗                | ✗               |
| Sig. FDR                  | ✗                | ✗             | ✗             | ✓           | ✓                | ✓               |

**Diễn giải quan trọng:** Alpha C và 2 chiến lược Ensemble — vốn là kết quả chính của nghiên cứu Ngày 5 — **mất toàn bộ ý nghĩa thống kê và đảo dấu** khi mở rộng universe. Đây là dấu hiệu overfit vào sample 10 mã ban đầu (chi tiết: mục 6, `data_audit.md`). Ngược lại, **VolumeRatio, AlphaB_TSRankVol, ZLEMA_Reversion** nổi lên có ý nghĩa ở mức raw p-value và FDR (nhưng chưa vượt Bonferroni) — cần out-of-sample test trước khi tin tưởng đây là tín hiệu thật.

Sharpe Ratio / Max Drawdown / Annualized Return: **chưa tính** — hiện tại mới dừng ở phân tích IC (dự báo), chưa có backtest return thực tế (chưa tính transaction cost, sizing, slippage).

## Hạn chế & Rủi ro

- **Chưa backtest return thực:** toàn bộ đánh giá hiện tại dựa trên IC (khả năng dự báo), chưa mô phỏng P&L có transaction cost/slippage.
- **Survivorship bias:** universe lấy theo VN30 hiện tại, không phản ánh đúng thành phần rổ tại các thời điểm quá khứ trong giai đoạn test. Chi tiết: `reports/data_audit.md`.
- **Overlapping observations:** forward return dùng N_FWD=5 ngày gối lên nhau, có thể làm t-stat bị thổi phồng nếu tính theo công thức IID chuẩn (chưa áp dụng Newey-West).
- **Ensemble weight cố định 50/50:** thiết kế cho Alpha C — hiện Alpha C đã mất ý nghĩa trên 30 mã nên cấu trúc ensemble này cần xem lại từ đầu, không chỉ là vấn đề tinh chỉnh trọng số.
- **Dữ liệu MCH bất thường:** 10/28 phiên biến động >7% thuộc về MCH (biên độ tới ±14%), có thể ảnh hưởng đến các factor trend-based. Chưa loại trừ khỏi phân tích — xem mục 3, `data_audit.md`.
- **VolumeRatio/AlphaB/ZLEMA mới nổi lên có ý nghĩa (sig. FDR, chưa Bonferroni):** chưa qua out-of-sample test, chưa nên coi là kết luận cuối cùng — kết quả trên 10 mã cho thấy sự đảo ngược hoàn toàn giữa các lần thử universe khác nhau là hoàn toàn có thể xảy ra.

## Cách chạy

```bash
pip install -r requirements.txt
```

```python
from src.data_loader import load_price_volume, find_extreme_moves, VN30_UNIVERSE
from src.features import build_all_factors
from src.ic_analysis import forward_return, calc_ic, ic_summary_table, align_common_obs, multiple_testing_correction
from src.simulate_correlated_returns import simulate_correlated_returns

# 1. Load dữ liệu (mặc định: 30 mã VN30, 2024-01-01 → 2025-12-31)
price_df, open_df, volume_df = load_price_volume()
find_extreme_moves(price_df)  # data quality check

# 2. Build toàn bộ factor
factors = build_all_factors(price_df, open_df, volume_df)

# 3. IC analysis
fwd_ret = forward_return(price_df, n_fwd=5)
ic_series = {name: calc_ic(f, fwd_ret) for name, f in factors.items()}
ic_series_common = align_common_obs(ic_series)
summary = ic_summary_table(ic_series_common)
correction = multiple_testing_correction(summary)

# 4. (Tuỳ chọn) Monte Carlo return có tương quan, dùng cho stress-test / risk sizing
returns = price_df.pct_change().dropna()
simulated = simulate_correlated_returns(returns, n_sims=10_000)
```

Notebook nghiên cứu gốc (Ngày 3-6, exploratory) nằm ở `notebooks/`.
