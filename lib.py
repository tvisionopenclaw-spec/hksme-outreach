"""
HK SME Cold Outreach — shared library.

Used by both run.py (CLI) and portal.py (Streamlit web UI).
Handles env loading, Apify scraping, Gemini drafting, SQLite persistence.
"""
import json
import os
import re
import signal
import sqlite3
import subprocess
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

try:
    import requests
except ImportError:
    import subprocess
    import sys
    subprocess.check_call([sys.executable, "-m", "pip", "install", "--quiet", "requests"])
    import requests

# ---------- Paths ----------
SKILL_DIR = Path(__file__).parent
ENV_FILE = SKILL_DIR / ".env"
DB_PATH = SKILL_DIR / "data" / "leads.db"
AUTO_DISCOVER_PID_FILE = SKILL_DIR / "data" / "auto_discover.pid"
AUTO_DISCOVER_STATUS_FILE = SKILL_DIR / "data" / "auto_discover_status.json"
AUTO_DISCOVER_QUEUE_FILE = SKILL_DIR / "data" / "auto_discover_queue.json"
AUTO_DISCOVER_LOG_FILE = SKILL_DIR / "data" / "auto_discover.log"


def load_env():
    """Load APIFY_TOKEN and GEMINI_API_KEY from .env file or shell env."""
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return os.environ.get("APIFY_TOKEN", ""), os.environ.get("GEMINI_API_KEY", "")


# ---------- Niche config ----------
NICHES = {
    # === Food & Beverage ===
    "餐廳": {
        "queries": ["餐廳", "茶餐廳", "酒樓"],
        "pain": "客 reply、IG/FB post、reservation 同 takeout 雜事",
        "ai_quick_wins": "WhatsApp 自動 reply、IG caption AI 寫、菜單翻譯多語言",
    },
    "cafe": {
        "queries": ["cafe", "咖啡店"],
        "pain": "IG content 唔夠時間 post、customer message 多到爆、loyalty tracking",
        "ai_quick_wins": "AI 寫 IG caption + hashtag、auto-reply WA、customer DM 整理",
    },
    "酒吧": {
        "queries": ["酒吧", "bar", "lounge"],
        "pain": "event promo、reservation、客 IG DM 食晒時間",
        "ai_quick_wins": "event poster AI 生、auto-reply、weekly promo 自動 schedule",
    },
    # === Beauty & Wellness ===
    "美容": {
        "queries": ["美容院", "美甲", "髮型屋"],
        "pain": "booking 同 WhatsApp confirm 食晒時間、客 no-show、loyalty 留客",
        "ai_quick_wins": "booking auto-reminder、客 birthday auto-message、IG before/after auto-post",
    },
    "按摩": {
        "queries": ["按摩", "spa", "推拿"],
        "pain": "預約 confirm、客 follow-up、therapist schedule",
        "ai_quick_wins": "預約 auto-reminder、客 health profile track、packages auto-renewal",
    },
    "健身": {
        "queries": ["健身室", "yoga", "私人教練", "gym"],
        "pain": "member retention、class booking、PT schedule、會員 billing",
        "ai_quick_wins": "lapsed member auto-reach、class capacity dashboard、PT note AI 整理",
    },
    # === Health ===
    "牙醫": {
        "queries": ["牙醫", "dental clinic"],
        "pain": "appointment confirm、insurance claim form、follow-up reminder",
        "ai_quick_wins": "appointment 自動提醒、保險 form OCR + auto-fill、術後 follow-up auto",
    },
    "中醫": {
        "queries": ["中醫診所", "中醫師"],
        "pain": "預約管理、處方記錄、回診 reminder、藥材庫存",
        "ai_quick_wins": "預約 reminder、病人記錄 search AI、藥材 stock alert",
    },
    "物理治療": {
        "queries": ["物理治療", "脊醫", "physio"],
        "pain": "預約、treatment plan 跟進、保險 claim、術後 exercise reminder",
        "ai_quick_wins": "exercise reminder 自動 send、保險 form 自動處理、treatment note AI 整理",
    },
    # === Professional services ===
    "會計師": {
        "queries": ["會計師事務所", "accounting firm", "稅務顧問"],
        "pain": "客 document chase（WhatsApp 跟單）、quarterly report、tax filing reminder、客 invoice",
        "ai_quick_wins": "客 doc chase 自動 reminder、receipt OCR auto-categorize、tax filing checklist auto-generate",
    },
    "律師": {
        "queries": ["律師樓", "law firm", "solicitor"],
        "pain": "client intake、case research、document drafting、time billing",
        "ai_quick_wins": "client intake form AI summary、legal doc draft AI、billable time auto-track",
    },
    "物業代理": {
        "queries": ["地產代理", "物業代理", "property agent"],
        "pain": "viewing schedule、客 follow-up、listing update、document chase",
        "ai_quick_wins": "viewing auto-confirm、listing AI 寫 IG post、client follow-up sequence",
    },
    "保險經紀": {
        "queries": ["保險經紀", "insurance broker"],
        "pain": "lead follow-up、policy explain、claim assist、renewal reminder",
        "ai_quick_wins": "renewal auto-reminder、client FAQ AI auto-reply、policy comparison AI",
    },
    "IT": {
        "queries": ["IT 公司", "電腦維修", "IT services"],
        "pain": "ticket triage、client comms、service report、quotation",
        "ai_quick_wins": "ticket auto-triage、service report AI draft、quotation template auto-gen",
    },
    "設計公司": {
        "queries": ["設計公司", "design studio", "branding"],
        "pain": "client brief 收集、mood board、feedback rounds、project track",
        "ai_quick_wins": "client brief AI summary、moodboard AI 生、feedback consolidate AI",
    },
    "攝影": {
        "queries": ["攝影", "婚紗攝影", "photographer"],
        "pain": "booking、contract、schedule coordination、gallery delivery",
        "ai_quick_wins": "booking auto-confirm、contract template AI、gallery 自動 send",
    },
    # === Trade & Services ===
    "裝修": {
        "queries": ["裝修公司", "renovation"],
        "pain": "quote requests、project schedule、supplier comms、客 update",
        "ai_quick_wins": "quote AI generate、project status auto-update WA、supplier order auto-track",
    },
    "搬屋": {
        "queries": ["搬屋公司", "moving company"],
        "pain": "quote、scheduling、inventory list、客 follow-up",
        "ai_quick_wins": "quote calculator AI、scheduling auto-optimize、client follow-up sequence",
    },
    "清潔": {
        "queries": ["清潔公司", "cleaning service"],
        "pain": "booking、team schedule、客 feedback collect、billing",
        "ai_quick_wins": "booking 自動 confirm、team route AI optimize、recurring auto-billing",
    },
    "維修": {
        "queries": ["維修", "家居維修", "handyman"],
        "pain": "quote、scheduling、parts ordering、客 follow-up",
        "ai_quick_wins": "quote auto-template、schedule optimize、parts inventory alert",
    },
    # === Education ===
    "補習": {
        "queries": ["補習社", "教育中心"],
        "pain": "家長 WhatsApp 不停問問題、學生 progress 難 track、課程 admin",
        "ai_quick_wins": "家長 FAQ auto-reply、progress report AI draft、enrollment form 自動處理",
    },
    "興趣班": {
        "queries": ["興趣班", "音樂學校", "畫畫班"],
        "pain": "報名、家長 comms、schedule change、學生記錄",
        "ai_quick_wins": "enrollment auto、家長 broadcast、attendance auto-track",
    },
    "駕駛學校": {
        "queries": ["駕駛學校", "駕駛教練", "driving school"],
        "pain": "預約 lesson、學生 progress、考試 reminder、scheduling",
        "ai_quick_wins": "lesson 預約 auto、考試 reminder auto-send、學生 progress AI track",
    },
    # === Retail ===
    "retail": {
        "queries": ["服飾店", "精品店", "雜貨店"],
        "pain": "stock 對唔到、IG/FB 唔夠時間 post、return / refund admin",
        "ai_quick_wins": "stock auto-check、IG content batch 出、customer support AI",
    },
    "電器": {
        "queries": ["電器舖", "家電", "electronics"],
        "pain": "客 query、warranty admin、stock、後續 service",
        "ai_quick_wins": "客 FAQ AI、warranty auto-track、stock alert",
    },
    "花店": {
        "queries": ["花店", "florist"],
        "pain": "order 客 WhatsApp、scheduling delivery、IG post、節日預訂",
        "ai_quick_wins": "order auto-confirm、IG post AI、節日 promotion auto-blast",
    },
    # === General ===
    "clinic": {
        "queries": ["診所", "牙醫", "中醫"],
        "pain": "appointment 同 reminder 食晒人手、follow-up 流失客、insurance form admin",
        "ai_quick_wins": "appointment reminder auto-send、follow-up auto-message、form OCR + auto-fill",
    },
}

