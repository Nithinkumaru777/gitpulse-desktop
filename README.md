# GitPulse Activity

Automated GitHub activity tracker — *Keep your graph alive.*

This repository is managed by [GitPulse](https://github.com/Nithinkumaru777), a desktop app that automatically pushes timestamped commits on a randomized schedule to keep your GitHub contribution graph green.

## How It Works

- GitPulse appends a timestamp to `activity_log.txt` every 30–60 minutes
- Commits are pushed automatically via `git pull → add → commit → push`
- All operations are handled gracefully — network errors are skipped silently
