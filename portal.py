"""
HK SME Cold Outreach Portal — Streamlit web UI.

Launch:
    streamlit run ~/.claude/skills/hksme-cold-outreach/portal.py

Then open http://localhost:8501.
"""
import hmac
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

# Detect Streamlit Cloud vs local
IS_CLOUD = bool(
    os.environ.get("STREAMLIT_SHARING")
    or os.environ.get("STREAMLIT_SERVER_PORT") == "8501"
    and "/mount/src/" in str(Path(__file__).resolve())
    or "/mount/src/" in str(Path(__file__).resolve())
)


def _populate_env_from_secrets():
    """On Streamlit Cloud, secrets live in st.secrets. Mirror them into os.environ
    so existing lib.load_env() / lib.load_resend_config() etc. work unchanged."""
    try:
        for k, v in st.secrets.items():
            if isinstance(v, str) and k not in os.environ:
                os.environ[k] = v
    except Exception:
        pass


_populate_env_from_secrets()


def _check_password() -> bool:
    """Render a password gate. Returns True if user is authenticated."""
    # No password configured = open access (local dev only)
    expected = os.environ.get("PORTAL_PASSWORD")
    if not expected:
        return True

    if st.session_state.get("password_correct"):
        return True

    def _on_submit():
        entered = st.session_state.get("password_input", "")
        if hmac.compare_digest(entered, expected):
            st.session_state["password_correct"] = True
            st.session_state.pop("password_input", None)
        else:
            st.session_state["password_correct"] = False

    st.title("📱 HK SME Outreach")
    st.text_input(
        "Password", type="password", key="password_input", on_change=_on_submit,
    )
    if st.session_state.get("password_correct") is False:
        st.error("Wrong password")
    st.stop()


_check_password()

import lib