CHAIN_KEYWORDS = [
    "Starbucks", "McDonald", "KFC", "Pacific Coffee", "Pizza Hut",
    "7-Eleven", "Circle K", "OK便利店", "Watsons", "Mannings",
    "華潤", "百佳", "惠康", "Wellcome", "ParknShop",
    "Pret A Manger", "Subway", "MX", "大家樂", "大快活", "美心", "翠華",
    "Tsui Wah", "Café de Coral", "Maxim",
]


# ---------- Apify scrape ----------
def scrape_gmaps(niche, area, count, apify_token, scrape_progress_callback=None):
    """Run Apify Google Places scraper async + poll for completion.

    Async pattern avoids connection timeouts on the sync endpoint for longer scrapes.
    """
    queries = [f"{area} {q}" for q in NICHES[niche]["queries"]]
    body = {
        "searchStringsArray": queries,
        "locationQuery": "Hong Kong",
        "maxCrawledPlacesPerSearch": max(20, count // len(queries) + 10),
        "language": "zh-TW",
        "scrapePlaceDetailPage": True,
    }

    # 1. Start run (async)
    start_url = f"https://api.apify.com/v2/acts/compass~crawler-google-places/runs?token={apify_token}"
    r = requests.post(start_url, json=body, timeout=30)
    r.raise_for_status()
    run = r.json()["data"]
    run_id = run["id"]
    dataset_id = run["defaultDatasetId"]

    # 2. Poll for completion (max 15 min)
    status_url = f"https://api.apify.com/v2/actor-runs/{run_id}?token={apify_token}"
    start_ts = time.time()
    poll_interval = 5
    max_wait = 15 * 60  # 15 min hard cap
    final_status = None
    while time.time() - start_ts < max_wait:
        time.sleep(poll_interval)
        try:
            s = requests.get(status_url, timeout=30)
            s.raise_for_status()
            data = s.json()["data"]
            status = data["status"]
            stats = data.get("stats", {}) or {}
            done = stats.get("requestsFinished", 0)
            total_q = stats.get("requestsTotal", 0)
            elapsed = int(time.time() - start_ts)
            if scrape_progress_callback:
                scrape_progress_callback(done, total_q, elapsed, status)
            if status in ("SUCCEEDED", "FAILED", "TIMED-OUT", "ABORTED"):
                final_status = status
                break
        except requests.exceptions.RequestException:
            # transient — keep polling
            continue

    if final_status != "SUCCEEDED":
        raise RuntimeError(f"Apify run ended with status: {final_status or 'TIMEOUT'}")

    # 3. Fetch dataset items
    data_url = f"https://api.apify.com/v2/datasets/{dataset_id}/items?token={apify_token}&clean=true&format=json"
    d = requests.get(data_url, timeout=120)
    d.raise_for_status()
    return d.json()


def is_hk_mobile(phone):
    """HK mobile numbers are 8 digits starting with 5/6/7/9.
    2xxx and 3xxx are landlines (no WhatsApp). 8xxx is unused.
    """
    digits = re.sub(r"\D", "", phone)
    if digits.startswith("852"):
        digits = digits[3:]
    return len(digits) == 8 and digits[0] in "5679"


def filter_results(results, count):
    seen_phones = set()
    filtered = []
    for r in results:
        phone = r.get("phone") or r.get("phoneUnformatted") or ""
        if not phone:
            continue
        phone = re.sub(r"[^\d+]", "", phone)
        if not phone or phone in seen_phones:
            continue
        # HK mobile filter — landlines (2xxx/3xxx) don't have WhatsApp
        if not is_hk_mobile(phone):
            continue
        title = r.get("title", "") or ""
        if any(c.lower() in title.lower() for c in CHAIN_KEYWORDS):
            continue
        reviews = r.get("reviewsCount", 0) or 0
        if reviews < 3:
            continue
        seen_phones.add(phone)
        filtered.append({
            "name": title,
            "phone": phone,
            "address": r.get("address", "") or "",
            "rating": r.get("totalScore", 0) or 0,
            "reviews": reviews,
            "website": r.get("website", "") or "",
            "categories": ", ".join(r.get("categoryName", "").split(",")[:2]) if r.get("categoryName") else "",
        })
        if len(filtered) >= count:
            break
    return filtered


# ---------- Gemini draft ----------
def draft_message(biz, niche, mode, gemini_key):
    cfg = NICHES[niche]
    common = (
        f"目標公司：{biz['name']}\n"
        f"行業：{niche}\n"
        f"地址：{biz['address']}\n"
        f"Google rating：{biz['rating']}（{biz['reviews']} reviews）\n"
        f"典型痛點：{cfg['pain']}\n"
        f"AI quick wins：{cfg['ai_quick_wins']}\n\n"
        f"你 offer：免費 30 分鐘 AI workflow audit，揾出 3 個慳時間方法。\n"
    )
    if mode == "voice":
        rules = (
            "寫一個 45 秒 cold WhatsApp voice memo script。\n"
            "規則：\n"
            "1. 廣東話口語，用「你哋」唔好「您」「親愛的」\n"
            "2. 開頭 mention 佢嘅 business name + 1 個 specific pain point\n"
            "3. 講「完全免費，唔需要 sign 任何嘢」\n"
            "4. 結尾叫佢回 voice memo 講「ok」就 send calendar link\n"
            "5. 全文 80-110 中文字\n"
            "6. 唔好用 emoji\n"
            "7. 直接出 script 文字，唔好加 markdown，唔好加「以下係 script：」呢類 prefix"
        )
    else:
        rules = (
            "寫一個 cold WhatsApp text DM。\n"
            "規則：\n"
            "1. 廣東話口語，用「你哋」唔好「您」「親愛的」\n"
            "2. 開頭 mention 佢嘅 business name + 1 個 specific pain point\n"
            "3. 講「完全免費」\n"
            "4. 結尾叫佢回「ok」就 send calendar link\n"
            "5. 全文 50-80 中文字\n"
            "6. 最多 1 個 emoji\n"
            "7. 直接出 message 文字，唔好加 markdown，唔好加 prefix"
        )
    prompt = common + rules

    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={gemini_key}"
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.9,
            "maxOutputTokens": 1024,
            # Disable thinking mode to avoid partial-output artifacts on 2.5-flash
            "thinkingConfig": {"thinkingBudget": 0},
        },
    }
    # Free tier is 15 RPM — back off aggressively on 429
    backoffs_429 = [10, 30, 60, 120]
    backoffs_other = [3, 6, 12]
    max_attempts = 4
    last_err = None
    for attempt in range(max_attempts):
        try:
            r = requests.post(url, json=body, timeout=45)
            if r.status_code == 429:
                wait = backoffs_429[min(attempt, len(backoffs_429) - 1)]
                last_err = f"rate-limited (429), waiting {wait}s"
                time.sleep(wait)
                continue
            r.raise_for_status()
            data = r.json()
            candidates = data.get("candidates", [])
            if not candidates:
                last_err = f"no candidates: {data.get('promptFeedback', {})}"
                time.sleep(backoffs_other[min(attempt, len(backoffs_other) - 1)])
                continue
            text = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip()
            if not text:
                last_err = "empty response from Gemini"
                time.sleep(backoffs_other[min(attempt, len(backoffs_other) - 1)])
                continue
            return text
        except requests.exceptions.RequestException as e:
            last_err = f"network: {type(e).__name__}"
            if attempt < max_attempts - 1:
                time.sleep(backoffs_other[min(attempt, len(backoffs_other) - 1)])
        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            if attempt < max_attempts - 1:
                time.sleep(backoffs_other[min(attempt, len(backoffs_other) - 1)])
    return f"[ERROR drafting: {last_err}]"


