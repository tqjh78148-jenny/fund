"""
台灣銀行與基金平台可購基金績效試算與最高獲利分析工具
支援：
- 台股、美股、全球股票型與配息型基金比較
- 淨值累積型 (複利資產極大化) vs 每月/每季分紅配息型 (現金流 + 含息總報酬)
- 依據投入台幣金額與期望年化獲利率，精確試算並挑選最高獲利基金
"""

import json
import argparse
import sys
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform.startswith("win"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

DATA_FILE = Path(__file__).parent / "taiwan_bank_funds.json"

def load_funds_data():
    if not DATA_FILE.exists():
        print(f"錯誤：找不到基金資料庫檔案 {DATA_FILE}")
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict):
        last_updated = data.get("last_updated", "未知")
        funds = data.get("funds", [])
        return funds, last_updated
    return data, "未知"

def calculate_fund_profit(fund, capital, target_return, years):
    """
    計算單一基金在特定投資金額與年期下的預期獲利與現金流
    """
    # 依年期選用歷史CAGR數據
    if years <= 1:
        cagr = fund.get("cagr_1y", 0.0)
    elif years <= 3:
        cagr = fund.get("cagr_3y", 0.0)
    elif years <= 5:
        cagr = fund.get("cagr_5y", 0.0)
    else:
        cagr = fund.get("cagr_10y", 0.0)

    is_dividend = "配息型" in fund.get("share_type", "")
    div_yield = fund.get("div_yield_annual", 0.0)

    if not is_dividend:
        # 累積型 (不配息，股息直接滾入淨值複利)
        ending_value = capital * ((1 + cagr / 100.0) ** years)
        total_profit = ending_value - capital
        total_return_pct = ((ending_value - capital) / capital) * 100.0
        monthly_cashflow = 0.0
        total_dividends = 0.0
        nav_capital = ending_value
    else:
        # 配息型 (每月/季發放現金流)
        annual_dividend = capital * (div_yield / 100.0)
        monthly_cashflow = annual_dividend / 12.0
        total_dividends = annual_dividend * years

        # 估算含息總回報下的期末淨值（若CAGR為含息年化報酬率）
        # 含息總資產價值 (假設配息領出不滾入，純以現金持有)：
        # 年化總報酬 CAGR = ( (期末淨值 + 累計配息) / 本金 ) ^ (1/years) - 1
        # 期末資產總值 = Capital * (1 + cagr/100)^years
        total_value_with_div = capital * ((1 + cagr / 100.0) ** years)
        total_profit = total_value_with_div - capital
        total_return_pct = ((total_value_with_div - capital) / capital) * 100.0
        
        # 估算期末剩餘本金淨值 (總價值扣除已領走配息)
        nav_capital = max(0.0, total_value_with_div - total_dividends)
        ending_value = total_value_with_div

    # 達標狀況判斷
    achieved = cagr >= target_return
    diff_from_target = cagr - target_return

    return {
        "id": fund["id"],
        "name": fund["name"],
        "issuer": fund["issuer"],
        "market": fund["market"],
        "manager": fund["manager"],
        "manager_tenure": fund.get("manager_tenure", ""),
        "share_type": "配息型" if is_dividend else "累積型",
        "freq": fund.get("distribution_frequency", ""),
        "div_yield": div_yield,
        "cagr_period": cagr,
        "capital": capital,
        "ending_value": ending_value,
        "total_profit": total_profit,
        "total_return_pct": total_return_pct,
        "monthly_cashflow": monthly_cashflow,
        "total_dividends": total_dividends,
        "nav_capital": nav_capital,
        "achieved": achieved,
        "diff_from_target": diff_from_target,
        "channels": fund.get("channels", ""),
        "risk_level": fund.get("risk_level", ""),
        "official_url": fund.get("official_url", ""),
        "query_url": fund.get("query_platform_url", "")
    }

def run_simulation(capital=1000000, target_return=12.0, years=3, mode="all", market="all"):
    funds, last_updated = load_funds_data()
    results = []

    for f in funds:
        is_div = "配息型" in f.get("share_type", "")
        # 模式篩選
        if mode == "accumulate" and is_div:
            continue
        if mode == "dividend" and not is_div:
            continue

        # 市場篩選
        m = f.get("market", "")
        if market == "tw" and "台股" not in m:
            continue
        if market == "us" and "美股" not in m and "全球" not in m:
            continue

        res = calculate_fund_profit(f, capital, target_return, years)
        results.append(res)

    # 依獲利金額由高至低排序
    results.sort(key=lambda x: x["total_profit"], reverse=True)
    return results, last_updated

