# Data Audit — Alpha Factor Research (VN30)

Cập nhật sau khi chạy pipeline trên universe mở rộng **30 mã VN30** (trước đó: 10 mã, Ngày 4-5). Các mục 1-5 là audit gốc; mục 6 là kết quả thực tế + phát hiện mới sau khi chạy trên 30 mã.

---

## 1. Survivorship Bias — Universe VN30 hiện tại

Universe (`VN30_UNIVERSE` trong `src/data_loader.py`) lấy từ danh sách VN30 **hiện tại**:

- **Mã được bổ sung gần đây:** MCH, TCX
- **Mã từng bị loại khỏi rổ:** VCK, PLX, TPB, và trước đó là DGC

**Rủi ro:** dùng thành phần rổ hiện tại để tải lịch sử giá nghĩa là các mã từng "rớt hạng" không có mặt trong mẫu — IC/backtest có xu hướng bị thổi phồng nhẹ so với thực tế nếu chiến lược chạy live tại các thời điểm quá khứ. Chưa khắc phục được trong lần chạy này (chưa có point-in-time universe).

---

## 2. Selection Bias — Cổ phiếu outlier

Ở universe 10 mã ban đầu, loại VRE khỏi rổ làm mean IC của factor Momentum đổi dấu hoàn toàn (từ -0.045 về +0.004). Giả thuyết đặt ra khi đó: **kết quả trên universe nhỏ dễ bị 1 mã chi phối.**

**→ Đã xác nhận bằng kết quả thực tế (xem mục 6):** khi mở rộng lên 30 mã, Alpha C — chiến lược mạnh nhất ở 10 mã (Mean IC +0.060, t=2.60) — **đảo dấu hoàn toàn** thành Mean IC -0.009 (t=-0.65), mất toàn bộ ý nghĩa thống kê. Đây là bằng chứng khá thuyết phục rằng kết luận trước đó phần lớn là overfit vào sample nhỏ, không phải hiệu ứng thị trường thật.

---

## 3. Data Quality Check — Biến động giá bất thường (kết quả thực tế)

Chạy `find_extreme_moves(price_df, threshold=0.07)` trên 30 mã (2024-01-01 → 2025-12-31):

- **Tổng số phiên biến động > 7%: 28**
- **MCH chiếm 10/28 (≈36%)** phiên biến động cực đoan, với biên độ lên tới ±14% (VD: -14.1% ngày 2025-04-08, +13.2% ngày 2025-04-10) — vượt xa biên độ trần/sàn chuẩn 7% của HOSE, gợi ý MCH có thể thuộc nhóm biên độ khác.
- BSR cũng xuất hiện với biến động sát ngưỡng (~8%).
- Lý do cho các phiên biến động này là vì 2 mã trên có sự thay đổi sàn (từ sàn Upcom có biên độ 15% sang sàn HOSE có biên độ 7%).

**Khuyến nghị:** Cần phải chỉnh sửa, có thể bỏ qua mã MCH hoặc cách khác.

---

## 4. Warm-up / Look-back Bias — N Obs không đồng nhất giữa factor

Sau khi align common observations: **235 quan sát chung** (so với 248 ở universe 10 mã) — giảm nhẹ, chủ yếu do TCX (mã mới niêm yết) rút ngắn giai đoạn có đủ dữ liệu cho toàn bộ 30 mã cùng lúc.

---

## 5. Multiple Testing Bias — So sánh nhiều factor cùng lúc (kết quả thực tế)

Chạy `multiple_testing_correction()` trên 12 factor (α=0.05, Bonferroni threshold=0.0042):

