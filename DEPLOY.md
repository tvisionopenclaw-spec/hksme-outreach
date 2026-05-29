# Deploy to Streamlit Community Cloud

## ⚠️ Tradeoffs

| | Local (`launch.sh`) | Streamlit Cloud |
|---|---|---|
| 📞 Phone Mode | ✅ | ✅ (call from phone) |
| 📥 Inbox + status update | ✅ | ✅ |
| 📨 Bulk Send (Resend / Gmail) | ✅ | ✅ |
| 🤖 Auto-Discover daemon | ✅ | ❌ Disabled (no subprocess) |
| 📡 Manual Discover scrape | ✅ | ✅ (synchronous, takes 5-8 min per scrape — page stays open) |
| 💾 SQLite persistence | ✅ Permanent | ❌ Resets when container restarts |
| 🔐 API keys location | `.env` local | `secrets.toml` on Streamlit Cloud (encrypted) |
| Mac on required? | ✅ Yes | ❌ Anywhere |

**Strategy**: use BOTH.
- Local Mac = primary workspace (Auto-Discover daemon + persistent DB)
- Streamlit Cloud = phone-only quick checks + send buttons when out of office

For persistent cloud DB → migrate SQLite → Supabase Postgres (out of scope for v1).

---

## Step 1 — Create GitHub repo

```bash
cd ~/.claude/skills/hksme-cold-outreach
git init
git add .gitignore .streamlit/secrets.toml.example DEPLOY.md \
        SKILL.md README.md \
        lib.py portal.py auto_discover.py gmail_sender.py \
        find_emails.py find_ig_handles.py find_linkedin_urls.py \
        handcraft_scripts.py launch.sh requirements.txt
git commit -m "Initial portal for Streamlit Cloud deploy"

# Create repo on GitHub (use gh CLI or web)
gh repo create hksme-outreach --private --source=. --remote=origin --push
# OR web: github.com/new → create → follow push instructions
```

**⚠️ verify `.env` is NOT committed:**
```bash
git ls-files | grep -i env
# Should show: .env.example (OK) + .streamlit/secrets.toml.example (OK)
# Should NOT show: .env or .streamlit/secrets.toml
```

## Step 2 — Set up Streamlit Cloud

1. Go to [share.streamlit.io](https://share.streamlit.io) → sign in with GitHub
2. Click **"Create app"** → "Deploy a public app from GitHub"
3. Repository: select your `hksme-outreach` repo
4. Branch: `main`
5. Main file path: `portal.py`
6. App URL: pick a name like `your-name-hksme-outreach`
7. **Don't deploy yet** — click "Advanced settings"

## Step 3 — Configure secrets

In Advanced settings → **Secrets** field, paste this (replacing values):

```toml
PORTAL_PASSWORD = "use-a-strong-password-only-you-know"

APIFY_TOKEN = "apify_api_xxxxxxxxxxxxxxxxxxxx"  # paste from your .env
GEMINI_API_KEY = "AIzaSy-xxxxxxxxxxxxxxxxxx"   # paste from your .env

# Optional - only if using email
RESEND_API_KEY = "re_xxxxx"
RESEND_FROM_EMAIL = "onboarding@resend.dev"
RESEND_FROM_NAME = "Your Name"

EMAIL_DELAY_SECONDS = "5"
```

Click **Save** then **Deploy**.

## Step 4 — Wait + access

- First deploy: 3-5 min
- You'll get URL: `https://your-name-hksme-outreach.streamlit.app`
- Open on phone → enter password → use it
- Bookmark on phone home screen

## Step 5 — Daily workflow

**Local Mac (primary):**
```bash
~/.claude/skills/hksme-cold-outreach/launch.sh
```
Run Auto-Discover daemon to keep scraping leads. Make phone calls via Phone Mode.

**Phone (secondary):**
Open Streamlit Cloud URL from anywhere. View leads, click "Send →", update status. **NB**: phone changes don't sync to local DB and vice versa (separate DBs).

For sync: export CSV from one, import to other manually.

## Updating the deployed app

```bash
cd ~/.claude/skills/hksme-cold-outreach
git add lib.py portal.py  # whatever you changed
git commit -m "Update: short description"
git push
# Streamlit Cloud auto-redeploys in ~1 min
```

## Troubleshooting

- **"App is in the oven"** → still deploying, wait
- **App crashes** → check logs in Streamlit Cloud dashboard
- **Password not asking** → secret `PORTAL_PASSWORD` not set
- **API key errors** → check secrets format (TOML, double quotes)
- **Page slow** → Apify scrape is synchronous on cloud (no daemon), takes 5-8 min — be patient
- **DB has no leads** → container restarted, DB reset. Run a Discover OR import CSV.

## Best practice: Keep local & cloud separate

Treat cloud as "phone companion view" — read + click send.
Treat local as "workshop" — Auto-Discover + persistent DB + Phone Mode + analytics.

Export CSV daily from local for offline backup.
