"""Find IG handle for each lead by:
1. Check if `website` field IS an IG URL directly
2. Otherwise fetch website HTML and extract IG link from it

Run: python3 find_ig_handles.py
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
        return r.text
    except Exception:
        return ""


def find_handle_for_lead(lead):
    website = lead.get("website") or ""
    # 1. Maybe website itself IS an IG URL
    h = lib.extract_ig_handle(website)
    if h:
        return h, "website-is-ig"
    # 2. Fetch website HTML, look for IG link inside
    if website:
        html = fetch_html(website)
        if html:
            h = lib.extract_ig_handle(html)
            if h:
                return h, "found-in-html"
    return None, "not-found"


def main():
    leads = lib.get_leads(limit=200)
    conn = lib.get_db()
    found = 0
    for l in leads:
        if l.get("ig_handle"):
            print(f"⏭️  [{l['id']}] {l['name'][:35]:35} | already has @{l['ig_handle']}")
            continue
        handle, reason = find_handle_for_lead(l)
        if handle:
            conn.execute("UPDATE leads SET ig_handle = ? WHERE id = ?", (handle, l["id"]))
            found += 1
            print(f"✅ [{l['id']}] {l['name'][:35]:35} | @{handle:20} ({reason})")
        else:
            print(f"❌ [{l['id']}] {l['name'][:35]:35} | ({reason})")
    conn.commit()
    conn.close()
    print(f"\nFound IG handle for {found}/{len(leads)} leads")


if __name__ == "__main__":
    main()