# ---------- wa.me deeplink ----------
def wa_deeplink(phone, text):
    p = re.sub(r"[^\d]", "", phone)
    if not p.startswith("852") and len(p) == 8:
        p = "852" + p
    return f"https://wa.me/{p}?text={quote(text)}"


# ---------- IG deeplink ----------
IG_HANDLE_PATTERNS = [
    re.compile(r"(?:https?://)?(?:www\.)?instagram\.com/([A-Za-z0-9_.]+)", re.IGNORECASE),
    re.compile(r"(?:https?://)?instagr\.am/([A-Za-z0-9_.]+)", re.IGNORECASE),
]
IG_BLACKLIST = {
    "p", "reel", "reels", "tv", "explore", "accounts", "stories",
    "direct", "developer", "about", "help", "blog", "press",
}


def extract_ig_handle(text):
    """Pull first Instagram handle from a string. Returns lowercase handle or None."""
    if not text:
        return None
    for pat in IG_HANDLE_PATTERNS:
        m = pat.search(text)
        if not m:
            continue
        handle = m.group(1).lower().strip("/?#&. ")
        handle = handle.split("?")[0].split("/")[0]
        if not handle or handle in IG_BLACKLIST or len(handle) < 2:
            continue
        return handle
    return None


def ig_dm_link(handle):
    """Open IG DM with this handle. Works on mobile (opens IG app)."""
    if not handle:
        return ""
    return f"https://ig.me/m/{handle}"


