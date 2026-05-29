---
name: hksme-cold-outreach
description: Auto-scrape HK SME businesses from Google Maps via Apify, draft personalized Cantonese WhatsApp outreach via Gemini, and output a ready-to-send CSV with one-click wa.me deeplinks. Use proactively when user wants to cold-outreach HK SME owners at scale — triggers include "cold outreach HK SME", "WhatsApp blast HK SME", "scrape Google Maps HK 餐廳/美容/補習", "find HK SME for AI consulting", or "/hksme-cold-outreach".
---

# HK SME Cold Outreach Auto-Run

When invoked, run the cold outreach generator end-to-end. Goal: hand the user a CSV with N personalized Cantonese WhatsApp scripts + one-click wa.me deeplinks they can fire off in ~30 sec/each.

## Inputs (ask user only if not in invocation args)

1. **Niche** (required): `餐廳` / `cafe` / `美容` / `補習` / `retail` / `clinic`
2. **Area** (required, HK district): e.g. `觀塘` / `旺角` / `銅鑼灣` / `尖沙咀` / `中環` / `葵涌` / `荃灣` / `沙田`
3. **Count** (default 100, range 20-300)
4. **Mode** (default `text`):
   - `text` — pre-filled WhatsApp text DM via wa.me deeplink (1 click → opens WA → click send. ~5 sec/send)
   - `voice` — script user reads aloud as voice memo (~45 sec/send, 2-3x higher reply rate)

## Execution steps

1. **Check env vars** — `APIFY_TOKEN` and `GEMINI_API_KEY` must be set. Source from `~/.claude/skills/hksme-cold-outreach/.env` if exists, or user's shell env. If missing, prompt user.

2. **Run scraper + drafter**:
   ```bash
   python3 ~/.claude/skills/hksme-cold-outreach/run.py \
     --niche {niche} \
     --area {area} \
     --count {count} \
     --mode {mode} \
     --output ~/Desktop/outreach-{niche}-{area}-{YYYYMMDD}.csv
   ```

3. **Report back** to user:
   - Total drafted
   - Output CSV path
   - First 3 wa.me deeplinks (preview so user can test 1 immediately)
   - Estimated send time at 50/day pace

4. **Remind compliance**:
   - Use SEPARATE WhatsApp Business account (not personal, not SocialAuto admin)
   - New WA ramp: Day 1-2 = 30/day, Day 3-7 = 50/day, Week 2+ = 100/day
   - 1 follow-up max per business
   - If reply says stop / 唔好再聯絡 / remove → flag in `notes`, never re-contact

## Output CSV columns

| Col | Content |
|---|---|
| name | Business name |
| phone | Phone (852-prefixed, no spaces) |
| address | HK address |
| rating | Google rating |
| reviews | Review count |
| script | Cantonese WhatsApp script (ready to read/paste) |
| wa_deeplink | `https://wa.me/852XXX?text=...` — text mode pre-fills script |
| website | Website if any |
| status | (user fills: Drafted / Sent / Replied / Booked / Done / Skip) |
| sent_at | (user fills timestamp) |
| replied | (user fills Y/N) |
| booked_demo | (user fills Y/N) |
| notes | (user fills any context) |

## Failure modes

- **No Apify results**: try broader area, or check Apify actor `compass/crawler-google-places` is enabled
- **Gemini rate limit**: script sleeps 0.5s between calls; if hit limit, retry with `--count` lower
- **wa.me deeplink doesn't pre-fill on iOS**: known iOS quirk; user copies script from CSV manually

## Related skills / projects

- `tvision-sales/` — full Firebase build of this concept (paused; use this skill for now)
- See `~/.claude/skills/hksme-cold-outreach/README.md` for full 3-day blast plan
