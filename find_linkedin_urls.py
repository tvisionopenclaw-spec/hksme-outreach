"""Find LinkedIn company URL for each lead by scraping their website.

Run: python3 find_linkedin_urls.py
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import requests
import lib


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


def find_linkedin_for_lead(lead):
    website = lead.get("website") or ""
    if not website:
        return None, "no-website"
    html = fetch_html(website)
    if not html:
        return None, "fetch-failed"
    url = lib.extract_linkedin_url(html)
    if url:
        return url, "found-in-html"
    return None, "not-found"


def main():
    leads = lib.get_leads(limit=200)
    conn = lib.get_db()
    found = 0
    for l in leads:
        if l.get("linkedin_url"):
            print(f"⏭️  [{l['id']}] {l['name'][:35]:35} | already has {l['linkedin_url'][:60]}")
            continue
        url, reason = find_linkedin_for_lead(l)
        if url:
            conn.execute("UPDATE leads SET linkedin_url = ? WHERE id = ?", (url, l["id"]))
            found += 1
            print(f"✅ [{l['id']}] {l['name'][:35]:35} | {url[:60]} ({reason})")
        else:
            print(f"❌ [{l['id']}] {l['name'][:35]:35} | ({reason})")
    conn.commit()
    conn.close()
    print(f"\nFound LinkedIn URL for {found}/{len(leads)} leads")


if __name__ == "__main__":
    main()