# ---------- LinkedIn helpers ----------
LINKEDIN_URL_PATTERNS = [
    re.compile(r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:company|in|school)/[A-Za-z0-9_\-一-鿿%]+/?", re.IGNORECASE),
]


def extract_linkedin_url(text):
    """Pull first LinkedIn company/profile URL from a text blob."""
    if not text:
        return None
    for pat in LINKEDIN_URL_PATTERNS:
        m = pat.search(text)
        if m:
            url = m.group(0).rstrip("/")
            # Normalise to https://www.linkedin.com/...
            url = re.sub(r"^https?://[a-z]{2,3}\.linkedin\.com", "https://www.linkedin.com", url)
            url = re.sub(r"^https?://linkedin\.com", "https://www.linkedin.com", url)
            return url
    return None


def gen_linkedin_connect_msg(lead, sender_name="TVision"):
    """300-char LinkedIn connection request note (LinkedIn hard cap)."""
    name = lead.get("name", "there")
    niche = lead.get("niche", "")
    # Keep brief, < 300 chars total
    msg = (
        f"Hi! 見你哋做 {name}. 我做 AI workflow consulting 幫 HK SME "
        f"({niche}) 慳 5-10 小時一週。30 分鐘免費 audit interest？"
        f"—{sender_name}"
    )
    return msg[:300]  # hard truncate to be safe


def gen_linkedin_followup_msg(lead, sender_name="TVision",
                               calcom_url="https://cal.com/tvision/ai-workflow-audit"):
    """Longer LinkedIn DM sent after connection accepted."""
    name = lead.get("name", "there")
    script = lead.get("script", "") or ""
    return (
        f"Hi {name}!\n\n"
        f"多謝 connect 😊\n\n"
        f"{script}\n\n"
        f"如果有興趣，揾個方便時間揀：\n{calcom_url}\n\n"
        f"完全免費，唔需要 commit。\n\n"
        f"Thanks,\n{sender_name}"
    )


