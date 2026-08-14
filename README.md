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

_(Kết quả dưới đây là từ nghiên cứu ban đầu trên universe 10 mã — Ngày 5, cùng 248 quan sát chung. Cần chạy lại trên universe 30 mã để cập nhật bảng này — xem "Cách chạy".)_

| Metric              | Alpha C | Ensemble C+D4 | Ensemble C+D5 |
| ------------------- | ------- | ------------- | ------------- |
| Mean IC             | 0.0603  | 0.0716        | 0.0725        |
| IC IR               | 0.1648  | 0.2266        | 0.2072        |
| t-stat              | 2.596   | 3.569         | 3.263         |
| Hit Rate            | 0.5806  | 0.5766        | 0.5484        |
| Sig. sau Bonferroni | ✗       | ✓             | ✓             |
| Sig. sau FDR        | ✓       | ✓             | ✓             |

Sharpe Ratio / Max Drawdown / Annualized Return: **chưa tính** — hiện tại mới dừng ở phân tích IC (dự báo), chưa có backtest return thực tế (chưa tính transaction cost, sizing, slippage).

## Hạn chế & Rủi ro

- **Chưa backtest return thực:** toàn bộ đánh giá hiện tại dựa trên IC (khả năng dự báo), chưa mô phỏng P&L có transaction cost/slippage.
- **Survivorship bias:** universe lấy theo VN30 hiện tại, không phản ánh đúng thành phần rổ tại các thời điểm quá khứ trong giai đoạn test. Chi tiết: `reports/data_audit.md`.
- **Overlapping observations:** forward return dùng N_FWD=5 ngày gối lên nhau, có thể làm t-stat bị thổi phồng nếu tính theo công thức IID chuẩn (chưa áp dụng Newey-West).
- **Ensemble weight cố định 50/50:** chưa test out-of-sample, có rủi ro overfit nhẹ vào giai đoạn 2025 đang dùng để đánh giá.
- **Kết quả bảng trên là từ universe 10 mã (Ngày 5):** cần chạy lại toàn bộ pipeline trên universe 30 mã để xác nhận kết luận còn giữ nguyên.

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
