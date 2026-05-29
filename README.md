# HK SME Cold Outreach Skill

Auto-scrape Google Maps → draft Cantonese WhatsApp scripts → one-click send.
Designed for booking AI workflow consulting demos at scale from cold market.

---

## One-time setup (5 分鐘)

### 1. Set API keys

```bash
cp ~/.claude/skills/hksme-cold-outreach/.env.example \
   ~/.claude/skills/hksme-cold-outreach/.env

# Edit and fill in your Apify token + Gemini key
$EDITOR ~/.claude/skills/hksme-cold-outreach/.env
```

You already have both keys (from SocialAuto). Re-use them.

### 2. Get a separate WhatsApp Business account

**CRITICAL — DO NOT USE personal WhatsApp or SocialAuto admin WA.**

- New SIM card (~HK$50 prepaid) OR second-line app (Truphone / Hushed)
- Install WhatsApp Business app on that number
- Profile name: `[Your Name] — AI for HK SME`
- Add your Cal.com / Calendly link in bio

### 3. Set up Calendly / Cal.com

- Free Cal.com account
- 1 event type: "AI Workflow Audit (Free 30 min)"
- Open all weekday slots 10am-7pm next 14 days

---

## Usage

```bash
# Quick blast — 100 餐廳 in 觀塘, text DM mode
python3 ~/.claude/skills/hksme-cold-outreach/run.py \
  --niche 餐廳 --area 觀塘 --count 100 --mode text

# Voice memo mode (higher reply but slower to send)
python3 ~/.claude/skills/hksme-cold-outreach/run.py \
  --niche 美容 --area 銅鑼灣 --count 50 --mode voice
```

Output: CSV on Desktop with `wa_deeplink` column. Click each link → opens WhatsApp with pre-filled message (text mode) → click Send button.

### Or just invoke the skill in Claude Code

Type `/hksme-cold-outreach` and Claude will ask for niche + area + count + mode, then run.

---

## 3-Day Maximum Outreach Plan — 300+ touches

### Reach as many as possible: stack channels + ramp WA carefully

**WhatsApp send caps (new account safety):**
| Day | Safe cap | Cumulative |
|---|---|---|
| Day 1 | 30 | 30 |
| Day 2 | 50 | 80 |
| Day 3 | 70 | 150 |

To push beyond 150 in 3 days, **stack additional channels** on the same target list.

### Day 1 — Setup + first 30 sends + IG/FB stacking

**Morning (90 min):**
1. Run skill: `--niche 餐廳 --area 觀塘 --count 150 --mode text`
   - This drafts 150 WA scripts, but you'll only send 30 today
2. Output CSV gets ~150 rows
3. While drafting runs, for each row do this in parallel (open in new tab):
   - Search Google: `"<business name>" instagram` → get IG handle
   - Search Google: `"<business name>" facebook` → get FB page
   - Add to CSV columns `ig_handle` and `fb_page`

**Late morning (1 hr):**
- Send 30 WA via wa_deeplink (1 click each, ~3 sec/send = 90 sec total)
- Done. Stay under cap day 1.

**Afternoon (2 hr) — IG DM blast:**
- For 50 of your 150 list that have IG handle
- Open IG, paste same script (Cantonese), send
- IG has no day cap if not flagged spam — ramp gradually anyway, 50/day max

**Evening:**
- For 30 of your list that have FB page
- Open FB Business Suite, send message via page
- Caps ~30/day to fresh pages

**Day 1 total: 30 WA + 50 IG + 30 FB = 110 touches**

### Day 2 — Reply to Day 1 + 50 new WA + new IG/FB batch

**Morning:**
- Check WA / IG / FB for replies. Reply within 1 hr (HK SME owners expect fast)
- For "ok" replies → send Cal.com link immediately. Don't negotiate.

**Mid-day:**
- Send 50 new WA (next 50 rows in CSV)
- Send 50 new IG DM
- Send 30 new FB message

**Day 2 total: 50 WA + 50 IG + 30 FB = 130 touches. Cumulative: 240.**

### Day 3 — Final push + first demos

**Morning:**
- Send 70 WA (final batch from CSV)
- Send 50 IG DM
- Send 30 FB message
- Day 3 total: 150 touches. Cumulative: 390.

**Afternoon:**
- Start conducting demos that booked Mon/Tue
- Block 4 × 30-min slots: 2pm, 3pm, 4pm, 5pm

### Expected outcome (conservative)

```
390 touches
├─ 60-80 replies (15-20%)
├─ 25-40 book demo (35-50% of replies)
├─ 15-25 demos conducted in week (rest book for week 2)
└─ 4-8 paid Founding Client Audits @ HK$3k = HK$12-24k cash
```

### Expected outcome (if scripts hit hard)

```
390 touches
├─ 120 replies (30%)
├─ 60 book demo
├─ 30 demos conducted
└─ 10 paid @ HK$3k = HK$30k cash
```

---

## Compliance / Risk

- **Use SEPARATE WA Business account.** Mixing with personal or SocialAuto admin = ban risk
- **Don't repeat-send.** 1 voice/text + 1 follow-up after 48 hr max. After that, stop.
- **Honor opt-outs immediately.** If reply says "stop" / "唔好再聯絡" / "remove" → mark in CSV `notes`, never re-contact
- **No spammy hashtags.** Don't blast same script to chains' staff or non-businesses
- **Don't claim you have customers if you don't.** Frame: "我自己做緊呢方面，想揾 founding clients"

---

## Niche options

| Niche | Best for | Avg reply rate |
|---|---|---|
| `餐廳` | High volume, owner on WA | 12-18% |
| `cafe` | Younger owner, IG-active | 15-20% |
| `美容` | Owner directly answers | 18-25% |
| `補習` | Owner-operated, pain clear | 10-15% |
| `retail` | Smaller pain, lower rate | 8-12% |
| `clinic` | Higher ticket but slow | 8-12% |

**Recommendation for first blast:** `美容 銅鑼灣 100 text` — highest expected reply rate.

---

## Troubleshooting

**"No businesses passed filter"**: Try broader area (e.g. `九龍` instead of `觀塘工廈`) or different niche queries.

**Gemini rate limit hit**: Script auto-retries 3x. If persistent, reduce `--count` to 50 and run twice.

**wa.me deeplink doesn't pre-fill on iOS**: iOS Safari quirk. Copy script from CSV `script` column manually after deeplink opens WA.

**WA account flagged**: You're sending too fast. Stop 24 hr. Resume at half the rate. Don't send to numbers that block you.
