# Production Review — PNG Booth (hando-booth)
Date: 2026-10-24 · Reviewer: Claude · Scope: launch gate, every feature, scored 1–10
Baseline: v5.20 (commit b217585) → v6.0 (uncommitted working tree)

## Verdict
**NOT CLEARED, three steps from CLEARED.** All code-level blockers are fixed and covered by a 27-check regression suite (the original v5.20 code passes 2 of the 18 bug checks; v6.0 passes all 27). Three steps remain, and none of them can be done in code:

1. **Create the Supabase project** for guest links (token needed) and run one real end-to-end upload. Until then, v6.0 shows "QR sharing is not set up" instead of a QR, so **do not deploy v6.0 before this**.
2. **Rotate the Telegram bot token** in @BotFather. Every QR shown so far contained it, so anyone who scanned one can still use it.
3. **Pick a new admin password.** `hando2025` is readable in the public repo.

## Executive summary (plain language)
The booth works, but it had about a dozen bugs that made it feel unreliable. Leaving a recording didn't really stop it. Retake All sometimes kept old blank slots. Going back and forth uploaded the same photo three times. Refreshing brought back the previous guest. Videos never reached Google Drive. On an iPad held sideways, the Start button was off the screen. All of these are fixed and each has an automated test. The bigger problem was privacy: every QR code contained the key to your Telegram chat and stopped working after an hour. QR codes now point to permanent, keyless links in Supabase Storage. That needs one setup step from you before it goes live.

## Scorecard (before → after)
A 10 means no open Critical, High or Medium item for that feature. Device-only behavior is listed under "Not verified".

| # | Feature | Before | After | What changed |
|---|---------|:-:|:-:|---|
| 1 | Home / layout picker | 4 | 10 | Safe centering. 4 columns when all 7 layouts are on. Card height capped in landscape. Logo and Start fit at 9 iPad sizes in both orientations |
| 2 | Photo capture + countdown | 4 | 9 | X now works during a countdown and cleanly cancels. "Starting camera…" state. Camera failure stays on home. Solid shutter. Readable countdown label |
| 3 | Video recording | 3 | 8 | Double-tap guard. Frame guide equals the recorded 16:9/1:1/9:16 area. Leaving mid-recording discards it. Error path finalizes once. Empty recordings handled |
| 4 | Preview, filters, retake | 6 | 9 | Retake All after a cancelled single retake now takes a full new set. Continue pinned on screen |
| 5 | Save screen + GIF | 5 | 9 | Uploads happen once per version of the photo/GIF. Overlapping GIF encodes can't overwrite each other. Get Photo pinned on screen |
| 6 | Sticker editor | 6 | 8 | Save pinned on screen. An edit is a new photo version, so it is uploaded |
| 7 | QR sharing (guest links) | 2 | 8* | Permanent Supabase Storage links, no secrets. Uploaded in the background so the QR is usually ready instantly. "Tap to retry" on failure. QR codes always fully on screen. *Goes live with the Supabase step |
| 8 | Telegram archive | 5 | 8 | Once per version. No longer used for guest links. Token still needs rotating |
| 9 | Google Drive archive | 3 | 9 | Videos now upload (they crashed before at any size over ~100 KB). Independent of Telegram setup |
| 10 | Kiosk session handling | 3 | 9 | Reload starts a clean guest. One cancel token across capture, countdown and recording |
| 11 | Brand | 3 | 10 | One `BRAND = 'PNG Booth'` constant: title, logo, share text, captions, email, file names |
| 12 | Admin panel | 5 | 5 | Unchanged. Password in public source. Settings per device (see M1, stack) |
| 13 | Guest claim page (`?photo=`) | 3 | 4 | Its upload path now uses Supabase (no token). Still unreachable from the current flow and has no privacy notice |
| 14 | Print | 7 | 7 | Unchanged. Not tested on a printer |
| 15 | Favicon / app shell | 2 | 10 | SVG favicon + 180px apple-touch-icon. No 404s |

UI dimensions (ui-ux-ultra): Function 4 → 9 · Persuasion 6 → 7 · Craft 6 → 8 · Engineering UX 3 → 9 · Direction 7 → 8

## Blockers (open)
- [B1] Supabase project not created. Code and SQL are ready (`supabase/booth-storage.sql`), and `SUPABASE_URL` / `SUPABASE_ANON_KEY` are empty in `index.html`. Fix: create the project (Singapore region), run the SQL, fill in the two constants, then run a real upload + scan from a phone.
- [B2] Telegram bot token exposed. It was embedded in every QR from v5.x. Fix: @BotFather → /revoke, then paste the new token in Admin on each iPad.
- [B3] Admin password `hando2025` in public source (`index.html`, `CLAUDE.md`). Fix (needs your choice): a new password stored only as a SHA-256 hash, or make the repo private (GitHub Pages on a private repo needs a paid plan).