# ---------- Email helpers ----------
EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
# Substring match against domain — catches subdomains too
EMAIL_BLACKLIST_DOMAIN_SUBSTRINGS = [
    # placeholders
    "example.com", "example.org", "example.net", "mysite.com",
    "domain.com", "yourdomain", "yourcompany", "yoursite",
    # web-host / tracking
    "sentry.io", "sentry-next", "wix.com", "wixpress.com", "wixsite.com",
    "godaddy.com", "squarespace.com", "cloudflare.com",
    "googleapis.com", "gstatic.com", "google-analytics.com",
    "facebook.com", "instagram.com", "twitter.com", "schema.org",
    "wordpress.com", "shopify.com", "stripe.com",
    # third-party SaaS support emails (not the business)
    "schedulista.com", "calendly.com", "intercom.io", "zendesk.com",
    "hubspot.com", "mailchimp.com", "constantcontact.com",
]
# Only allow real TLDs (most common). Anything else = junk.
EMAIL_ALLOWED_TLDS = {
    "com", "org", "net", "edu", "gov", "io", "co", "ai", "app", "dev",
    "hk", "tw", "jp", "sg", "cn", "kr", "my", "th", "vn", "ph",
    "us", "uk", "ca", "au", "nz", "de", "fr", "es", "it", "nl",
    "info", "biz", "asia", "pro", "online", "store", "shop", "tech",
}
EMAIL_BLACKLIST_LOCAL = {
    "noreply", "no-reply", "donotreply", "do-not-reply",
    "user", "username", "name", "email", "yourname", "test", "demo",
}
# File extensions sometimes get parsed as TLD
EMAIL_FAKE_TLDS = {
    "css", "png", "jpg", "jpeg", "gif", "svg", "webp", "ico",
    "js", "ts", "html", "htm", "json", "xml",
    "mp3", "mp4", "wav", "pdf", "zip", "woff", "woff2", "ttf",
}


def extract_email(text):
    """Pull first usable business email from a text blob."""
    if not text:
        return None
    matches = EMAIL_PATTERN.findall(text)
    for m in matches:
        m = m.lower().strip(".,;:'\"")
        local, _, domain = m.partition("@")
        if not domain or "." not in domain:
            continue
        # TLD check — last segment after .
        tld = domain.rsplit(".", 1)[-1]
        if tld in EMAIL_FAKE_TLDS:
            continue
        # Whitelist real TLDs only
        if tld not in EMAIL_ALLOWED_TLDS:
            continue
        # Blacklist substring match in domain
        if any(b in domain for b in EMAIL_BLACKLIST_DOMAIN_SUBSTRINGS):
            continue
        # Blacklist local part
        if local in EMAIL_BLACKLIST_LOCAL:
            continue
        # Sanity: image-filename-like local part with @2x etc
        if re.search(r"@[\d]+x$", "@" + local) or local.endswith(("@2x", "@3x")):
            continue
        if re.match(r"^[a-f0-9]{32,}$", local):  # tracking ID hash
            continue
        if len(local) > 30:  # very long = likely junk
            continue
        return m
    return None


def tel_link(phone):
    """Generate tel: link for click-to-call from Mac FaceTime / iPhone."""
    if not phone:
        return ""
    p = re.sub(r"[^\d+]", "", phone)
    if not p.startswith("+"):
        if p.startswith("852"):
            p = "+" + p
        elif len(p) == 8:
            p = "+852" + p
        else:
            p = "+" + p
    return f"tel:{p}"


def gen_email_template(lead, sender_name="TVision Limited", calcom_url="https://cal.com/tvision/ai-workflow-audit"):
    """Generate email subject + body from a lead's data."""
    name = lead.get("name", "there")
    script = lead.get("script", "") or ""
    subject = f"免費 AI Workflow Audit 畀 {name}"
    body = (
        f"Hi {name}，\n\n"
        f"{script}\n\n"
        f"如果有興趣，直接 click 呢個 link 揀時間：\n"
        f"{calcom_url}\n\n"
        f"完全免費，唔需要 commit 任何嘢。\n\n"
        f"Thanks,\n{sender_name}"
    )
    return subject, body


def mailto_link(email, subject, body):
    if not email:
        return ""
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


# ---------- Bulk email send ----------
def load_resend_config():
    """Load Resend API config. Returns dict or None."""
    key = os.environ.get("RESEND_API_KEY", "")
    if not key or key.startswith("re_xxxx"):
        return None
    return {
        "api_key": key,
        "from_email": os.environ.get("RESEND_FROM_EMAIL") or "onboarding@resend.dev",
        "from_name": os.environ.get("RESEND_FROM_NAME") or "TVision",
    }


def load_gmail_config():
    """Load Gmail SMTP config from env. Returns dict or None."""
    addr = os.environ.get("GMAIL_ADDRESS", "")
    pw = os.environ.get("GMAIL_APP_PASSWORD", "")
    if not addr or not pw or addr.startswith("your.business"):
        return None
    return {
        "address": addr,
        "app_password": pw,
        "sender_name": os.environ.get("GMAIL_SENDER_NAME") or addr.split("@")[0],
    }


def load_email_config():
    """Returns (provider_name, config_dict) — Resend takes priority if both set."""
    r = load_resend_config()
    if r:
        return "resend", r
    g = load_gmail_config()
    if g:
        return "gmail", g
    return None, None