st.set_page_config(
    page_title="HK SME Outreach",
    page_icon="📱",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Init DB
lib.get_db()

# ---------- Sidebar ----------
st.sidebar.title("📱 HK SME Outreach")
if IS_CLOUD:
    st.sidebar.warning(
        "🌐 Cloud mode\n\n"
        "⚠️ DB resets on container restart — export CSV often!\n\n"
        "⚠️ Auto-Discover daemon disabled.\n\n"
        "✅ Phone Mode + Inbox + send buttons work."
    )
page = st.sidebar.radio("Page", ["📡 Discover", "📥 Inbox", "📞 Phone Mode", "🤖 Auto-Discover", "📊 Stats"])

# Show background auto-discover status as a sidebar badge
_ad_running, _ad_pid = lib.is_auto_discover_running()
if _ad_running:
    _ad_status, _ = lib.get_auto_discover_status()
    completed = _ad_status.get("completed_jobs", 0)
    total = _ad_status.get("total_jobs", 0)
    inserted = _ad_status.get("total_inserted", 0)
    st.sidebar.success(
        f"🤖 Auto-Discover RUNNING\n\n"
        f"Job {completed}/{total} done\n\n"
        f"{inserted} new leads added"
    )

apify_token, gemini_key = lib.load_env()
env_ok = bool(apify_token and gemini_key)

if env_ok:
    st.sidebar.success("✅ API keys loaded")
else:
    st.sidebar.error(
        "⚠️ Missing .env\n"
        "Set APIFY_TOKEN + GEMINI_API_KEY in\n"
        "`~/.claude/skills/hksme-cold-outreach/.env`"
    )

st.sidebar.markdown("---")
st.sidebar.caption("💡 Cap 50-100 sends/day from one WA number to avoid ban.")
st.sidebar.caption("💡 Use SEPARATE WA Business — not personal, not SocialAuto.")


# ========== DISCOVER ==========
if page == "📡 Discover":
    st.title("📡 Discover & Draft new leads")
    st.caption("Scrape Google Maps + draft Cantonese WhatsApp scripts in one click.")

    if not env_ok:
        st.warning("⚠️ Set your API keys first (see sidebar).")

    with st.form("discover_form"):
        c1, c2, c3, c4 = st.columns([2, 2, 2, 2])
        with c1:
            niche = st.selectbox("Niche", list(lib.NICHES.keys()), index=2)  # default 美容
        with c2:
            area = st.text_input("Area", "銅鑼灣", help="e.g. 觀塘 / 旺角 / 銅鑼灣 / 尖沙咀")
        with c3:
            count = st.slider("Count", min_value=20, max_value=300, value=100, step=10)
        with c4:
            mode = st.radio(
                "Mode",
                ["text", "voice"],
                horizontal=True,
                help="text = pre-filled WA DM (5 sec/send). voice = script to read aloud (45 sec/send, higher reply).",
            )

        submitted = st.form_submit_button(
            "🚀 Run scrape + draft",
            disabled=not env_ok,
            type="primary",
            use_container_width=True,
        )

    if submitted and env_ok:
        progress = st.progress(0.0, text="Scraping Google Maps via Apify (this can take 2-5 min)...")

        def draft_cb(i, total, name):
            progress.progress((i + 1) / total, text=f"[{i + 1}/{total}] Drafting: {name[:40]}")

        def scrape_cb(done, total, elapsed, status):
            pct = 0.0
            if total and total > 0:
                pct = min(0.95, done / total)  # cap at 95% so drafting can take over
            msg = f"🛰️ Apify scrape: {done}/{total or '?'} places | elapsed {elapsed}s | status: {status}"
            progress.progress(pct, text=msg)

        try:
            with st.spinner("Running..."):
                inserted, skipped = lib.discover_and_draft(
                    niche, area, count, mode, apify_token, gemini_key,
                    progress_callback=draft_cb,
                    scrape_progress_callback=scrape_cb,
                )
            progress.empty()
            st.success(f"✅ {inserted} new leads added to Inbox | {skipped} duplicates skipped")
            st.balloons()
        except Exception as e:
            progress.empty()
            # sanitize error: strip API token if present
            err_str = str(e)
            import re as _re
            err_str = _re.sub(r"token=[A-Za-z0-9_]+", "token=***", err_str)
            err_str = _re.sub(r"apify_api_[A-Za-z0-9]+", "apify_api_***", err_str)
            err_str = _re.sub(r"AIza[A-Za-z0-9_-]+", "AIza***", err_str)
            st.error(f"Failed: {err_str}")

    st.markdown("---")
    st.subheader("Recent 5 leads")
    recent = lib.get_leads(limit=5)
    if recent:
        st.dataframe(
            pd.DataFrame(recent)[["name", "niche", "area", "rating", "status", "created_at"]],
            hide_index=True,
            use_container_width=True,
        )
    else:
        st.info("No leads yet. Run a discover above to start.")


# ========== INBOX ==========
elif page == "📥 Inbox":
    st.title("📥 Inbox")
    st.caption("Click 'Send →' to open WhatsApp with pre-filled message. Then mark status here.")

    # Filters
    c1, c2, c3 = st.columns(3)
    with c1:
        status_filter = st.multiselect(
            "Status",
            ["Drafted", "Sent", "Conn Sent", "Connected", "Replied", "Booked", "Done", "Skip"],
            default=["Drafted"],
        )
    with c2:
        niche_filter = st.multiselect("Niche", list(lib.NICHES.keys()))
    with c3:
        search = st.text_input("🔍 Search by name", "")

    leads = lib.get_leads(
        status_filter=status_filter or None,
        niche_filter=niche_filter or None,
        search=search or None,
    )

    st.caption(f"{len(leads)} leads matching filters")

    # === Backfill contacts (email / IG / LinkedIn) from websites ===
    conn_bf = lib.get_db()
    missing = conn_bf.execute(
        "SELECT COUNT(*) FROM leads WHERE website IS NOT NULL AND website != '' "
        "AND (email IS NULL OR ig_handle IS NULL OR linkedin_url IS NULL)"
    ).fetchone()[0]
    conn_bf.close()
    if missing > 0:
        bf1, bf2 = st.columns([3, 1])
        with bf1:
            st.info(
                f"🔍 {missing} leads missing email / IG / LinkedIn — auto-scrape from their websites (~{missing * 5}s)"
            )
        with bf2:
            if st.button(f"🔍 Backfill {missing}", use_container_width=True):
                prog = st.progress(0.0, text="Fetching websites...")

                def bf_cb(j, total, name):
                    prog.progress((j + 1) / total, text=f"[{j + 1}/{total}] {name[:30]}")

                t, em, ig, li = lib.backfill_contacts(bf_cb)
                prog.empty()
                st.success(f"✅ {t} leads updated | +{em} emails | +{ig} IG | +{li} LinkedIn")
                st.session_state.pop("inbox_df", None)
                st.session_state.pop("inbox_df_id_set", None)
                st.rerun()

    # === Bulk Email Send (Resend or Gmail, PDPO compliant) ===
    email_provider, email_cfg = lib.load_email_config()
    leads_with_email = [l for l in leads if l.get("email") and l.get("status") == "Drafted"]
    if leads_with_email:
        delay = float(os.environ.get("EMAIL_DELAY_SECONDS", "5"))
        bc1, bc2 = st.columns([3, 1])
        with bc1:
            est_sec = len(leads_with_email) * delay
            if email_provider:
                provider_label = "Resend API" if email_provider == "resend" else "Gmail SMTP"
                st.info(
                    f"📧 **{len(leads_with_email)}** drafted leads have email & ready to bulk send "
                    f"via **{provider_label}** (~{int(est_sec)}s @ {delay}s/send). "
                    f"PDPO unsubscribe footer auto-added."
                )
            else:
                st.warning(
                    "📧 Bulk send disabled — add `RESEND_API_KEY` (recommended) or "
                    "`GMAIL_ADDRESS`+`GMAIL_APP_PASSWORD` to `.env`. "
                    "Resend signup: https://resend.com (2 min)"
                )
        with bc2:
            if st.button(
                f"📨 Bulk Send {len(leads_with_email)}",
                use_container_width=True,
                disabled=not email_provider,
                type="primary",
            ):
                provider_name = "Resend" if email_provider == "resend" else "Gmail"
                progress = st.progress(0.0, text=f"Connecting to {provider_name}...")
                ids_to_send = [l["id"] for l in leads_with_email]

                def email_cb(i, total, name):
                    progress.progress((i + 1) / total, text=f"[{i+1}/{total}] Sending to {name[:40]}")

                try:
                    sent, skipped, failed, prov = lib.bulk_send_email(
                        ids_to_send, progress_callback=email_cb
                    )
                    progress.empty()
                    st.success(f"✅ {sent} sent via {prov} | {skipped} skipped (no email) | {failed} failed")
                    if sent > 0:
                        st.balloons()
                    st.session_state.pop("inbox_df", None)
                    st.session_state.pop("inbox_df_id_set", None)
                    st.rerun()
                except Exception as e:
                    progress.empty()
                    err = str(e)
                    import re as _re
                    err = _re.sub(r"re_[A-Za-z0-9_]+", "re_***", err)
                    err = _re.sub(r"app_password\W+\w+", "app_password=***", err)
                    st.error(f"Bulk send failed: {err}")

    # Surface problematic scripts (errored OR truncated) at top of inbox with retry button
    conn = lib.get_db()
    all_db = conn.execute("SELECT script FROM leads").fetchall()
    conn.close()
    problem_count = sum(1 for r in all_db if lib.is_problematic_script(r["script"]))
    if problem_count > 0:
        ec1, ec2 = st.columns([3, 1])
        with ec1:
            st.warning(
                f"⚠️ {problem_count} script(s) need redraft (errored or truncated by Gemini thinking mode)."
                f" Click to retry — uses 13 RPM safe rate, takes ~{problem_count * 5}s."
            )
        with ec2:
            if st.button(f"🔄 Redraft {problem_count}", use_container_width=True):
                if not env_ok:
                    st.error("Set API keys first.")
                else:
                    rprog = st.progress(0.0, text="Redrafting errored scripts...")

                    def rcb(i, total, name):
                        rprog.progress((i + 1) / total, text=f"[{i+1}/{total}] Redrafting: {name[:40]}")

                    ok, fail = lib.redraft_errored(gemini_key, mode="text", progress_callback=rcb)
                    rprog.empty()
                    if ok > 0:
                        st.success(f"✅ Redrafted {ok} | still failed: {fail}")
                    else:
                        st.error(f"All {fail} still failed — Gemini quota may be hit. Try again in a few minutes.")
                    st.session_state.pop("inbox_df", None)
                    st.session_state.pop("inbox_df_id_set", None)
                    st.rerun()

    if not leads:
        st.info("No leads. Try different filters or run a Discover.")
    else:
        df = pd.DataFrame(leads)
        # Compute channel deeplink columns
        df["phone_call"] = df["phone"].apply(lambda p: lib.tel_link(p) if p else "")
        df["ig_dm_link"] = df["ig_handle"].apply(lambda h: lib.ig_dm_link(h) if h else "")

        def _mailto_for_row(row):
            if not row.get("email"):
                return ""
            subject, body = lib.gen_email_template(row)
            return lib.mailto_link(row["email"], subject, body)

        df["email_mailto"] = df.apply(_mailto_for_row, axis=1)

        cols_order = [
            "id", "name", "niche", "area", "rating", "reviews",
            "script",
            "phone_call", "email_mailto", "ig_dm_link", "linkedin_url", "wa_deeplink",
            "email", "ig_handle",
            "status", "last_channel", "replied", "booked_demo",
            "notes", "sent_at",
        ]
        df = df[[c for c in cols_order if c in df.columns]]

        # Cache original snapshot for diff
        current_id_set = set(df["id"])
        if (
            "inbox_df" not in st.session_state
            or st.session_state.get("inbox_df_id_set") != current_id_set
        ):
            st.session_state.inbox_df = df.copy()
            st.session_state.inbox_df_id_set = current_id_set

        edited_df = st.data_editor(
            df,
            hide_index=True,
            num_rows="fixed",
            use_container_width=True,
            column_config={
                "id": st.column_config.NumberColumn("ID", disabled=True, width="small"),
                "name": st.column_config.TextColumn("Name", disabled=True, width="medium"),
                "niche": st.column_config.TextColumn("Niche", disabled=True, width="small"),
                "area": st.column_config.TextColumn("Area", disabled=True, width="small"),
                "rating": st.column_config.NumberColumn("⭐", disabled=True, format="%.1f", width="small"),
                "reviews": st.column_config.NumberColumn("Reviews", disabled=True, width="small"),
                "script": st.column_config.TextColumn("Script (editable)", width="large"),
                "phone_call": st.column_config.LinkColumn("📞", display_text="Call →", width="small", help="Click-to-call (FaceTime on Mac, dialer on phone)"),
                "email_mailto": st.column_config.LinkColumn("📧", display_text="Mail →", width="small", help="Opens default email client with pre-filled subject + body"),
                "ig_dm_link": st.column_config.LinkColumn("📱", display_text="IG →", width="small", help="Opens IG DM (mobile only)"),
                "linkedin_url": st.column_config.LinkColumn("🔗", display_text="LinkedIn →", width="small", help="Opens LinkedIn page — manually click Connect + paste request"),
                "wa_deeplink": st.column_config.LinkColumn("💬", display_text="WA →", width="small", help="⚠️ HIGH BAN RISK — use sparingly, max 5/day"),
                "email": st.column_config.TextColumn("Email", width="medium", help="Editable — paste business email if missing"),
                "ig_handle": st.column_config.TextColumn("IG @", width="small", help="Editable — paste IG username if missing"),
                "status": st.column_config.SelectboxColumn(
                    "Status",
                    options=["Drafted", "Sent", "Conn Sent", "Connected", "Replied", "Booked", "Done", "Skip"],
                    width="small",
                ),
                "last_channel": st.column_config.SelectboxColumn(
                    "Via",
                    options=["", "Phone", "Email", "IG", "LinkedIn", "WA", "Multi"],
                    width="small",
                    help="Which channel was last used to reach this lead",
                ),
                "replied": st.column_config.CheckboxColumn("Reply?", width="small"),
                "booked_demo": st.column_config.CheckboxColumn("Book?", width="small"),
                "notes": st.column_config.TextColumn("Notes", width="medium"),
                "sent_at": st.column_config.TextColumn("Sent At", disabled=True, width="small"),
            },
            key="inbox_editor",
        )

        c1, c2, c3 = st.columns([1, 1, 2])
        with c1:
            save_clicked = st.button("💾 Save changes", type="primary", use_container_width=True)
        with c2:
            mark_all_sent = st.button("✅ Mark visible as Sent", use_container_width=True)
        with c3:
            csv_bytes = edited_df.to_csv(index=False).encode("utf-8-sig")
            st.download_button(
                "📥 Export visible to CSV",
                data=csv_bytes,
                file_name=f"outreach-export-{datetime.now().strftime('%Y%m%d-%H%M')}.csv",
                mime="text/csv",
                use_container_width=True,
            )

        if save_clicked:
            orig = st.session_state.inbox_df.set_index("id")
            new = edited_df.set_index("id")
            now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            changes = 0
            for lead_id in new.index:
                if lead_id not in orig.index:
                    continue
                diff = {}
                for col in ["status", "replied", "booked_demo", "notes", "script", "ig_handle", "email", "last_channel"]:
                    if col not in new.columns:
                        continue
                    old_val = orig.at[lead_id, col]
                    new_val = new.at[lead_id, col]
                    if pd.isna(old_val) and pd.isna(new_val):
                        continue
                    if old_val != new_val:
                        if col in ("replied", "booked_demo"):
                            diff[col] = int(bool(new_val))
                        else:
                            diff[col] = new_val
                # Auto-fill sent_at when status transitions to Sent
                if diff.get("status") == "Sent":
                    cur_sent_at = orig.at[lead_id, "sent_at"] if "sent_at" in orig.columns else None
                    if pd.isna(cur_sent_at) or not cur_sent_at:
                        diff["sent_at"] = now_iso
                if diff:
                    lib.update_lead(int(lead_id), **diff)
                    changes += 1
            if changes:
                st.success(f"💾 Saved {changes} change(s)")
                st.session_state.pop("inbox_df", None)
                st.session_state.pop("inbox_df_id_set", None)
                st.rerun()
            else:
                st.info("No changes to save.")

        if mark_all_sent:
            now_iso = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for lead_id in edited_df["id"]:
                lib.update_lead(int(lead_id), status="Sent", sent_at=now_iso)
            st.success(f"✅ Marked {len(edited_df)} as Sent")
            st.session_state.pop("inbox_df", None)
            st.session_state.pop("inbox_df_id_set", None)
            st.rerun()


# ========== PHONE MODE ==========
elif page == "📞 Phone Mode":
    st.title("📞 Phone Mode")
    st.caption("One lead at a time. Click → call → log result → auto-advance. Designed for 100/day grind.")

    # Queue = drafted leads with phone, NOT already called via phone
    queue = [
        l for l in lib.get_leads(status_filter=["Drafted"])
        if l.get("phone") and l.get("last_channel") != "Phone"
    ]
    if not queue:
        st.success("🎉 No 'Drafted' leads left to call! Run a Discover or switch to Inbox.")
    else:
        # Init / clamp index
        if "phone_idx" not in st.session_state:
            st.session_state.phone_idx = 0
        idx = st.session_state.phone_idx % len(queue)
        lead = queue[idx]

        st.progress((idx + 1) / len(queue), text=f"Lead {idx + 1} / {len(queue)} in call queue")

        # Lead card
        with st.container(border=True):
            cA, cB = st.columns([3, 2])
            with cA:
                st.markdown(f"## {lead['name']}")
                st.markdown(
                    f"**{lead['niche']}** · {lead['area']} · "
                    f"⭐ {lead['rating']} ({lead['reviews']} reviews)"
                )
                if lead.get("address"):
                    st.markdown(f"📍 {lead['address']}")
                if lead.get("website"):
                    st.markdown(f"🌐 [{lead['website']}]({lead['website']})")
                if lead.get("ig_handle"):
                    st.markdown(f"📱 @{lead['ig_handle']}")
            with cB:
                phone = lead["phone"]
                tel = lib.tel_link(phone)
                st.markdown(f"### 📞 `{phone}`")
                st.link_button(
                    f"Click to Call",
                    tel,
                    use_container_width=True,
                    type="primary",
                )
                st.caption("Opens FaceTime (Mac) / phone dialer")

        # Elevator pitch
        st.subheader("Elevator Pitch — 讀呢段 (30 秒)")
        pitch = (
            f"Hi 老闆好。我係 TVision，做 AI workflow consulting。\n\n"
            f"啱啱見到你哋 {lead['name']} 喺 {lead['area']} 做 {lead['niche']}，"
            f"⭐ {lead['rating']}（{lead['reviews']} 個 reviews）好正。\n\n"
            f"我估你哋日日 reply WhatsApp + plan booking 食晒老闆時間。"
            f"我而家做緊一個免費 30 分鐘 AI workflow audit，揾出 3 個用 AI 慳時間方法。"
            f"完全免費，唔需要 commit 任何嘢。\n\n"
            f"可唔可以 plan 一個下星期嘅 demo 畀你？我可以即刻 send 你 calendar link。"
        )
        st.text_area(" ", value=pitch, height=200, label_visibility="collapsed")

        # Result buttons — 5 most common outcomes
        st.subheader("Log call result")
        from datetime import datetime as _dt
        now_iso = _dt.now().strftime("%Y-%m-%d %H:%M:%S")

        c1, c2, c3, c4, c5 = st.columns(5)

        def _advance_with(update_fields):
            base_notes = (lead.get("notes") or "").strip()
            tag = update_fields.pop("_note_tag", "")
            if tag:
                update_fields["notes"] = (base_notes + " " + tag).strip()
            update_fields["last_channel"] = "Phone"
            if "sent_at" not in update_fields:
                update_fields["sent_at"] = now_iso
            lib.update_lead(lead["id"], **update_fields)
            st.session_state.phone_idx += 1
            st.rerun()

        with c1:
            if st.button("✅ Booked!", use_container_width=True, type="primary"):
                _advance_with({"status": "Booked", "booked_demo": 1, "_note_tag": "[BOOKED via phone]"})
        with c2:
            if st.button("📞 Pickup, interested", use_container_width=True):
                _advance_with({"status": "Replied", "replied": 1, "_note_tag": "[pickup-interested]"})
        with c3:
            if st.button("📴 Voicemail", use_container_width=True):
                _advance_with({"status": "Sent", "_note_tag": "[voicemail]"})
        with c4:
            if st.button("❌ No answer", use_container_width=True):
                _advance_with({"status": "Sent", "_note_tag": "[no-answer]"})
        with c5:
            if st.button("🚫 Not interested", use_container_width=True):
                _advance_with({"status": "Skip", "_note_tag": "[not-interested]"})

        # Nav controls
        st.markdown("---")
        n1, n2, n3, n4 = st.columns([1, 1, 1, 1])
        with n1:
            if st.button("⬅ Previous", use_container_width=True):
                st.session_state.phone_idx = max(0, st.session_state.phone_idx - 1)
                st.rerun()
        with n2:
            if st.button("⏭ Skip (don't log)", use_container_width=True):
                st.session_state.phone_idx += 1
                st.rerun()
        with n3:
            if st.button("🔄 Restart queue", use_container_width=True):
                st.session_state.phone_idx = 0
                st.rerun()
        with n4:
            if st.button("📊 View Stats", use_container_width=True):
                st.session_state.phone_idx = 0  # reset for next time
                st.info("Switch to Stats page in sidebar →")


# ========== AUTO-DISCOVER (background daemon) ==========
elif page == "🤖 Auto-Discover":
    st.title("🤖 Auto-Discover")
    if IS_CLOUD:
        st.error(
            "❌ Auto-Discover daemon **唔 work on Streamlit Cloud** — cloud sandbox 唔畀 spawn subprocess。\n\n"
            "**Workaround**：去 📡 Discover page 手動 run scrape one at a time。\n\n"
            "**True automation**：用 local Mac portal（`launch.sh`），cloud version 留俾你 phone 睇 + click send。"
        )
        st.stop()
    st.caption(
        "Queue up multiple scrapes that run in background. Survives portal close. "
        "Keep this open + go to 📞 Phone Mode — new leads appear in your call queue automatically."
    )

    running, pid = lib.is_auto_discover_running()

    if running:
        # === Running view ===
        status, log_tail = lib.get_auto_discover_status()
        st.success(f"🟢 RUNNING (PID {pid})")

        c1, c2, c3 = st.columns(3)
        c1.metric("Job", f"{status.get('current_job_index', 0) + 1}/{status.get('total_jobs', 0)}")
        c2.metric("Leads added", status.get("total_inserted", 0))
        c3.metric("Duplicates skipped", status.get("total_skipped", 0))

        st.subheader("Current activity")
        st.info(status.get("current_progress", "—"))
        st.caption(f"Current job: **{status.get('current_job', '—')}**")

        if status.get("last_error"):
            st.warning(f"Last error: {status['last_error']}")

        st.subheader("Live log (last 20 lines)")
        st.text(log_tail or "(no log yet)")

        cs1, cs2 = st.columns(2)
        with cs1:
            if st.button("🛑 Stop auto-discover", type="primary", use_container_width=True):
                if lib.stop_auto_discover():
                    st.success("Stopped")
                    time.sleep(1)
                st.rerun()
        with cs2:
            if st.button("🔄 Refresh", use_container_width=True):
                st.rerun()

        # Auto-refresh every 8s while running
        st.markdown(
            "<meta http-equiv='refresh' content='8'>",
            unsafe_allow_html=True,
        )

    else:
        # === Configure + start view ===
        st.info("⚪ Not running. Build a queue below + 🚀 Start.")

        # Read past status (if finished)
        past_status, _ = lib.get_auto_discover_status()
        if past_status.get("finished_at"):
            st.success(
                f"Last run finished {past_status.get('finished_at', '')[:19]} | "
                f"{past_status.get('completed_jobs', 0)} jobs | "
                f"{past_status.get('total_inserted', 0)} leads added"
            )

        # Build queue in session state
        if "ad_queue" not in st.session_state:
            st.session_state.ad_queue = []

        st.subheader("Add a job")
        with st.form("ad_add_form", clear_on_submit=False):
            f1, f2, f3, f4 = st.columns([2, 2, 1, 1])
            with f1:
                niche = st.selectbox("Niche", list(lib.NICHES.keys()), index=0)
            with f2:
                area = st.text_input("Area", "中環")
            with f3:
                count = st.number_input("Count", min_value=20, max_value=300, value=100, step=10)
            with f4:
                mode = st.radio("Mode", ["text", "voice"], horizontal=False)
            add = st.form_submit_button("➕ Add to queue", use_container_width=True, type="secondary")
            if add:
                st.session_state.ad_queue.append({
                    "niche": niche, "area": area, "count": int(count), "mode": mode,
                })

        if st.session_state.ad_queue:
            st.subheader(f"Queue ({len(st.session_state.ad_queue)} jobs)")
            for i, job in enumerate(st.session_state.ad_queue):
                qc1, qc2 = st.columns([9, 1])
                with qc1:
                    st.text(f"  {i + 1}. {job['niche']:8} | {job['area']:8} | {job['count']:>3} | {job['mode']}")
                with qc2:
                    if st.button("🗑", key=f"del_{i}"):
                        st.session_state.ad_queue.pop(i)
                        st.rerun()

            total_count = sum(j["count"] for j in st.session_state.ad_queue)
            est_min = len(st.session_state.ad_queue) * 8  # ~8 min per scrape incl Gemini drafting
            st.caption(f"Total: ~{total_count} leads, est {est_min} min (incl 30s gaps + Gemini drafting)")

            cb1, cb2 = st.columns(2)
            with cb1:
                if st.button("🚀 Start background auto-discover", type="primary", use_container_width=True):
                    if not env_ok:
                        st.error("Missing API keys in .env")
                    else:
                        new_pid = lib.start_auto_discover(st.session_state.ad_queue)
                        st.success(f"Started PID {new_pid}. Switch to 📞 Phone Mode → start calling.")
                        st.session_state.ad_queue = []
                        time.sleep(1)
                        st.rerun()
            with cb2:
                if st.button("🗑 Clear queue", use_container_width=True):
                    st.session_state.ad_queue = []
                    st.rerun()
        else:
            st.caption("Queue empty — add jobs above.")

            st.markdown("---")
            st.subheader("⚡ Quick presets")
            preset_col1, preset_col2, preset_col3 = st.columns(3)
            with preset_col1:
                if st.button("🏢 B2B Pro Services\n(會計師 + 律師 + 物業 × 中環)", use_container_width=True):
                    st.session_state.ad_queue = [
                        {"niche": "會計師", "area": "中環", "count": 100, "mode": "text"},
                        {"niche": "律師", "area": "中環", "count": 100, "mode": "text"},
                        {"niche": "物業代理", "area": "中環", "count": 100, "mode": "text"},
                        {"niche": "保險經紀", "area": "中環", "count": 100, "mode": "text"},
                    ]
                    st.rerun()
            with preset_col2:
                if st.button("🛒 Retail blast\n(美容/餐廳/cafe × 銅鑼灣)", use_container_width=True):
                    st.session_state.ad_queue = [
                        {"niche": "美容", "area": "銅鑼灣", "count": 100, "mode": "text"},
                        {"niche": "餐廳", "area": "銅鑼灣", "count": 100, "mode": "text"},
                        {"niche": "cafe", "area": "銅鑼灣", "count": 100, "mode": "text"},
                    ]
                    st.rerun()
            with preset_col3:
                if st.button("🔧 Trade & Service\n(裝修/清潔/IT × 觀塘)", use_container_width=True):
                    st.session_state.ad_queue = [
                        {"niche": "裝修", "area": "觀塘", "count": 100, "mode": "text"},
                        {"niche": "清潔", "area": "觀塘", "count": 100, "mode": "text"},
                        {"niche": "IT", "area": "觀塘", "count": 100, "mode": "text"},
                    ]
                    st.rerun()


# ========== STATS ==========
elif page == "📊 Stats":
    st.title("📊 Stats")

    stats = lib.get_stats()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Total leads", stats["total"])
    c2.metric("Sent", stats["sent"])
    c3.metric("Replied", stats["replied"])
    c4.metric("Booked demo", stats["booked"])

    c1, c2 = st.columns(2)
    c1.metric("Reply rate", f"{stats['reply_rate']:.1f}%", help="replied / sent")
    c2.metric("Booking rate", f"{stats['booking_rate']:.1f}%", help="booked / sent")

    st.markdown("---")
    st.subheader("📞 By Channel")
    conn_ch = lib.get_db()
    ch_rows = conn_ch.execute(
        "SELECT COALESCE(NULLIF(last_channel,''),'(none)') AS ch, COUNT(*) AS c FROM leads "
        "WHERE status IN ('Sent','Replied','Booked','Done') GROUP BY ch ORDER BY c DESC"
    ).fetchall()
    book_rows = conn_ch.execute(
        "SELECT COALESCE(NULLIF(last_channel,''),'(none)') AS ch, COUNT(*) AS c FROM leads "
        "WHERE booked_demo = 1 GROUP BY ch"
    ).fetchall()
    conn_ch.close()
    if ch_rows:
        ch_df = pd.DataFrame([{"Channel": r["ch"], "Touches": r["c"]} for r in ch_rows])
        book_dict = {r["ch"]: r["c"] for r in book_rows}
        ch_df["Booked"] = ch_df["Channel"].map(lambda c: book_dict.get(c, 0))
        ch_df["Book %"] = (ch_df["Booked"] / ch_df["Touches"] * 100).round(1)
        st.dataframe(ch_df, hide_index=True, use_container_width=True)
    else:
        st.info("No sent leads yet — nothing to break down by channel.")

    st.markdown("---")

    c1, c2 = st.columns(2)

    with c1:
        st.subheader("By Niche")
        if stats["by_niche"]:
            df_niche = pd.DataFrame(
                [{"Niche": k, "Count": v} for k, v in stats["by_niche"].items()]
            ).sort_values("Count", ascending=False)
            st.bar_chart(df_niche.set_index("Niche"))
        else:
            st.info("No data yet")

    with c2:
        st.subheader("By Status")
        if stats["by_status"]:
            df_status = pd.DataFrame(
                [{"Status": k, "Count": v} for k, v in stats["by_status"].items()]
            )
            st.dataframe(df_status, hide_index=True, use_container_width=True)
        else:
            st.info("No data yet")

    st.markdown("---")
    st.subheader("Funnel")
    drafted_total = stats["total"]
    sent = stats["sent"]
    replied = stats["replied"]
    booked = stats["booked"]

    funnel_data = [
        ("1. Drafted", drafted_total, 100.0),
        ("2. Sent", sent, (sent / drafted_total * 100) if drafted_total else 0),
        ("3. Replied", replied, (replied / sent * 100) if sent else 0),
        ("4. Booked demo", booked, (booked / replied * 100) if replied else 0),
    ]
    st.dataframe(
        pd.DataFrame(funnel_data, columns=["Stage", "Count", "Conv % from previous"]).round(1),
        hide_index=True,
        use_container_width=True,
    )
