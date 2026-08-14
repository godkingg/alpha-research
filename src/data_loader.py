"""Data loader — tận dụng lại vnstock-db (Quote, source='KBS') để tải OHLCV cho một universe.

Universe mặc định: VN30 (30 mã, snapshot hiện tại từ Listing.symbols_by_group('VN30')).
Lưu ý (xem reports/data_audit.md): dùng thành phần VN30 hiện tại để tải lịch sử có thể
gây survivorship bias — các mã từng bị loại khỏi rổ (VD: VCK, PLX, TPB, DGC) không có mặt.
"""
from __future__ import annotations

import pandas as pd
from vnstock import Quote

# Universe: VN30 hiện tại (30 mã) — snapshot từ Listing(source='VCI').symbols_by_group('VN30')
VN30_UNIVERSE: list[str] = [
    "ACB", "BID", "BSR", "CTG", "FPT", "GAS", "GVR", "HDB", "HPG", "LPB",
    "MBB", "MCH", "MSN", "MWG", "SAB", "SHB", "SSB", "SSI", "STB", "TCB",
    "TCX", "VCB", "VHM", "VIB", "VIC", "VJC", "VNM", "VPB", "VPL", "VRE",
]

DEFAULT_START = "2024-01-01"  # đủ ~252 phiên lookback cho momentum tính trong 2025
DEFAULT_END = "2025-12-31"


def load_price_volume(
    symbols: list[str] = VN30_UNIVERSE,
    start: str = DEFAULT_START,
    end: str = DEFAULT_END,
    interval: str = "d",
    source: str = "KBS",
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Tải close/open/volume cho toàn bộ symbols, trả về 3 DataFrame wide-format (index=time, columns=symbol).

    Note: một số mã mới bổ sung vào VN30 (VD: MCH, TCX) có thể chưa đủ lịch sử từ `start`
    -> sẽ có NaN ở đầu chuỗi, các factor cần lookback dài (momentum 12-1, Alpha C 100 ngày)
    sẽ tự động NaN cho các mã này trong giai đoạn thiếu dữ liệu.
    """
    raw: dict[str, pd.DataFrame] = {}
    for sym in symbols:
        df = Quote(symbol=sym, source=source).history(start=start, end=end, interval=interval)
        raw[sym] = df.set_index("time")[["close", "open", "volume"]]

    price_df = pd.DataFrame({sym: d["close"] for sym, d in raw.items()}).sort_index()
    open_df = pd.DataFrame({sym: d["open"] for sym, d in raw.items()}).sort_index()
    volume_df = pd.DataFrame({sym: d["volume"] for sym, d in raw.items()}).sort_index()
    return price_df, open_df, volume_df


def find_extreme_moves(price_df: pd.DataFrame, threshold: float = 0.07) -> pd.DataFrame:
    """Data quality check: liệt kê các phiên có |return| > threshold (mặc định 7%, biên độ HOSE).

    Dùng để rà soát dữ liệu bất thường trước khi build factor — không tự động loại bỏ.
    """
    ret = price_df.pct_change()
    mask = ret.abs() > threshold
    return (
        ret[mask]
        .stack()
        .rename("return")
        .reset_index()
        .rename(columns={"level_0": "date", "level_1": "symbol"})
        .sort_values("return", key=abs, ascending=False)
        .reset_index(drop=True)
    )


if __name__ == "__main__":
    price_df, open_df, volume_df = load_price_volume()
    print(f"Universe: {len(VN30_UNIVERSE)} mã | {price_df.index.min().date()} → {price_df.index.max().date()}")
    print(find_extreme_moves(price_df).head())