def _send_one_resend(cfg, to_email, to_name, subject, body, unsubscribe_text=""):
    """Send via Resend HTTPS API. Returns (ok, msg)."""
    full_body = body + ("\n\n---\n" + unsubscribe_text if unsubscribe_text else "")
    from_field = f"{cfg['from_name']} <{cfg['from_email']}>"
    to_field = [f"{to_name} <{to_email}>"] if to_name else [to_email]
    try:
        r = requests.post(
            "https://api.resend.com/emails",
            json={
                "from": from_field,
                "to": to_field,
                "subject": subject,
                "text": full_body,
            },
            headers={
                "Authorization": f"Bearer {cfg['api_key']}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if r.status_code in (200, 202):
            return True, "ok"
        return False, f"{r.status_code}: {r.text[:120]}"
    except Exception as e:
        return False, f"{type(e).__name__}: {str(e)[:120]}"


def _send_one_gmail(cfg, to_email, to_name, subject, body, unsubscribe_text=""):
    """Send via Gmail SMTP. Returns (ok, msg)."""
    from gmail_sender import GmailSender
    sender = GmailSender(
        gmail_address=cfg["address"],
        app_password=cfg["app_password"],
        sender_name=cfg["sender_name"],
        delay_seconds=0,  # we handle delay outside
    )
    return sender.send_email(
        to_email=to_email,
        subject=subject,
        body=body,
        to_name=to_name,
        unsubscribe_text=unsubscribe_text,
    )


PDPO_UNSUBSCRIBE_FOOTER = (
    "如果你唔想再收到我哋嘅訊息，"
    "覆「unsubscribe」或者直接無視呢封 email。"
    "我哋唔會再聯絡你。"
    "\n"
    "依據香港《個人資料（私隱）條例》第 35 條，你有權拒絕收到 marketing message。"
)


def bulk_send_email(lead_ids_to_send, progress_callback=None):
    """Send personalized cold email to a list of lead IDs.

    Auto-picks Resend if RESEND_API_KEY set, else Gmail (GMAIL_ADDRESS+APP_PASSWORD),
    else raises.

    Each lead must have a valid `email` field. Skips leads without email.
    Auto-updates status='Sent', last_channel='Email', sent_at=now.
    Sleeps EMAIL_DELAY_SECONDS between sends (5s default).

    Returns (sent, skipped, failed, provider_name) tuple.
    """
    provider, cfg = load_email_config()
    if provider is None:
        raise RuntimeError(
            "No email provider configured. Set RESEND_API_KEY (recommended) or "
            "GMAIL_ADDRESS+GMAIL_APP_PASSWORD in ~/.claude/skills/hksme-cold-outreach/.env"
        )

    delay = float(os.environ.get("EMAIL_DELAY_SECONDS", "5"))
    send_fn = _send_one_resend if provider == "resend" else _send_one_gmail

    conn = get_db()
    sent = 0
    skipped = 0
    failed = 0
    now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    leads = []
    for lid in lead_ids_to_send:
        row = conn.execute(
            "SELECT id, name, email, script, niche FROM leads WHERE id = ?",
            (lid,),
        ).fetchone()
        if not row:
            continue
        if not row["email"]:
            skipped += 1
            continue
        leads.append(dict(row))

    total = len(leads)
    for i, lead in enumerate(leads):
        if progress_callback:
            progress_callback(i, total, lead["name"])
        subject, body = gen_email_template(lead)
        ok, send_msg = send_fn(
            cfg,
            to_email=lead["email"],
            to_name=lead["name"],
            subject=subject,
            body=body,
            unsubscribe_text=PDPO_UNSUBSCRIBE_FOOTER,
        )
        if ok:
            conn.execute(
                "UPDATE leads SET status = 'Sent', last_channel = 'Email', sent_at = ? "
                "WHERE id = ?",
                (now_iso, lead["id"]),
            )
            sent += 1
        else:
            conn.execute(
                "UPDATE leads SET notes = COALESCE(notes,'') || ? WHERE id = ?",
                (f" [email-fail: {send_msg[:60]}]", lead["id"]),
            )
            failed += 1
        conn.commit()
        if i < total - 1:
            time.sleep(delay)

    conn.close()
    return sent, skipped, failed, provider


# ---------- SQLite ----------
SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    phone TEXT UNIQUE NOT NULL,
    name TEXT NOT NULL,
    niche TEXT,
    area TEXT,
    address TEXT,
    rating REAL,
    reviews INTEGER,
    categories TEXT,
    website TEXT,
    script TEXT,
    wa_deeplink TEXT,
    ig_handle TEXT,
    fb_page TEXT,
    email TEXT,
    last_channel TEXT,
    status TEXT DEFAULT 'Drafted',
    sent_at TEXT,
    replied INTEGER DEFAULT 0,
    booked_demo INTEGER DEFAULT 0,
    notes TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_niche ON leads(niche);
"""

def _migrate_schema(conn):
    """Add new columns to existing DBs without dropping data."""
    cols = {r[1] for r in conn.execute("PRAGMA table_info(leads)").fetchall()}
    for col, ddl in [
        ("email", "ALTER TABLE leads ADD COLUMN email TEXT"),
        ("last_channel", "ALTER TABLE leads ADD COLUMN last_channel TEXT"),
        ("linkedin_url", "ALTER TABLE leads ADD COLUMN linkedin_url TEXT"),
    ]:
        if col not in cols:
            conn.execute(ddl)


def get_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    _migrate_schema(conn)
    conn.commit()
    return conn


# ---------- Pipeline ----------
ALLOWED_UPDATE_COLS = {"status", "sent_at", "replied", "booked_demo", "notes", "ig_handle", "fb_page", "script", "email", "last_channel", "linkedin_url"}


def extract_contacts_from_website(website_url, timeout=8):
    """Fetch website HTML once, extract email + ig_handle + linkedin_url.
    Returns dict with those 3 keys (values None if not found / website unreachable)."""
    out = {"email": None, "ig_handle": None, "linkedin_url": None}
    if not website_url:
        return out
    try:
        r = requests.get(
            website_url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            allow_redirects=True,
        )
        html = r.text or ""
    except Exception:
        return out
    out["email"] = extract_email(html)
    out["ig_handle"] = extract_ig_handle(html)
    out["linkedin_url"] = extract_linkedin_url(html)
    return out


def discover_and_draft(niche, area, count, mode, apify_token, gemini_key, progress_callback=None, scrape_progress_callback=None):
    """Run scrape + filter + extract contacts + draft + insert pipeline. Returns (inserted, skipped_dup)."""
    raw = scrape_gmaps(niche, area, count, apify_token, scrape_progress_callback)
    filtered = filter_results(raw, count)

    conn = get_db()
    inserted = 0
    skipped = 0

    for i, biz in enumerate(filtered):
        if progress_callback:
            progress_callback(i, len(filtered), biz["name"])

        # Single website fetch → extract email + IG + LinkedIn
        contacts = extract_contacts_from_website(biz.get("website"))

        script = draft_message(biz, niche, mode, gemini_key)
        link_text = script if mode == "text" else "Hi！我啱啱 send 咗個 voice memo 你，得閒聽吓 :)"
        deeplink = wa_deeplink(biz["phone"], link_text)

        try:
            conn.execute(
                """
                INSERT INTO leads
                (phone, name, niche, area, address, rating, reviews, categories, website,
                 script, wa_deeplink, email, ig_handle, linkedin_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    biz["phone"], biz["name"], niche, area, biz["address"],
                    biz["rating"], biz["reviews"], biz["categories"], biz["website"],
                    script, deeplink,
                    contacts["email"], contacts["ig_handle"], contacts["linkedin_url"],
                ),
            )
            inserted += 1
        except sqlite3.IntegrityError:
            skipped += 1

        # Gemini free tier = 15 RPM. Sleep 4.5s between calls = ~13 RPM safe.
        time.sleep(4.5)

    conn.commit()
    conn.close()
    return inserted, skipped


def backfill_contacts(progress_callback=None):
    """Run extract_contacts on all leads missing email/ig/linkedin. Updates DB.
    Returns (touched, email_added, ig_added, linkedin_added)."""
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, website, email, ig_handle, linkedin_url FROM leads "
        "WHERE website IS NOT NULL AND website != '' "
        "AND (email IS NULL OR ig_handle IS NULL OR linkedin_url IS NULL)"
    ).fetchall()
    touched = 0
    em_n = ig_n = li_n = 0
    for i, row in enumerate(rows):
        if progress_callback:
            progress_callback(i, len(rows), row["name"])
        contacts = extract_contacts_from_website(row["website"])
        updates = {}
        if not row["email"] and contacts["email"]:
            updates["email"] = contacts["email"]
            em_n += 1
        if not row["ig_handle"] and contacts["ig_handle"]:
            updates["ig_handle"] = contacts["ig_handle"]
            ig_n += 1
        if not row["linkedin_url"] and contacts["linkedin_url"]:
            updates["linkedin_url"] = contacts["linkedin_url"]
            li_n += 1
        if updates:
            sets = ", ".join(f"{k} = ?" for k in updates)
            conn.execute(f"UPDATE leads SET {sets} WHERE id = ?", list(updates.values()) + [row["id"]])
            touched += 1
    conn.commit()
    conn.close()
    return touched, em_n, ig_n, li_n


