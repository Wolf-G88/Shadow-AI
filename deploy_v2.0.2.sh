#!/bin/bash

# Shadow AI v2.0.2 - GitHub Deployment Script
# Prepares and pushes the standalone release to GitHub

echo "================================================"
echo "  Shadow AI v2.0.2 - GitHub Deployment"
echo "================================================"
echo ""

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo "❌ Not a git repository"
    echo "   Initialize with: git init"
    exit 1
fi

# Check for uncommitted changes
if [[ -n $(git status -s) ]]; then
    echo "📝 Uncommitted changes detected"
    echo ""
    git status -s
    echo ""
    read -p "Stage and commit these changes? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Stage all new documentation and updated files
        echo "📦 Staging files..."
        git add README.md
        git add CONTRIBUTING.md
        git add LICENSE
        git add install.sh
        git add .gitattributes
        git add output/gui.py
        git add core/unified_llm.py
        git add core/config.py
        git add docs/
        git add debian-package/shadow-ai-2.0.2.deb
        git add debian-package/INSTALL_v2.0.2.md
        git add debian-package/RELEASE_NOTES_v2.0.2.md
        
        echo "✅ Files staged"
        echo ""
        
        # Show what will be committed
        echo "Files to be committed:"
        git diff --cached --name-status
        echo ""
        
        # Commit
        echo "📝 Committing changes..."
        git commit -m "feat: v2.0.2 standalone release with Warp-like features

Major release transforming Shadow AI into a fully standalone application:

## Fixed (6 Critical Bugs)
- Model selection crash (AttributeError)
- First reply crash (IndexError)
- Config not persisting across sessions
- Gemini 1.5 API 404 errors
- Limited API support (4 → 15 providers)
- No visual feedback during processing

## Added (10+ Features)
- Real-time streaming text (word-by-word display)
- Live shell commands (\!command syntax)
- Visual status bar with indicators
- Syntax highlighting (terminal/AI/system)
- 3-tier safety gates (Critical/High/Medium)
- 10 new API providers (Groq, DeepSeek, Mistral, etc.)
- Cognitive architecture framework
- 2,500+ lines of documentation

## Architecture
- 100% standalone (no Warp dependency)
- Producer-consumer pattern with threading
- Queue-based streaming (50ms polling)
- Native tkinter GUI with terminal emulation

## Documentation
- README.md: Comprehensive overview
- CONTRIBUTING.md: Contribution guidelines
- LICENSE: MIT License
- install.sh: One-command setup
- docs/: Full technical documentation

Co-authored-by: Warp AI <agent@warp.dev>"
        
        echo "✅ Changes committed"
    else
        echo "❌ Deployment cancelled"
        exit 1
    fi
else
    echo "✅ No uncommitted changes"
fi

# Check remote
echo ""
echo "🔍 Checking remote repository..."
REMOTE_URL=$(git remote get-url origin 2>/dev/null || echo "")

if [ -z "$REMOTE_URL" ]; then
    echo "⚠️  No remote 'origin' configured"
    echo "   Add remote: git remote add origin https://github.com/Wolf-G88/Shadow-AI.git"
    exit 1
fi

echo "✅ Remote: $REMOTE_URL"

# Create and push tag
echo ""
echo "🏷️  Creating release tag..."
if git rev-parse v2.0.2 >/dev/null 2>&1; then
    echo "⚠️  Tag v2.0.2 already exists"
    read -p "Delete and recreate? (y/N): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        git tag -d v2.0.2
        git push origin :refs/tags/v2.0.2 2>/dev/null || true
    else
        echo "❌ Deployment cancelled"
        exit 1
    fi
fi

git tag -a v2.0.2 -m "Shadow AI v2.0.2 - Standalone Release

Production-ready release with full Warp independence:
- 100% standalone (no external terminal required)
- Real-time streaming text display
- Live shell command execution
- 3-tier safety gate system
- 15 API providers supported
- 2,500+ lines of documentation

Downloads:
- shadow-ai-2.0.2.deb (30 KB)

See RELEASE_NOTES_v2.0.2.md for full changelog."

echo "✅ Tag v2.0.2 created"

# Push to GitHub
echo ""
echo "🚀 Pushing to GitHub..."
read -p "Push to origin/main? (y/N): " -n 1 -r
echo

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo "📤 Pushing commits..."
    git push origin main
    
    echo "📤 Pushing tags..."
    git push origin v2.0.2
    
    echo ""
    echo "================================================"
    echo "✅ Deployment Complete!"
    echo "================================================"
    echo ""
    echo "Shadow AI v2.0.2 is now live on GitHub!"
    echo ""
    echo "📦 Next Steps:"
    echo ""
    echo "1. Create GitHub Release:"
    echo "   - Go to: https://github.com/Wolf-G88/Shadow-AI/releases/new"
    echo "   - Tag: v2.0.2"
    echo "   - Title: Shadow AI v2.0.2 - Standalone Release"
    echo "   - Description: Copy from debian-package/RELEASE_NOTES_v2.0.2.md"
    echo "   - Upload: debian-package/shadow-ai-2.0.2.deb"
    echo ""
    echo "2. Update Repository Description:"
    echo "   Shadow AI — open source, one click install. No accounts. No paywall."
    echo "   No fluff. Drop a file, clone a repo, pick a model. Works offline,"
    echo "   thinks fast, stays quiet. Made for hackers, dads, and tired people"
    echo "   who just want it to work. Grab it. Run it. Own it."
    echo ""
    echo "3. Add Topics (GitHub Settings):"
    echo "   - ai, ai-assistant, ollama, python, tkinter"
    echo "   - chatbot, llm, local-ai, privacy, standalone"
    echo ""
    echo "4. Enable Discussions:"
    echo "   - Go to Settings → General → Features"
    echo "   - Check \"Discussions\""
    echo ""
    echo "5. Announce Release:"
    echo "   - Share on social media"
    echo "   - Post in relevant communities"
    echo "   - Update personal/project websites"
    echo ""
    echo "🎉 Built for hackers, dads, and tired people who just want it to work."
    echo ""
else
    echo "❌ Push cancelled"
    echo "   Run this script again when ready to deploy"
    exit 1
fi
