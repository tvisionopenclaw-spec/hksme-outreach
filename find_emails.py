"""Find business email for each lead by fetching their website and extracting email patterns.

Run: python3 find_emails.py
"""
import sys
import re
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import requests
import lib

# Pages where email is most commonly published
CONTACT_PATHS = ["", "/contact", "/contact-us", "/about", "/about-us", "/contactus"]


def fetch_html(url, timeout=8):
    try:
        r = requests.get(
            url,
            timeout=timeout,
            headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"},
            allow_redirects=True,
        )
        return r.text or ""
    except Exception:
        return ""


def normalize_base(url):
    """Strip trailing slash, get scheme+host."""
    if not url:
        return ""
    url = url.strip()
    if not url.startswith("http"):
        url = "http://" + url
    # Find host root
    m = re.match(r"^(https?://[^/]+)", url)
    return m.group(1) if m else url


def find_email_for_lead(lead):
    website = lead.get("website") or ""
    if not website:
        return None, "no-website"

    # Try the original URL first
    html = fetch_html(website)
    if html:
        em = lib.extract_email(html)
        if em:
            return em, "main-page"

    # Try common contact paths under same host
    base = normalize_base(website)
    if not base:
        return None, "bad-url"
    for path in CONTACT_PATHS[1:]:  # skip "" since we already tried
        html = fetch_html(base + path)
        if html:
            em = lib.extract_email(html)
            if em:
                return em, f"path:{path}"

    return None, "not-found"


def main():
    leads = lib.get_leads(limit=200)
    conn = lib.get_db()
    found = 0
    for l in leads:
        if l.get("email"):
            print(f"⏭️  [{l['id']}] {l['name'][:35]:35} | already has {l['email']}")
            continue
        email, reason = find_email_for_lead(l)
        if email:
            conn.execute("UPDATE leads SET email = ? WHERE id = ?", (email, l["id"]))
            found += 1
            print(f"✅ [{l['id']}] {l['name'][:35]:35} | {email:30} ({reason})")
        else:
            print(f"❌ [{l['id']}] {l['name'][:35]:35} | ({reason})")
    conn.commit()
    conn.close()
    print(f"\nFound email for {found}/{len(leads)} leads")


if __name__ == "__main__":
    main()
