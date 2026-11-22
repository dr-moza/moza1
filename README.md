# سَطر — automated TikTok video publishing

This repository generates a short Arabic quote video and submits it through TikTok's official Content Posting API. GitHub Actions runs the workflow every six hours and also supports manual dispatch. The workflow needs approved TikTok API access and valid authorization for the account; TikTok may reject apps or content that do not meet its current requirements. It cannot bypass TikTok's creator controls, consent, app review, or publishing restrictions.

## One-time setup

1. Create a TikTok developer app and obtain approval for the Content Posting API and the required video publishing scope. Complete OAuth authorization for the account and keep its client key, client secret, and refresh token private.
2. In **Settings → Secrets and variables → Actions**, add secrets `GEMINI_API_KEY`, `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_REFRESH_TOKEN`, and `GH_PAT`. The GitHub token must have permission to read and update Actions secrets and push commits to `main` (fine-grained token: repository **Secrets: read/write** and **Contents: read/write**). `GH_PAT` is needed to persist a rotated TikTok refresh token; never put credentials in the repository.
3. Optionally add the Actions variable `TIKTOK_PRIVACY_LEVEL`, using a level enabled for the authorized account (defaults to `PUBLIC_TO_EVERYONE`).
4. Review and edit `data/inspiration_pool.json` to tune the original topic ideas used by Gemini. Keep entries as short themes, not copied quotes or posts from other creators.
5. Add licensed, vertical MP4 backgrounds to `assets/backgrounds/` and MP3 tracks to `assets/music/`. `assets/fonts/Amiri-Bold.ttf` is included under the SIL Open Font License, which is also included in that directory. The renderer prefers this Arabic font. If there are no backgrounds it uses a dark solid background; if there is no music it uses silence. The workflow installs FFmpeg and Noto fonts.
6. Enable Actions, then run **TikTok autopilot → Run workflow** once to verify your configuration. Scheduled runs use UTC cron and may be delayed by GitHub.

## Local use

Install FFmpeg and the Python dependencies in `requirements.txt`, set the same environment variables, and run `python main.py`. A successful API response means TikTok accepted the post for processing, not necessarily that it is already public. The workflow commits the inspiration pool and quote history after a successful submission.

## Operational notes

- The generator uses only the curated topic ideas in `data/inspiration_pool.json`; it does not scrape competitor channels or reuse their posts.
- Quotes are checked against `data/history.json`; only successfully submitted quotes enter history.
- The refresh token is rotated via TikTok OAuth and written back to the `TIKTOK_REFRESH_TOKEN` Actions secret using GitHub's encrypted-secret API. If rotation occurs, `GH_PAT` and repository secret permissions must be valid.
- GitHub Actions consumes included assets and workflow minutes; the free allowance depends on the account/repository plan. Continuous publishing is not guaranteed "free forever."
- Use only inspiration sources and music/background assets you are authorized to use. The generated quotes and video should comply with TikTok's current terms and disclosure requirements.
