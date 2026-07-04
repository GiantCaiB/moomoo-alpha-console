"""Verify time_key type."""
import moomoo as ft
ctx = ft.OpenQuoteContext(host='127.0.0.1', port=11111)
try:
    ret, data, page_key = ctx.request_history_kline('US.SPY', start='2025-01-01', end='2026-07-04', ktype=ft.KLType.K_DAY, max_count=5)
    row = data.iloc[0]
    tk = row.get("time_key")
    print(f"time_key value={tk}, type={type(tk)}")
    if hasattr(tk, 'strftime'):
        print("has strftime, date:", tk.date())
    else:
        print("no strftime, isoformat:", tk[:10])
except Exception as e:
    print(f"Error: {e}")
finally:
    ctx.close()
