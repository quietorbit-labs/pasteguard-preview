# PasteGuard cloud routine

Runs on GitHub-hosted Ubuntu, not the owner's PC or ChatGPT. Scheduled checks at 5:17 AM,11:17 AM,5:17 PM Central; daily publishing slot at11 PM Central with a23:30 catch-up. GitHub scheduling may be delayed, so this is not an exact-time guarantee. The durable ledger and account-media check prevent a second daily post. A manually posted reel today also suppresses today's bot post.

The workflow is initially a tested render/assessment pipeline. **It is not an authenticated publisher until the Meta connection is installed and tested.** Missing credentials are an explicit failure in the scheduled publishing step. No local ChatGPT heartbeat is used as a PC-off fallback.

## Account connection still required

Use Meta's supported API for the existing professional account `pasteguard.local`. Authorize only publishing/basic identity and insights permissions; messages/comments access is not needed. Do not paste tokens into chats, commits or files. Store credentials in repository Actions secrets through GitHub's UI:

- `IG_ACCESS_TOKEN`: authorized Meta access token. Never a browser-session cookie.
- `IG_USER_ID`: target professional account ID.
- Variables `IG_API_VERSION` (the version enabled in the Meta app), `IG_API_HOST` (`https://graph.instagram.com` for Instagram Login or `https://graph.facebook.com` for the configured Facebook Login flow), and `IG_PUBLISH_ENABLED=true` only after successful identity/permission verification.
- Optional Cloudflare Web Analytics read-only secrets `CF_ANALYTICS_TOKEN`, `CF_ACCOUNT_ID`, `CF_SITE_TAG`. Query schema/permissions need a real connected test; unavailable data must not be reported as zero. Existing private dashboard remains the source of truth until connected.

Tokens may expire or permissions may be revoked. The job must report and stop on these failures; refresh/reconnection is a real maintenance requirement. This is not indefinite unattended access.

## Verification and operation

Push triggers a cloud render without posting. Inspect the Actions run and download its video/cover artifact. After connecting Meta, dispatch once with publish enabled and verify the resulting reel on Instagram. This is the final external publishing test, not something a renderer test establishes.

Only fake demo data is used. Cloud recording blocks the analytics beacon so synthetic visits do not inflate demand. Site detector behavior is asserted before render; a changed/broken demo stops the job. Short portrait before/after clips use real browser captures, quiet original music, no voiceover and limitations in the export/caption.

The bot fetches each media metric separately. Unsupported watch-time metrics stay unavailable. It does not infer retention from views or pretend that3 low-volume posts prove a winning format. Mature sample thresholds are exploratory heuristics, not a scientific test. It rotates examples/hooks when evidence is insufficient. It does not alter prices, billing, privacy or production site code autonomously.

Raw private metrics are kept in memory and never committed, printed or uploaded. Artifacts contain intended-public demo media and connection status only. Public state contains dates,public media IDs,captions,hook/example choices and duplicate-protection phases; no tokens,personal identities or raw insight counts. A pending publishing state is deliberately not retried blindly—inspect the account/container first.

Website visits are not verified unique people, installs,retention or revenue. Those require separate consent-aware measurement or real tester feedback. This code does not collect pasted secrets,session recordings or per-user identity. A workflow cannot guarantee views or conversions.

Sources: Meta's official Instagram API collection https://www.postman.com/meta/instagram/documentation/6yqw8pt/instagram-api ; GitHub schedules https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#onschedule .
