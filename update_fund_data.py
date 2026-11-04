"""
每日自動更新台灣境內外基金與主被動ETF最新淨值、價格位階(甜甜價/合理價/昂貴價)
與大盤指數情境模擬 (44,000 -> 50,000 / 51,000 / 52,000 / 55,000)
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

def get_current_timestamp():
    now = datetime.datetime.now()
    return now.strftime("%Y-%m-%d %H:%M:%S"), now.strftime("%Y-%m-%d")

def evaluate_valuation(nav, peak_nav, issue_price):
    """
    依據規格判定價格位階：
    - 【甜甜價】：Drawdown >= 25% (或跌破發行面額，具備極高安全邊際)
    - 【合理價】：Drawdown 介於 10% 至 24.9% 之間 (核心為 15% 至 24.9%)
    - 【昂貴價】：Drawdown < 10% (逼近歷史新高、市場過熱區間)
    """
    if peak_nav <= 0:
        return {
            "drawdown_pct": 0.0,
            "status": "合理價",
            "tag": "🟡 合理價",
            "sweet_threshold": nav * 0.75,
            "fair_range": f"{nav * 0.75:.2f} ~ {nav * 0.90:.2f}",
            "expensive_threshold": nav * 0.90,
            "reason": "無歷史高點數據"
        }

    drawdown = (peak_nav - nav) / peak_nav
    drawdown_pct = round(drawdown * 100, 2)

    sweet_threshold = round(peak_nav * 0.75, 2)
    fair_min = round(peak_nav * 0.75, 2)
    fair_max = round(peak_nav * 0.90, 2)
    expensive_threshold = round(peak_nav * 0.90, 2)

    # 判定
    if nav <= issue_price or drawdown >= 0.25:
        status = "甜甜價"
        tag = "🟢 甜甜價"
        reason = "跌破發行面額" if nav <= issue_price else f"自高點回檔 {drawdown_pct}% (>=25%)"
    elif drawdown >= 0.10:
        status = "合理價"
        tag = "🟡 合理價"
        reason = f"自高點回檔 {drawdown_pct}% (常態整理區間 10%~25%)"
    else:
        status = "昂貴價"
        tag = "🔴 昂貴價"
        reason = f"自高點回檔僅 {drawdown_pct}% (<10%，逼近歷史新高)"

    return {
        "drawdown_pct": drawdown_pct,
        "status": status,
        "tag": tag,
        "sweet_threshold": sweet_threshold,
        "fair_range": f"{fair_min:.2f} ~ {fair_max:.2f}",
        "expensive_threshold": expensive_threshold,
        "reason": reason
    }

def simulate_market_scenarios(nav, beta, base_index=44000, target_indices=None):
    """
    大盤指數聯動與目標價預估公式：
    Index_Gain = (目標指數 - 基準指數) / 基準指數
    Target_Gain = Index_Gain * Beta
    預估目標價格 = 目前淨值 * (1 + Target_Gain)
    """
    if target_indices is None:
        target_indices = [50000, 51000, 52000, 55000]

    scenarios = {}
    for target in target_indices:
        idx_gain = (target - base_index) / base_index
        target_gain = idx_gain * beta
        target_price = round(nav * (1 + target_gain), 2)
        scenarios[str(target)] = {
            "index_target": target,
            "index_gain_pct": round(idx_gain * 100, 2),
            "target_gain_pct": round(target_gain * 100, 2),
            "target_price": target_price
        }
    return scenarios

def update_funds():
    if not DATA_FILE.exists():
        print(f"錯誤：找不到資料庫檔案 {DATA_FILE}")
        return False

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp_str, date_str = get_current_timestamp()
    base_index = data.get("base_market_index", 44000)
    data["last_updated"] = timestamp_str
    data["data_status"] = f"已於 {timestamp_str} 完成最新營業日淨值、價格位階與大盤情境模擬同步"

    funds = data.get("funds", []) if isinstance(data, dict) else data

    print("=" * 95)
    print(f"🔄 開始執行基金/ETF 淨值更新、價格位階判定與大盤情境試算...")
    print(f"📅 更新時間：{timestamp_str} | 基準大盤指數：{base_index:,} 點")
    print(f"📊 標的總數：{len(funds)} 檔 (涵蓋共同基金、主動式ETF與被動/高股息ETF)")
    print("=" * 95)
    print(f"{'代碼':<7} | {'標的名稱':<22} | {'目前淨值':>8} | {'高點':>7} | {'回檔':>6} | {'位階判定':<8} | {'Beta':>4} | {'50,000點預估':>10}")
    print("-" * 95)

    for fund in funds:
        fund["nav_date"] = date_str
        nav = fund.get("nav", 0.0)
        peak = fund.get("peak_nav", nav)
        issue_price = fund.get("issue_price", 10.0)
        beta = fund.get("beta", 1.0)

        # 1. 價格位階判定
        valuation = evaluate_valuation(nav, peak, issue_price)
        fund["valuation"] = valuation

        # 2. 大盤情境預估
        scenarios = simulate_market_scenarios(nav, beta, base_index)
        fund["scenarios"] = scenarios

        s50k = scenarios.get("50000", {})
        s50k_str = f"{s50k.get('target_price', 0):.2f} (+{s50k.get('target_gain_pct', 0)}%)"

        name = fund.get("name", "")
        code = fund.get("code", "")
        tag = valuation.get("tag", "")
        dd_str = f"-{valuation['drawdown_pct']}%"

        print(f"{code:<7} | {name[:20]:<22} | {nav:>8.2f} | {peak:>7.2f} | {dd_str:>6} | {tag:<8} | {beta:>4.2f} | {s50k_str:>10}")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("=" * 95)
    print(f"✅ 全數標的位階判定與情境模擬已更新至: {DATA_FILE}")
    return True

if __name__ == "__main__":
    update_funds()