def get_leads(status_filter=None, niche_filter=None, search=None, limit=500):
    conn = get_db()
    q = "SELECT * FROM leads WHERE 1=1"
    params = []
    if status_filter:
        placeholders = ",".join("?" * len(status_filter))
        q += f" AND status IN ({placeholders})"
        params.extend(status_filter)
    if niche_filter:
        placeholders = ",".join("?" * len(niche_filter))
        q += f" AND niche IN ({placeholders})"
        params.extend(niche_filter)
    if search:
        q += " AND name LIKE ?"
        params.append(f"%{search}%")
    q += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    rows = [dict(r) for r in conn.execute(q, params).fetchall()]
    conn.close()
    return rows


def update_lead(lead_id, **fields):
    fields = {k: v for k, v in fields.items() if k in ALLOWED_UPDATE_COLS}
    if not fields:
        return
    conn = get_db()
    sets = ", ".join(f"{k} = ?" for k in fields)
    conn.execute(f"UPDATE leads SET {sets} WHERE id = ?", list(fields.values()) + [lead_id])
    conn.commit()
    conn.close()


def is_problematic_script(script):
    """Detect truncated, errored, or low-quality scripts that should be redrafted."""
    if not script or not isinstance(script, str):
        return True
    s = script.strip()
    if s.startswith("[ERROR"):
        return True
    if len(s) < 50:  # too short to be a complete cold DM
        return True
    # Complete scripts should end with sentence punctuation / closing bracket / emoji
    end_chars = "?？!！。.)）」』😊🙂😉🤝👍✨"
    if not any(s.endswith(c) for c in end_chars):
        return True
    return False


