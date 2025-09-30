#!/bin/bash
# Quick Commit and Push Script for SDC Project
# Usage: ./scripts/quick_push.sh "commit message"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🚀 SDC Project Quick Push Script${NC}"
echo "=================================="

# Check if we're in a git repository
if [ ! -d ".git" ]; then
    echo -e "${RED}❌ Error: Not in a git repository${NC}"
    exit 1
fi

# Get commit message from argument or prompt
if [ -z "$1" ]; then
    echo -e "${YELLOW}📝 Enter commit message:${NC}"
    read -r COMMIT_MSG
else
    COMMIT_MSG="$1"
fi

# Check if commit message is provided
if [ -z "$COMMIT_MSG" ]; then
    COMMIT_MSG="Update: $(date '+%Y-%m-%d %H:%M:%S')"
    echo -e "${YELLOW}⚠️  Using default commit message: $COMMIT_MSG${NC}"
fi

# Show current git status
echo -e "${BLUE}📊 Current Git Status:${NC}"
git status --short

# Add all changes
echo -e "${BLUE}➕ Adding all changes...${NC}"
git add .

# Check if there are changes to commit
if git diff --staged --quiet; then
    echo -e "${YELLOW}⚠️  No changes to commit${NC}"
    exit 0
fi

# Commit changes
echo -e "${BLUE}💾 Committing changes...${NC}"
git commit -m "$COMMIT_MSG

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Commit successful${NC}"
else
    echo -e "${RED}❌ Commit failed${NC}"
    exit 1
fi

# Push to GitHub
echo -e "${BLUE}⬆️  Pushing to GitHub...${NC}"
git push origin main

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✅ Push successful!${NC}"
    echo -e "${GREEN}🔗 Repository: https://github.com/ptyoung65/sdc_i${NC}"
else
    echo -e "${RED}❌ Push failed${NC}"
    echo -e "${YELLOW}💡 You may need to set up the remote origin:${NC}"
    echo "git remote add origin https://github.com/ptyoung65/sdc_i.git"
    exit 1
fi

echo -e "${GREEN}🎉 All done!${NC}"