#!/bin/bash
# Launch the HK SME Outreach portal.
# Usage: ~/.claude/skills/hksme-cold-outreach/launch.sh
#
# Opens http://localhost:8501 in your default browser.

set -e
cd "$(dirname "$0")"

# Bootstrap venv if missing (first-run on a new machine)
if [ ! -d ".venv" ]; then
    echo "First-run setup: creating venv + installing deps..."
    python3 -m venv .venv
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt
    echo "✅ venv ready"
fi

# Check .env exists; warn if not
if [ ! -f ".env" ]; then
    echo "⚠️  .env not found. Discover page will not work until you set API keys."
    echo "   cp .env.example .env  &&  open -e .env"
fi

echo "🚀 Launching portal at http://localhost:8501"
echo "   Press Ctrl+C to stop."
echo ""

# Bind to 0.0.0.0 so phone on same wifi can access (for IG DM sending on phone)
exec .venv/bin/streamlit run portal.py \
    --browser.gatherUsageStats false \
    --server.address 0.0.0.0
