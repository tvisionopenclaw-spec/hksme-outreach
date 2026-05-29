"""Handcrafted Cantonese scripts for the 20 銅鑼灣 美容 leads.
Bypasses Gemini quota for tomorrow's send.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
import lib

SCRIPTS = {
    120: "Hi Rosy Nails！見你哋 Windsor House 鋪做美甲，估你哋日日 WhatsApp 同 booking confirm 食晒時間 😊 我送你免費 30 分鐘 AI workflow audit，揾出 3 個慳時間方法。覆「ok」我即刻 send calendar link 畀你揀時間。",
    119: "你哋好 甲甲屋！知你哋做美甲，4.9 評分好正。但我估你哋日日 reply 客 WhatsApp + 排 booking 食晒時間。我送你免費 30 分鐘 AI audit，揾 3 個慳時間方法。回「ok」send calendar 揀時間 😊",
    118: "Hello NAIL NAIL！見你哋啱啱開喺銅鑼灣，5 星評分爆好。新店最食時間就係 booking 同客 message。免費 30 分鐘 AI workflow audit，揾 3 個 quick wins。回「ok」我 send calendar 揀時間 🙂",
    117: "Hi Nail Captain！36 個 review 全 5 星好犀利。不過我估你哋平時 reply WhatsApp 同 confirm booking 食晒時間。免費 30 分鐘 AI audit，揾出 3 個慳時間方法。回「ok」我即刻 send calendar 揀時間 😊",
    116: "Hello Something You Love Nail！見你哋喺銅鑼灣做美甲，平日 booking 應該都好多，估你哋忙到 reply WA 都唔得閒。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。覆「ok」我 send calendar 揀時間。",
    115: "Hi Win.G Nail！我哋見好多 HK nail salon 都係 booking confirm + WA reply 食晒時間。送你免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。完全免費，覆「ok」我 send calendar 揀時間 🙂",
    114: "你哋好 Nail House！知你哋做美甲，估你哋日日 reply 客 WhatsApp + plan booking 食晒時間。免費 30 分鐘 AI workflow audit，揾出 3 個 quick wins。覆「ok」我 send calendar link 揀時間 😊",
    113: "Hi Love Share Beauty！見你哋銅鑼灣分店 reviews 都好正。我估你哋日日 booking confirm + WA 客查問食晒時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。回「ok」send calendar 揀時間 😊",
    112: "Hello Hand and Foot SPA！見你哋 309 個 review 真係靚仔。但我估你哋日日 reply WA 同 confirm booking 食晒時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。回「ok」我 send calendar 揀時間 🤝",
    111: "Hi Tinted！見你哋 reviews 過百好正。但我估你哋日日 WA confirm booking + 客 follow-up 食晒時間。送你免費 30 分鐘 AI workflow audit，揾 3 個慳時間 quick wins。覆「ok」send calendar 揀時間 😊",
    110: "Hello Queen's Beauty & Spa！見你哋 reviews 97 個好正。我估你哋日日 booking + WA reply 食晒老闆時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。覆「ok」即刻 send calendar 揀時間 😊",
    109: "Hi Skin Beauty Int'l！320 個 reviews 全 4.9 真係好厲害。不過我估你哋每日客 reception + booking confirm 用好多人手。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。回「ok」send calendar 揀時間 🤝",
    108: "你哋好 琥珀美容！120 個 5 星 review 真係好正。我估你哋平日 booking 同 WA 客 follow-up 食晒老闆時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間 quick wins。覆「ok」send calendar 揀時間 😊",
    107: "Hello pikapika the nail parlour！見你哋做美甲，估你哋日日 WhatsApp 同 booking 排期食晒時間。送你免費 30 分鐘 AI workflow audit，揾出 3 個慳時間方法。覆「ok」我 send calendar 揀時間 🙂",
    106: "Hi LE V BEAUTY 自妍•美！見你哋 reviews 4.9 好正。但我估你哋日日 booking confirm + WA reply 食晒老闆時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。回「ok」我即刻 send calendar 揀時間 😊",
    105: "Hello Miagnes Beaute Spa！見你哋做泰式按摩 + 面部瑜伽 + 一叮溶脂幾多元化。但我估 booking + WA 客 confirm 食晒時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。覆「ok」send calendar 揀時間 🤝",
    104: "Hi Mildred Beauty！見你哋銅鑼灣店 reviews 4.8 好穩。我估你哋每日 booking 同 WA confirm 食晒老闆時間。免費 30 分鐘 AI workflow audit，揾出 3 個慳時間方法。回「ok」我 send calendar 揀時間 😊",
    103: "你哋好 悠然薈！見你哋 reviews 4.9 好正喎。但我估你哋平日 booking + WA 客 reply 食晒時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。回「ok」我 send calendar 揀時間 🙂",
    102: "Hello You Medical Beauty！見你哋醫學美容做開銅鑼灣，reviews 都好正。但我估每日客 reception + WA reply 食晒時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。覆「ok」send calendar 揀時間 🤝",
    101: "Hi 森薈美容養生！見你哋做美容養生 reviews 全 5 星好厲害。我估你哋日日 booking + WA 客查 follow-up 食晒時間。免費 30 分鐘 AI workflow audit，揾 3 個慳時間方法。回「ok」send calendar 揀時間 😊",
}


def main():
    conn = lib.get_db()
    updated = 0
    for lead_id, script in SCRIPTS.items():
        # get phone for wa_deeplink
        row = conn.execute("SELECT phone FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if not row:
            print(f"  ⚠️ ID {lead_id} not found in DB")
            continue
        phone = row["phone"]
        deeplink = lib.wa_deeplink(phone, script)
        conn.execute(
            "UPDATE leads SET script = ?, wa_deeplink = ? WHERE id = ?",
            (script, deeplink, lead_id),
        )
        updated += 1
    conn.commit()
    conn.close()
    print(f"✅ Updated {updated} leads with handcrafted scripts")

    # Verify quality
    print("\n--- Verification ---")
    leads = lib.get_leads(limit=20)
    all_good = True
    for l in leads:
        s = l.get("script") or ""
        is_bad = lib.is_problematic_script(s)
        flag = "❌" if is_bad else "✅"
        print(f"{flag} [{l['id']}] len={len(s)}  {s[:60]}...")
        if is_bad:
            all_good = False
    print()
    if all_good:
        print("🎉 ALL 20 SCRIPTS CLEAN — ready for tomorrow's send")
    else:
        print("⚠️  Some still problematic — review above")


if __name__ == "__main__":
    main()