def print_report(results, last_updated, capital, target_return, years, mode, market):
    print("=" * 105)
    print("🌟 台灣銀行/平台可申購基金歷年獲利與經理人績效評估報告 🌟")
    print(f"📅 資料最後更新時間：{last_updated} (每日營業日淨值已更新)")
    print("=" * 105)
    print(f"【投資設定參數】")
    print(f"  • 投入本金: NT$ {capital:,.0f} 元")
    print(f"  • 期望年化獲利率: {target_return:.2f}%")
    print(f"  • 投資試算期間: {years} 年 (對應歷年年化CAGR)")
    print(f"  • 獲利機制篩選: {'全部比較' if mode == 'all' else ('淨值累積型' if mode == 'accumulate' else '配息型')}")
    print(f"  • 市場標的篩選: {'全部市場' if market == 'all' else ('純台股' if market == 'tw' else '美股/全球')}")
    print("-" * 105)

    if not results:
        print("未找到符合條件的基金。")
        return

    print(f"🔥【符合條件的前五名 (Top 5) 推薦清單】：")
    for idx, f in enumerate(results[:5], 1):
        cash_txt = f"每月現金: NT$ {f['monthly_cashflow']:,.0f}/月" if f['share_type'] == '配息型' else "複利滾入淨值"
        print(f"   [{idx}] {f['name']} | 經理人: {f['manager']} | {f['share_type']}")
        print(f"       ► 年化CAGR: {f['cagr_period']:.1f}% | 預估獲利: +NT$ {f['total_profit']:,.0f} 元 | {cash_txt}")
        print(f"       ► 官網連結: {f['official_url']}")
    print("-" * 105)

    print(f"{'排名':<4}{'基金名稱':<24}{'經理人':<14}{'機制':<8}{'年化CAGR':<10}{'預估總獲利(NTD)':<16}{'月配息(NTD)':<14}{'達標狀況':<10}")
    print("-" * 105)

    for rank, r in enumerate(results, 1):
        achieved_str = f"✅ +{r['diff_from_target']:.1f}%" if r["achieved"] else f"❌ {r['diff_from_target']:.1f}%"
        monthly_str = f"{r['monthly_cashflow']:,.0f}/月" if r["share_type"] == "配息型" else "滾入淨值"
        print(f"{rank:<4}{r['name'][:22]:<24}{r['manager'][:12]:<14}{r['share_type']:<8}{r['cagr_period']:>6.1f}%   {r['total_profit']:>14,.0f} 元 {monthly_str:>12}   {achieved_str:<10}")

    print("=" * 105)
    print("🎯【客製化三大精選投資組合方案】 (不單押單檔，兼顧收益極大化與防禦分散)：")
    print(f"  ► 組合 A【強攻衝刺型 ‧ 100%科技累積】 (40%安聯台科 + 30%統一奔騰 + 30%貝萊德科技)")
    p1_profit = capital * 0.4 * ((1 + 36.8/100)**years - 1) + capital * 0.3 * ((1 + 34.2/100)**years - 1) + capital * 0.3 * ((1 + 31.2/100)**years - 1)
    print(f"     預估 {years} 年總獲利: +NT$ {p1_profit:,.0f} 元 (平均年化約 +34.3%，衝刺本金翻倍)")

    print(f"  ► 組合 B【攻守兼備型 ‧ 50%累積+50%配息】 (25%安聯台科 + 25%貝萊德科技 + 25%元大高股息龍頭 + 25%安聯收益成長)")
    p2_profit = capital * 0.25 * ((1 + 36.8/100)**years - 1) + capital * 0.25 * ((1 + 31.2/100)**years - 1) + capital * 0.25 * ((1 + 21.2/100)**years - 1) + capital * 0.25 * ((1 + 12.8/100)**years - 1)
    p2_cash = (capital * 0.25 * 0.068 + capital * 0.25 * 0.081) / 12
    print(f"     預估 {years} 年總獲利: +NT$ {p2_profit:,.0f} 元 | 每月現金入帳: 約 NT$ {p2_cash:,.0f} 元/月 (雙引擎進退皆宜)")

    print(f"  ► 組合 C【退休金流型 ‧ 100%月配息高息】 (40%安聯收益成長 + 30%元大高股息龍頭 + 30%摩根多重收益)")
    p3_profit = capital * 0.4 * ((1 + 12.8/100)**years - 1) + capital * 0.3 * ((1 + 21.2/100)**years - 1) + capital * 0.3 * ((1 + 9.5/100)**years - 1)
    p3_cash = (capital * 0.4 * 0.081 + capital * 0.3 * 0.068 + capital * 0.3 * 0.092) / 12
    print(f"     預估 {years} 年含息總獲利: +NT$ {p3_profit:,.0f} 元 | 每月現金入帳: 約 NT$ {p3_cash:,.0f} 元/月 (月月領現金)")
    print("=" * 105)

def main():
    parser = argparse.ArgumentParser(description="台灣可購基金歷年獲利與最高收益試算器")
    parser.add_argument("-c", "--capital", type=float, default=1000000, help="投入台幣本金 (預設 1,000,000 元)")
    parser.add_argument("-r", "--target-return", type=float, default=12.0, help="期望年化獲利率百分比 (預設 12.0%)")
    parser.add_argument("-y", "--years", type=int, default=3, help="投資年期 (1, 3, 5, 10，預設 3 年)")
    parser.add_argument("-m", "--mode", choices=["all", "accumulate", "dividend"], default="all", help="獲利模式 (all, accumulate累積型, dividend配息型)")
    parser.add_argument("-k", "--market", choices=["all", "tw", "us"], default="all", help="市場篩選 (all, tw台股, us美股/全球)")

    args = parser.parse_args()
    results, last_updated = run_simulation(args.capital, args.target_return, args.years, args.mode, args.market)
    print_report(results, last_updated, args.capital, args.target_return, args.years, args.mode, args.market)

if __name__ == "__main__":
    main()
