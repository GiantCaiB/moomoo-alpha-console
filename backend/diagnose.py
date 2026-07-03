"""Diagnose moomoo OpenD connection and account queries."""
import moomoo as ft

ctx = ft.OpenSecTradeContext(filter_trdmarket=ft.TrdMarket.US, host='127.0.0.1', port=11111)
ctx.start()

print("=== get_acc_list ===")
ret, acc_list = ctx.get_acc_list()
print(f"ret={ret} (RET_OK={ft.RET_OK}, RET_ERROR={ft.RET_ERROR})")
if ret == ft.RET_OK and acc_list is not None and len(acc_list) > 0:
    print(f"Found {len(acc_list)} accounts:")
    print(acc_list.to_string())
    print()

    row0 = acc_list.iloc[0]
    acc_id = row0.get('acc_id')
    trd_env_str = row0.get('trd_env')
    print(f"First account: acc_id={acc_id}, trd_env={trd_env_str}")

    # Try different variants of accinfo_query
    variants = [
        ("SIMULATE, acc_id=acc_id", ft.TrdEnv.SIMULATE, acc_id),
        ("REAL, acc_id=acc_id", ft.TrdEnv.REAL, acc_id),
        ("SIMULATE, acc_id=0", ft.TrdEnv.SIMULATE, 0),
        ("REAL, acc_id=0", ft.TrdEnv.REAL, 0),
        ("SIMULATE, acc_index=0", ft.TrdEnv.SIMULATE, None),
        ("REAL, acc_index=0", ft.TrdEnv.REAL, None),
    ]
    for label, trd_env, aid in variants:
        print(f"\n=== accinfo_query({label}) ===")
        kwargs = dict(trd_env=trd_env, currency=ft.Currency.USD)
        if aid is not None:
            kwargs['acc_id'] = aid
        else:
            kwargs['acc_index'] = 0
        try:
            ret2, info = ctx.accinfo_query(**kwargs)
            print(f"ret={ret2}")
            if ret2 == ft.RET_OK and info is not None and len(info) > 0:
                r = info.iloc[0]
                for col in info.columns:
                    print(f"  {col}: {r.get(col)}")
            else:
                print("  FAILED or empty")
                print(f"  info type={type(info)}")
                if info is not None:
                    print(f"  info len={len(info)}")
        except Exception as e:
            print(f"  EXCEPTION: {e}")

else:
    print("No accounts found or error")

ctx.close()
print("\n=== Done ===")