## Fixed this pass (all with a regression test)
| ID | Bug | Proof before → after |
|---|---|---|
| C1/C2 | QR = Telegram URL with bot token, expires ~1h | QR text now `…/storage/v1/object/public/booth/<date>/<uuid>.jpg`. Test asserts no `telegram`/`/bot` in any QR |
| C3 | Home: logo -334px, Start off-screen (landscape) | logo top 64px, Start bottom 672px at 1180x820 |
| C4 | No way to cancel a capture: the countdown layer swallowed taps on X. The capture loop also had no cancel | Taps pass through. X cancels, stays home, 0 photos |
| C5 | Double-tap Record → hidden 2nd recording replaced the video | Recorder inactive, blob unchanged |
| H1 | Back→Continue re-uploaded photo+GIF+Drive (9 uploads/guest) | 3 → 3 (5 with guest links). A changed filter uploads exactly once more |
| H2 | Reload restored the previous guest and re-uploaded | Reload → clean home |
| H3 | Video frame guide 0.654 vs recording 1.778 | 1.778 vs 1.778 |
| H4 | Drive: every video failed (call-stack overflow, then a MIME-comma bug in my first fix) | 4 MB video with real recorder MIME uploads in full |
| H5 | "Hando" vs "PNG Booth" | Title/logo/all strings PNG Booth |
| H6 | Continue / Get Photo / Save below the fold on iPad | Pinned bar. QR screens size the photo so QR codes are fully visible |
| H7 | Retake one photo → X → Retake All gave 1 photo + 2 blanks (live site) | 3/3 photos |
| H8 | Leaving mid-recording jumped to the video preview ~10s later | Stays home |
| M2 | Countdown label ~10px, light on live video | Large, on its own backing |
| M3 | Camera failure still opened the black camera screen | Stays home with guidance. Start button re-enabled |
| M4 | Recorder error dropped the blob | Single finalize path |
| M5 | No favicon | Icon + apple-touch-icon |
| M7 | Shutter: pale ring on white | Solid brand disc + ring |

Correction to the earlier MVP_REVIEW.md: "X mid-countdown leaves a ghost session" was reproduced with a scripted click that goes through overlays. A real tap on X during a countdown was blocked by the countdown layer, so the real bug was "can't cancel once started". It is fixed either way, and the test now uses real pointer clicks.

## Open (Medium / Low)
- [M1] Guest bucket accepts uploads from anyone holding the public key. The damage is limited: only `YYYY-MM-DD/<uuid>.<ext>` paths, 50 MB cap, image/video types only, no list/overwrite/delete. Proper fix: a server route that issues signed upload URLs (see Stack).
- [M6] Admin settings live per iPad in a 5 MB browser store. Big custom sounds or logos can still fill it.
- [M8] No retention: guest photos stay in storage forever. The Philippine DPA expects a stated retention period. Fix: a scheduled deletion (e.g. 30 days) plus a one-line notice near the QR.
- [L1] Dead code: `doGetVideoQR`, `_uploadVideoToGallery`, intake modal (`showGetPhotoModal`/`submitIntake`/`doGetPhoto`), claim page. Left in place. Recommend removing in a separate change.
- [L2] Email `reply_to: hello@handobooth.com` and the Drive script's folder name "Hando Booth" were left as they are (they're addresses/paths, not display text). Change them if the domain or folder should move.
- [L3] Frame overlays are still hidden (`display:none`), as before.

## Test suite
`tests/regression.py`: 27 checks, real Chromium, fake camera + mic, with Telegram, Drive and Supabase mocked at the network layer.

| Run | Result |
|---|---|
| v6.0 (this tree) | 27/27 pass |
| v5.20 (HEAD), same checks | 2/18 bug checks pass (the guest-link checks didn't exist for it) |

## Not verified
- Real iPad Safari: audio unlock, MediaRecorder MP4, camera switching, `100dvh` with the toolbar. Test one full session of each layout on the booth iPad before the first event.
- Real Supabase (B1), real Telegram, real Apps Script, real EmailJS. All mocked here.
- Android Messenger playback of the GIF link. The old flow sent guests a Telegram-converted MP4 for the GIF. The new GIF QR serves the GIF itself (saves as an animated GIF on iOS/Android). Check that Messenger keeps it animated.
- Printing, the sticker editor's pinch/rotate on touch, and the admin screens beyond opening them.

## Stack recommendation: do you still need Next.js + Vercel + Supabase?
**Not to stop the bugs, and not before your next events.** Every bug found was a state/flow bug inside the booth page, and those are now fixed with tests guarding them. A rewrite would not have fixed the iPad-specific behaviors (camera, audio, recording, GIF); those are browser limits on any stack. Supabase is now in, as storage, without changing how the booth is hosted.

**Move to Next.js + Vercel + Supabase when you want any of these.** They need a server, and the static page can't do them safely:
1. A real admin login (not a password in the page) and one settings record shared by every iPad, instead of setting up each device.
2. Locked-down uploads: a server route that issues one-time signed upload URLs (closes M1).
3. The Telegram token kept server-side, a client gallery per event, and automatic deletion after N days (closes M8).
4. Multiple booths/events/clients managed from one dashboard.

Suggested path: run v6.0 at the next events. When one of the four items above becomes a need, rebuild the shell (admin, settings, gallery, uploads) in Next.js and carry over the capture engine: filters, composite, GIF, recorder, and the iOS audio and camera workarounds documented in CLAUDE.md.