def redraft_errored(gemini_key, mode="text", progress_callback=None):
    """Re-run Gemini for any leads with problematic (errored OR truncated) scripts.
    Returns (succeeded, still_failed)."""
    conn = get_db()
    all_rows = conn.execute(
        "SELECT id, name, niche, address, rating, reviews, phone, script FROM leads"
    ).fetchall()
    rows = [r for r in all_rows if is_problematic_script(r["script"])]
    succeeded = 0
    still_failed = 0
    for i, row in enumerate(rows):
        if progress_callback:
            progress_callback(i, len(rows), row["name"])
        biz = {
            "name": row["name"],
            "address": row["address"] or "",
            "rating": row["rating"] or 0,
            "reviews": row["reviews"] or 0,
            "phone": row["phone"],
        }
        script = draft_message(biz, row["niche"] or "美容", mode, gemini_key)
        if script.startswith("[ERROR"):
            still_failed += 1
        else:
            link_text = script if mode == "text" else "Hi！我啱啱 send 咗個 voice memo 你，得閒聽吓 :)"
            deeplink = wa_deeplink(row["phone"], link_text)
            conn.execute(
                "UPDATE leads SET script = ?, wa_deeplink = ? WHERE id = ?",
                (script, deeplink, row["id"]),
            )
            succeeded += 1
        # Free tier rate limit safety
        time.sleep(4.5)
    conn.commit()
    conn.close()
    return succeeded, still_failed


# ---------- Auto-discover background daemon controls ----------
def _ad_atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(data)
    tmp.replace(path)


def is_auto_discover_running():
    """Return (running_bool, pid_or_None)."""
    if not AUTO_DISCOVER_PID_FILE.exists():
        return False, None
    try:
        pid = int(AUTO_DISCOVER_PID_FILE.read_text().strip())
    except (ValueError, OSError):
        AUTO_DISCOVER_PID_FILE.unlink(missing_ok=True)
        return False, None
    try:
        os.kill(pid, 0)  # signal 0 = check process exists
        return True, pid
    except ProcessLookupError:
        AUTO_DISCOVER_PID_FILE.unlink(missing_ok=True)
        return False, None
    except PermissionError:
        return True, pid  # exists but not ours


def start_auto_discover(queue):
    """Spawn auto_discover.py as detached subprocess. Returns PID."""
    AUTO_DISCOVER_QUEUE_FILE.parent.mkdir(parents=True, exist_ok=True)
    _ad_atomic_write(AUTO_DISCOVER_QUEUE_FILE, json.dumps(queue, indent=2))
    AUTO_DISCOVER_LOG_FILE.write_text("")  # clear log
    _ad_atomic_write(AUTO_DISCOVER_STATUS_FILE, json.dumps({"starting": True}))

    script = SKILL_DIR / "auto_discover.py"
    venv_python = SKILL_DIR / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else "python3"
    proc = subprocess.Popen(
        [python, str(script)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        start_new_session=True,  # detach so it survives portal restart
        cwd=str(SKILL_DIR),
    )
    return proc.pid


def stop_auto_discover():
    """Kill background auto-discover. Returns True if was running."""
    running, pid = is_auto_discover_running()
    if not running or pid is None:
        return False
    try:
        os.kill(pid, signal.SIGTERM)
        time.sleep(0.5)
        # if still alive, force kill
        try:
            os.kill(pid, 0)
            os.kill(pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
    except Exception:
        return False
    AUTO_DISCOVER_PID_FILE.unlink(missing_ok=True)
    return True


def get_auto_discover_status():
    """Read current status JSON + last 20 log lines. Returns (status_dict, log_tail_str)."""
    status = {}
    if AUTO_DISCOVER_STATUS_FILE.exists():
        try:
            status = json.loads(AUTO_DISCOVER_STATUS_FILE.read_text())
        except (json.JSONDecodeError, OSError):
            pass
    log_tail = ""
    if AUTO_DISCOVER_LOG_FILE.exists():
        try:
            lines = AUTO_DISCOVER_LOG_FILE.read_text().splitlines()
            log_tail = "\n".join(lines[-20:])
        except OSError:
            pass
    return status, log_tail


def get_stats():
    conn = get_db()
    cur = conn.cursor()

    total = cur.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    sent = cur.execute("SELECT COUNT(*) FROM leads WHERE status IN ('Sent','Replied','Booked','Done')").fetchone()[0]
    replied = cur.execute("SELECT COUNT(*) FROM leads WHERE replied = 1").fetchone()[0]
    booked = cur.execute("SELECT COUNT(*) FROM leads WHERE booked_demo = 1").fetchone()[0]

    by_niche = {r["niche"]: r["c"] for r in cur.execute("SELECT niche, COUNT(*) AS c FROM leads GROUP BY niche").fetchall()}
    by_status = {r["status"]: r["c"] for r in cur.execute("SELECT status, COUNT(*) AS c FROM leads GROUP BY status").fetchall()}

    reply_rate = (replied / sent * 100) if sent > 0 else 0
    booking_rate = (booked / sent * 100) if sent > 0 else 0

    conn.close()
    return {
        "total": total,
        "sent": sent,
        "replied": replied,
        "booked": booked,
        "by_niche": by_niche,
        "by_status": by_status,
        "reply_rate": reply_rate,
        "booking_rate": booking_rate,
    }
