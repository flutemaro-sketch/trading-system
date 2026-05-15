"""
GUI 初期化テスト（表示なし）
- MainWindow と BoardUnit の初期化が成功するか確認
- Tkinter が利用可能な環境での動作確認
"""
import sys
from pathlib import Path
from queue import Queue

# プロジェクトルートを Python path に追加
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import tkinter as tk

    print("=" * 70)
    print("GUI Initialization Test")
    print("=" * 70)

    # Tkinter が利用可能か確認
    print("Creating root window...")
    root = tk.Tk()
    root.withdraw()  # ウィンドウを非表示

    print("OK: Tkinter is available")

    # MainWindow 初期化テスト
    print("")
    print("Initializing MainWindow...")
    from board_monitor.gui.main_window import MainWindow

    data_queue = Queue()
    main_window = MainWindow(root, data_queue, kabu_client=None)

    print("OK: MainWindow initialized successfully")
    print(f"  - {len(main_window.units)} board units created")

    # Unit キー確認
    print("")
    print("Unit structure:")
    unit_keys = sorted(main_window.units.keys())
    for i, key in enumerate(unit_keys, start=1):
        unit = main_window.units[key]
        print(f"  {i:2d}. {key}: {unit.__class__.__name__}")

    # BoardUnit 데이터 업데이트 테스트
    print("")
    print("Testing BoardUnit.update_data()...")

    test_board_data = {
        "symbol": "9984",
        "time": "14:59:59",
        "last_price": 4510.0,
        "change_pct": 0.2222,
        "previous_close": 4500.0,
        "open": 4500.5,
        "high": 4515.0,
        "low": 4495.0,
        "volume": 50000000,
        "vwap": 4507.5,
        "time_open": "09:00:00",
        "time_high": "14:30:00",
        "time_low": "10:15:00",
        "asks": [
            {"price": 4510.0 + i * 0.1, "volume": 100 - i * 5} for i in range(10)
        ],
        "asks_sign": ["OVER"] + [""] * 9,
        "bids": [
            {"price": 4509.9 - i * 0.1, "volume": 200 - i * 10} for i in range(10)
        ],
        "bids_sign": ["", "", "UNDER"] + [""] * 7,
    }

    unit_1 = main_window.units["unit_1"]
    unit_1.set_a_slot(0, "9984", "ソフトバンク")
    unit_1.push_board_data("9984", test_board_data)

    print("OK: BoardUnit push_board_data() executed successfully")
    print(f"  - Price label shows: {unit_1.price_label.cget('text')}")
    print(f"  - Change label shows: {unit_1.change_label.cget('text')}")

    # クリーンアップ
    root.destroy()

    print("")
    print("=" * 70)
    print("ALL TESTS PASSED!")
    print("=" * 70)

except ImportError as e:
    print(f"ERROR: Import failed - {e}")
    print("This test requires a GUI-enabled environment (Tkinter)")
    sys.exit(1)
except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()
    sys.exit(1)
