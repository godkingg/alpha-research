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

---

## 7. Deflated Sharpe Ratio (Ngày 8) — kiểm định độc lập cho kết luận ở mục 2 và 6

Coi chuỗi IC hàng ngày của mỗi factor như "return" của một chiến lược, áp dụng DSR
(Bailey & López de Prado, 2014) với **N_trials=12** (đúng số factor đã test trong project),
tính trên cả 2 universe. Implementation: `src/deflated_sharpe.py`.

### 7.1 Universe 10 mã (N_obs=201 common)

| Factor             | Sharpe thô (IC IR) | t-stat | DSR Z-score | **DSR**    |
| ------------------ | ------------------ | ------ | ----------- | ---------- |
| Ensemble_C_D4      | 0.2182             | 3.0938 | 0.3300      | **0.6293** |
| AlphaC_TrendCond   | 0.1851             | 2.6241 | -0.1403     | **0.4442** |
| Ensemble_C_D5      | 0.1642             | 2.3273 | -0.4395     | 0.3302     |
| AlphaA_RetCorr     | 0.1112             | 1.5762 | -1.1927     | 0.1165     |
| (8 factor còn lại) | —                  | —      | —           | < 0.06     |

**Phát hiện quan trọng:** t-stat=2.6241 của AlphaC_TrendCond trông "significant" theo chuẩn thống kê cổ điển (p<0.01), nhưng **DSR chỉ 0.4442 — dưới mức 0.5**, tức thấp hơn cả xác suất tung đồng xu. Ngay cả Ensemble_C_D4 — factor có DSR cao nhất — cũng chỉ đạt 0.6293, thấp hơn nhiều so với ngưỡng thường dùng để tự tin (DSR > 0.95).

**→ DSR đã cảnh báo được từ universe 10 mã, TRƯỚC KHI mở rộng lên 30 mã**, rằng độ tin cậy của AlphaC_TrendCond là mong manh — không cần đợi kết quả đảo dấu ở 30 mã mới biết. Đây là bằng chứng cho thấy quy trình đánh giá factor trước đây (chỉ dùng t-stat + Bonferroni/FDR) đã đánh giá quá lạc quan.

### 7.2 Universe 30 mã (N_obs=235 common)

| Factor             | Sharpe thô (IC IR) | t-stat  | DSR Z-score | **DSR**    |
| ------------------ | ------------------ | ------- | ----------- | ---------- |
| VolumeRatio        | 0.1652             | 2.5318  | -0.1097     | **0.4563** |
| AlphaA_RetCorr     | 0.1053             | 1.6147  | -1.0215     | 0.1535     |
| AlphaC_TrendCond   | -0.0389            | -0.5964 | -3.2304     | 0.0006     |
| Ensemble_C_D4      | -0.0430            | -0.6592 | -3.3137     | 0.0005     |
| Ensemble_C_D5      | -0.0527            | -0.8079 | -3.4421     | 0.0003     |
| (7 factor còn lại) | —                  | —       | —           | ≤ 0.03     |

**Xác nhận:** AlphaC_TrendCond và cả 2 Ensemble sụp đổ hoàn toàn về DSR (~0.0003-0.0006, gần như chắc chắn không có skill thật). VolumeRatio — factor tốt nhất ở 30 mã theo t-stat — cũng chỉ đạt DSR 0.4563, **vẫn dưới 0.5**.

**Kết luận xuyên suốt cả 2 universe: chưa có factor nào trong 12 factor đạt DSR đủ thuyết phục (>0.5, càng chưa đạt >0.95) để tự tin về skill thật.** Đây là câu chuyện nhất quán hơn nhiều so với khi chỉ nhìn t-stat — t-stat "khen" các factor khác nhau ở mỗi universe (AlphaC ở 10 mã, VolumeRatio ở 30 mã), trong khi DSR nhất quán nói: "chưa đủ bằng chứng ở cả hai".

### 7.3 Giả thuyết cho hiện tượng "factor đổi vai" giữa 2 universe

Ghi chú từ quá trình phân tích: các factor vô nghĩa ở 10 mã lại có ý nghĩa hơn ở 30 mã (và ngược lại), nhiều khả năng do nhóm cổ phiếu vốn hóa lớn mới được thêm vào ở 30 mã (VIC, VHM, VRE, VPL) có xu hướng hút dòng tiền mạnh, chi phối cross-section khác hẳn so với universe 10 mã ban đầu (vốn chỉ có 1 mã thuộc nhóm này là VRE). **Đây là giả thuyết, chưa kiểm định** — cần thử loại nhóm VIC-Group khỏi universe 30 mã và tính lại DSR để xác nhận.

### 7.4 Giới hạn của DSR trong phân tích này

- `SR_0*` được ước lượng từ **chính 12 Sharpe quan sát được trong cùng universe** (self-referential) — đây là cách tiếp cận thực dụng khi không biết phân phối null thật, nhưng có nghĩa DSR ở đây **chỉ bảo vệ khỏi việc chọn factor tốt nhất trong 12 factor của CÙNG 1 universe**, không bảo vệ khỏi việc chọn universe làm cả nhóm factor trông đẹp hơn (loại bias này vẫn cần out-of-sample theo universe, như đã làm thủ công ở Ngày 7).
- Kurtosis dùng trong công thức là kurtosis kiểu Pearson (normal=3); `pandas.Series.kurtosis()` trả về excess kurtosis nên cần +3 trước khi đưa vào công thức — đã xử lý đúng trong `src/deflated_sharpe.py`.
