# Quick Fix Instructions for Risk Radar
# ======================================

## The Problem
The `emergentintegrations` package is proprietary and not available publicly.

## The Fix
Two files need to be updated in your existing project:

### 1. backend/requirements.txt
Find this line:
    emergentintegrations==0.1.0

Replace with:
    # emergentintegrations removed - using openai directly

### 2. backend/.env
Your EMERGENT_LLM_KEY line can be replaced with:
    OPENAI_API_KEY=

(Leave it empty for now - the app will use rule-based analysis)

### 3. backend/server.py
The AI function has been updated to use OpenAI SDK directly.
Download the fresh server.py from the new zip file.

## Then Re-run Setup
After making these changes:

cd ~/Documents/ai-delivery-risk-radar-clickup
rm -rf backend/venv  # Remove old venv
./setup.sh           # Re-run setup