| Factor             | p-value | Raw sig. | Bonferroni | BH/FDR |
| ------------------ | ------- | -------- | ---------- | ------ |
| AlphaB_TSRankVol   | 0.0089  | ✓        | ✗          | ✓      |
| ZLEMA_Reversion    | 0.0108  | ✓        | ✗          | ✓      |
| VolumeRatio        | 0.0112  | ✓        | ✗          | ✓      |
| AlphaD5_SoftRegime | 0.0881  | ✗        | ✗          | ✗      |
| AlphaA_RetCorr     | 0.1059  | ✗        | ✗          | ✗      |
| (6 factor còn lại) | > 0.39  | ✗        | ✗          | ✗      |

**Không có factor nào vượt qua Bonferroni** với 12 test đồng thời — kể cả 3 factor có ý nghĩa ở mức raw/FDR. Đây là kết quả bảo thủ hợp lý vì số lượng test tăng từ 6 (Ngày 5) lên 12 (thêm universe rộng hơn không giảm số factor, chỉ tăng độ tin cậy dữ liệu).

**Lưu ý quan trọng:** 3 factor có ý nghĩa ở FDR (AlphaB, ZLEMA, VolumeRatio) **chưa từng được nêu bật** trong nghiên cứu Ngày 4 (khi đó chỉ mô tả định tính "Mean IC rất nhỏ, chưa bác bỏ H0"). Việc chúng nổi lên có ý nghĩa ở universe rộng hơn cần được xác nhận thêm bằng out-of-sample test trước khi kết luận đây là tín hiệu thật, không phải một dạng false discovery khác theo chiều ngược lại.

---

## 6. Kết luận tổng hợp: So sánh 10 mã vs 30 mã

| Factor           | Mean IC (10 mã)           | Mean IC (30 mã)          | Thay đổi             |
| ---------------- | ------------------------- | ------------------------ | -------------------- |
| AlphaC_TrendCond | +0.0603 (sig. FDR)        | -0.0094 (không sig.)     | Đảo dấu, mất ý nghĩa |
| Ensemble_C_D4    | +0.0716 (sig. Bonferroni) | -0.0094 (không sig.)     | Đảo dấu, mất ý nghĩa |
| Ensemble_C_D5    | +0.0725 (sig. Bonferroni) | -0.0130 (không sig.)     | Đảo dấu, mất ý nghĩa |
| VolumeRatio      | (chưa test riêng)         | +0.0329 (sig. raw & FDR) | Factor mới nổi bật   |
| AlphaB_TSRankVol | Mean IC nhỏ (định tính)   | -0.0360 (sig. raw & FDR) | Nổi lên có ý nghĩa   |
| ZLEMA_Reversion  | Mean IC nhỏ (định tính)   | -0.0385 (sig. raw & FDR) | Nổi lên có ý nghĩa   |

**Diễn giải:** kết quả này là một minh hoạ thực tế rõ ràng cho rủi ro overfitting trên sample nhỏ đã cảnh báo ở mục 2 — kết luận "Alpha C là chiến lược tốt nhất" từ nghiên cứu 10 mã **không replicate được** khi mở rộng universe, và ngược lại các factor từng bị đánh giá thấp lại nổi lên có ý nghĩa. Bài học quy trình: **không nên chốt kết luận về một factor chỉ dựa trên một universe/giai đoạn duy nhất** — cần ít nhất một bước xác nhận trên dữ liệu độc lập trước khi coi là phát hiện đáng tin.

## Việc cần làm tiếp theo

1. Tìm cách xử lý MCH / BSR trước khi dùng cho bất kỳ phân tích trend-based nào.
2. Out-of-sample test cho VolumeRatio, AlphaB_TSRankVol, ZLEMA_Reversion (chia theo thời gian, không chỉ theo universe).
3. Xem xét loại bỏ ngưỡng cứng 5% trong Alpha C — khả năng cao đây là tham số bị overfit vào universe 10 mã ban đầu.
4. Đã sửa 2 vấn đề kỹ thuật trong code: (a) `pct_change()` dùng `fill_method=None` để tránh forward-fill ẩn NaN thành return giả 0%; (b) `calc_ic()` bỏ qua các ngày factor/forward-return constant (tránh warning "input array is constant" và IC giả).
