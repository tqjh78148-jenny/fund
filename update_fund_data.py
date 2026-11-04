"""
台股科技 ETF 與高科技佔比基金——價格位階評估暨 50,000 點推估引擎
雙重演算法：
- 模型 A：波段高點回檔法 (Drawdown)
- 模型 B：均線負乖離法 (60MA / 120MA BIAS)
- 綜合燈號：雙重甜甜價 (💎) / 偏甜合理 (🟡) / 昂貴過熱 (🔴)
- 大盤 50,000 點連動推估 (每投入 10 萬元預估獲利)
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

def evaluate_models(current_p, peak_p, ma60, ma120):
    """
    模型 A：波段高點回檔法 (Drawdown)
    - 昂貴價：DD < 10%
    - 合理價：15% <= DD <= 20%
    - 甜甜價：DD >= 25% (達 30% 為極甜)

    模型 B：均線負乖離法 (BIAS)
    - 季線乖離：BIAS_60 = (P - 60MA) / 60MA * 100%
    - 半年線乖離：BIAS_120 = (P - 120MA) / 120MA * 100%
    - 昂貴價：BIAS_60 > +15%
    - 合理價：-5% <= BIAS_60 <= +5%
    - 甜甜價：BIAS_60 <= -10% 或 BIAS_120 <= -12%

    綜合燈號：
    - 雙重甜甜價 (💎 綠燈)：模型 A 與 模型 B 同時符合甜甜價
    - 偏甜/合理 (🟡 黃燈)：符合其中一項甜甜價，或兩者皆處於合理區
    - 昂貴過熱 (🔴 紅燈)：符合任一昂貴價標準
    """
    # 1. 模型 A
    dd = ((peak_p - current_p) / peak_p * 100) if peak_p > 0 else 0
    if dd >= 25.0:
        model_a_status = "甜甜價"
        model_a_tag = "🟢 甜甜價 (超跌打折)" if dd < 30.0 else "🟢 極甜超跌價 (≥30%)"
    elif 15.0 <= dd <= 20.0:
        model_a_status = "合理價"
        model_a_tag = "🟡 合理價 (健康回測)"
    elif dd < 10.0:
        model_a_status = "昂貴價"
        model_a_tag = "🔴 昂貴價 (追高風險大)"
    else:
        # 10% <= dd < 15% 或 20% < dd < 25%
        model_a_status = "合理偏高" if dd < 15.0 else "偏甜合理"
        model_a_tag = "🟡 常態整理區間"

    # 2. 模型 B
    bias_60 = ((current_p - ma60) / ma60 * 100) if ma60 > 0 else 0
    bias_120 = ((current_p - ma120) / ma120 * 100) if ma120 > 0 else 0

    if bias_60 <= -10.0 or bias_120 <= -12.0:
        model_b_status = "甜甜價"
        model_b_tag = "🟢 甜甜價 (橡皮筋負乖離超跌)"
    elif bias_60 > 15.0:
        model_b_status = "昂貴價"
        model_b_tag = "🔴 昂貴價 (正乖離過大)"
    elif -5.0 <= bias_60 <= 5.0:
        model_b_status = "合理價"
        model_b_tag = "🟡 合理價 (均線糾結回測支撐)"
    else:
        model_b_status = "偏甜合理" if bias_60 < 0 else "合理偏高"
        model_b_tag = "🟡 常態震盪"

    # 3. 綜合判定
    if model_a_status == "甜甜價" and model_b_status == "甜甜價":
        combined_status = "dual_sweet"
        combined_tag = "💎 雙重甜甜價"
        badge_style = "bg-emerald-100 text-emerald-800 border-emerald-300"
    elif model_a_status == "昂貴價" or model_b_status == "昂貴價":
        combined_status = "expensive"
        combined_tag = "🔴 昂貴過熱"
        badge_style = "bg-rose-100 text-rose-800 border-rose-300"
    else:
        combined_status = "fair"
        combined_tag = "🟡 偏甜 / 合理"
        badge_style = "bg-amber-100 text-amber-800 border-amber-300"

    return {
        "dd_pct": round(dd, 2),
        "bias_60_pct": round(bias_60, 2),
        "bias_120_pct": round(bias_120, 2),
        "model_a": {
            "status": model_a_status,
            "tag": model_a_tag
        },
        "model_b": {
            "status": model_b_status,
            "tag": model_b_tag
        },
        "combined": {
            "status": combined_status,
            "tag": combined_tag,
            "badge_style": badge_style
        }
    }

def project_scenario(current_p, beta, base_index=44000, target_index=50000):
    delta_index = (target_index - base_index) / base_index
    target_gain = delta_index * beta
    target_price = current_p * (1 + target_gain)
    profit_per_100k = 100000 * target_gain

    return {
        "base_index": base_index,
        "target_index": target_index,
        "delta_index_pct": round(delta_index * 100, 2),
        "target_gain_pct": round(target_gain * 100, 2),
        "target_price": round(target_price, 2),
        "profit_per_100k": round(profit_per_100k, 0)
    }

def update_all():
    if not DATA_FILE.exists():
        print(f"錯誤：找不到檔案 {DATA_FILE}")
        return False

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    timestamp_str, date_str = get_current_timestamp()
    data["last_updated"] = timestamp_str
    base_idx = data.get("base_market_index", 44000)
    target_idx = data.get("default_target_index", 50000)

    targets = data.get("targets", [])

    print("================================================================================")
    print("🚀 台股科技 ETF 與高科技佔比基金——價格位階評估暨 50,000 點推估系統")
    print(f"📅 資料更新時間：{timestamp_str}")
    print(f"📊 當前大盤指數：{base_idx:,} 點 ➔ 目標指數：{target_idx:,} 點 (預估大盤 +{((target_idx-base_idx)/base_idx*100):.2f}%)")
    print("================================================================================")

    for item in targets:
        p_curr = item.get("current_price", 0.0)
        p_peak = item.get("peak_price", p_curr)
        ma60 = item.get("ma_60", p_curr)
        ma120 = item.get("ma_120", p_curr)
        beta = item.get("beta", 1.8)

        # 雙重模型評估
        val = evaluate_models(p_curr, p_peak, ma60, ma120)
        item["evaluation"] = val

        # 50,000 點推估
        sc = project_scenario(p_curr, beta, base_idx, target_idx)
        item["scenario_50k"] = sc

        # 分項條列輸出 (嚴格禁止使用表格排版)
        print(f"【{item['code']} {item['name']}】")
        print(f"  • 當前淨值: {p_curr:.2f} 元 | 波段最高: {p_peak:.2f} 元 (回檔: -{val['dd_pct']}%)")
        print(f"  • 季線 60MA: {ma60:.2f} 元 (乖離: {val['bias_60_pct']:+.2f}%) | 半年線 120MA: {ma120:.2f} 元 (乖離: {val['bias_120_pct']:+.2f}%)")
        print(f"  • 綜合評估: {val['combined']['tag']} (模型A: {val['model_a']['status']} / 模型B: {val['model_b']['status']})")
        print(f"  • 大盤 50,000 點推估: 目標價 {sc['target_price']:.2f} 元 (漲幅 +{sc['target_gain_pct']}%) | 每投10萬預期獲利: +NT$ {int(sc['profit_per_100k']):,}")
        print("--------------------------------------------------------------------------------")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print("✅ 資料庫更新完畢，已成功寫入:", DATA_FILE)
    return True

if __name__ == "__main__":
    update_all()
