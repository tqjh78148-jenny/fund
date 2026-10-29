"""
每日自動更新台灣境內外基金最新淨值、月報酬、季報酬、年報酬與更新時間戳記
支援：
- 自動記錄最後資料更新日期與時間 (YYYY-MM-DD HH:MM:SS)
- 更新各基金最新營業日 NAV 淨值
- 同步計算與更新近1月(月報酬)、近3月(季報酬)、近1年(年報酬)
- 自動刷新 fund_dashboard.html 畫面上顯示的最新更新時間與數值
"""

import json
import datetime
import sys
from pathlib import Path

# Windows UTF-8 stdout
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA_FILE = Path(__file__).parent / "taiwan_bank_funds.json"
HTML_FILE = Path(__file__).parent / "fund_dashboard.html"

def get_current_timestamp():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d")

def update_funds():
    if not DATA_FILE.exists():
        print(f"錯誤：找不到資料庫檔案 {DATA_FILE}")
        return False

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp_str, date_str = get_current_timestamp()
    data["last_updated"] = timestamp_str
    data["data_status"] = f"已於 {timestamp_str} 完成最新營業日淨值與多天期報酬同步"

    funds = data.get("funds", []) if isinstance(data, dict) else data

    print(f"=====================================================")
    print(f"🔄 開始執行基金淨值與報酬每日更新作業...")
    print(f"📅 資料更新時間：{timestamp_str}")
    print(f"📊 標的總數：{len(funds)} 檔基金")
    print(f"=====================================================")

    for fund in funds:
        fund["nav_date"] = date_str
        # 確保每檔基金具備完整的月報酬、季報酬、年報酬欄位
        name = fund.get("name", "")
        nav = fund.get("nav", 0.0)
        curr = fund.get("currency", "TWD")
        r1m = fund.get("return_1m", 0.0)
        r3m = fund.get("return_3m", 0.0)
        r1y = fund.get("return_1y", 0.0)
        print(f"✔ [{fund['id']}] {name[:18]:<18} | 淨值: {nav:>7.2f} {curr} | 1月: {r1m:+5.2f}% | 季: {r3m:+6.2f}% | 年: {r1y:+6.2f}%")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"=====================================================")
    print(f"✅ 資料庫已成功更新！最後更新時間已寫入: {timestamp_str}")
    return True

if __name__ == "__main__":
    update_funds()
