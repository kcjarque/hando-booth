# Hando Booth — Claude Working Notes

**Always check this file before making changes.**

---

## Known Bugs & Fixes

### 1. Filters appearing broken (most common issue)
**Root cause A — Browser cache:** Browser serves old HTML/JS instead of the latest version.
**Fix applied:** `serve.js` now sends `Cache-Control: no-cache` headers on every response. HTML also has `<meta http-equiv="Cache-Control" content="no-cache">` tags.
**Root cause B — `ctx.filter` not supported:** Safari before v18 silently ignores `ctx.filter`, so filters appear to do nothing.
**Fix applied:** Filters now use pixel-level manipulation via `applyPixelFilter()` — pure `getImageData`/`putImageData` math that works in ALL browsers. Do NOT revert to `ctx.filter`.

### 2. "BOOTH" text invisible on home screen
**Root cause:** `.logo-booth` was `color: var(--cream)` — same as the background (`#fdf6ee`).
**Fix applied:** Changed to `color: var(--muted)` (`#9a7d55`) which is visible on the cream background.

### 3. Frame overlays hidden (intentional)
The overlay section in the preview screen is currently `display:none` pending a fix.
The overlay code (`STOCK_OVERLAYS`, `renderOverlayGallery`, etc.) is still in the JS — just hidden in the UI.
**Do NOT delete overlay code.** Re-enable by removing `style="display:none"` from the overlay `.prev-section` in `#preview`.

### 4. GIF worker CORS error
**Root cause:** `new Worker(cdnUrl)` is blocked by browser cross-origin policy.
**Fix applied:** `ensureWorkerBlob()` fetches the worker script, converts it to a Blob URL, and passes that as `workerScript` to the GIF constructor.

### 5. Race condition on composite re-render
If a filter is changed before a previous render completes, both renders run concurrently and the older (wrong) one can overwrite the newer.
**Fix applied:** `_renderGen` counter in `reRenderComposite()` — each render checks its generation before committing the result.

### 6. Custom sound plays all at once on first countdown
**Root cause:** `_playCustomShort()` created a new `Audio()` element on every call without stopping previous playback. Rapid countdown ticks stacked overlapping audio instances.
**Fix applied (v4.6):** Single `_customShortAudio` instance is reused. Previous playback is stopped (`pause()` + `currentTime = 0`) before each new play. A timer ID is tracked and cleared.

### 8. GIF not working on iOS (FIXED in v4.8)
**Root cause:** `gif.js` depends on Web Workers which are blocked by iOS Safari's cross-origin policy. The MediaRecorder MP4 fallback requires `canvas.captureStream()` which is only available on iOS 17.4+. Main-thread gif.js encoding was too slow and timed out.
**Fix applied (v4.8):** Replaced `gif.js` entirely with `gifenc` — a pure-JS GIF encoder that runs synchronously (no workers, no CORS). Loaded via dynamic `import()` from `https://unpkg.com/gifenc@1.0.3/dist/gifenc.esm.js`. Works on ALL browsers. Do NOT revert to `gif.js`.

### 7. Auto-download on save screen
**Root cause:** `showGifScreen()` auto-downloaded the photo via `fetch(compositeDataUrl).then(…a.click())`, and `_autoDownloadGif` auto-downloaded the GIF when generation finished. User explicitly requested removal.
**Fix applied (v4.6):** Both auto-download blocks removed. User taps download/share button explicitly.

### 9. Auto-advance to "Save Your Moment" (FIXED in v5.4)
**Root cause:** `_previewAutoAdvanceTimer` auto-called `continueFlow()` after 6 seconds on the preview screen.
**Fix applied (v5.4):** Removed the auto-advance timer entirely. User must explicitly tap Continue.

### 10. Admin ghost touches / crashes (FIXED in v5.4)
**Root cause:** iOS double-tap zoom and 300ms touch delay caused phantom button activations in the admin modal.
**Fix applied (v5.4):** Added `touch-action: pan-y` to `.modal-body` and `touch-action: manipulation` to all admin buttons, labels, toggles, and checkboxes.

### 11. Countdown sound disappears mid-session (FIXED in v5.4)
**Root cause:** iOS suspends `AudioContext` after a period of inactivity; custom sound `_customShortAudio` was never pre-unlocked.
**Fix applied (v5.4):** Added `_ensureAudioReady()` called before every countdown — resumes AudioContext and pre-loads custom audio. Also unlock `_customShortAudio` alongside `_customAudio` in `unlockAudioOnGesture()`.

### 12. Custom sound photo timing (FIXED in v5.4)
**Root cause:** Custom sound played at n=1 but photo was taken at n=0 (1 second later).
**Fix applied (v5.4):** When custom sound preset is active, `runCountdown()` resolves immediately after playing the sound (150ms delay for the sound to be heard), instead of waiting for the next tick.

### 13. Clear All gallery not working (FIXED in v5.4)
**Root cause:** Supabase Storage `DELETE /object/{bucket}` with `{ prefixes: [...] }` is for folder-prefix deletion, not individual files.
**Fix applied (v5.4):** Changed to delete files individually via `DELETE /object/{bucket}/{filename}` in a loop.

### 14. Custom sound not playing (FIXED in v5.4)
**Root cause:** `_customShortAudio` (the Audio element used in `_playCustomShort()`) was never created on page load — only `_customAudio` was. On iOS, this meant it was never unlocked by user gesture.
**Fix applied (v5.4):** Pre-create `_customShortAudio` on page load when restoring saved custom sound. Also create it in `handleSoundUpload()`. Both elements are now unlocked in `unlockAudioOnGesture()`.

### 15. Custom sound played at every countdown tick (FIXED in v5.7)
**Root cause:** `playCountdownTick()` called `_playCustomShort()` at every non-final tick.
**Fix applied (v5.7):** Custom sound now only plays on the final tick (`playCountdownFinal`). Non-final ticks play a default beep. The countdown still waits for the full custom sound duration before taking the photo.

### 16. Get Photo button missing from save screen (FIXED in v5.7)
**Root cause:** v5.6 replaced "Get Photo" button with "Share" on the gif-screen. The old `doGetQR()` was also broken — it called `renderQR()` with null since Telegram returns no public URL.
**Fix applied (v5.7):** Restored "Get Photo" button calling `doGetQR()`. Rewrote `doGetQR()` to show share buttons (↗ Share Photo / ↗ Share GIF) via native share sheet instead of QR code. Telegram upload happens in background.

### 17. Custom sound disappears mid-session (FIXED in v5.8)
**Root cause:** `_ensureAudioReady()` called `.load()` on the custom audio element, which resets the iOS unlock state. Also, the touchstart audio re-prime only resumed AudioContext but didn't re-unlock the HTMLAudio element.
**Fix applied (v5.8):** Replaced `.load()` with silent play/pause to keep the element alive. Added custom audio re-unlock on every touchstart. `_ensureAudioReady()` now re-creates AudioContext if closed and plays a silent buffer.

### 18. GIF/MP4 too large causing lag and upload failures (FIXED in v5.8)
**Root cause:** GIF and MP4 used full `CELL_W × CELL_H` (which at 300 DPI can be 1200×1600+). This made GIF encoding and MP4 recording extremely slow, causing timeouts and lag.
**Fix applied (v5.8):** Capped GIF at 480px max dimension, MP4 at 640px max dimension. Both scale down proportionally from CELL_W/CELL_H. Increased Telegram upload timeout to 30s.

### 19. Photos and GIFs not uploading to Telegram (FIXED in v5.9)
**Root cause:** While fixing double-send issue, ALL Telegram upload code was removed from both `doGetQR()` and `sharePhoto()`. Nothing triggered uploads anymore.
**Fix applied (v5.9):** Telegram uploads now happen automatically in `showGifScreen()` — photo uploads immediately when composite is ready, MP4 (GIF as video) uploads after `generateGif()` completes and MP4 is pre-cached. A `_tgPhotoUploaded` flag prevents re-uploads if user navigates back and forth. Share buttons do NOT trigger uploads (prevents double-send).

### 20. Video recording ignores admin size settings (FIXED in v5.9)
**Root cause:** `startRecording()` used raw camera resolution instead of admin-configured `vidWidth × vidHeight`. Camera preview used `object-fit: contain` showing full uncropped frame.
**Fix applied (v5.9):** Recording canvas uses `vidWidth × vidHeight` with center-crop math to fill the target aspect ratio. Camera preview uses `object-fit: cover` with `aspect-ratio` CSS set to `vidWidth/vidHeight`, so preview matches recording output exactly.

### 21–30. v6.0 production pass (2026-10-24) — see PRODUCTION_REVIEW.md
- **Guest QR links → Supabase Storage** (`_sbUpload`, `_sbPhotoLink/_sbGifLink/_sbVideoLink`). Telegram file URLs carried the bot token and expired after ~1h. Do NOT point QR codes at Telegram again. Telegram + Drive = operator archive only.
- **Cancel token** `_sessionId` / `_cancelSession()`: X, Home, Start Over, new session bump it; capture, countdown and recorder check it after every await. `#countdown` is `pointer-events:none` so X is tappable mid-countdown.
- **Record double-tap**: `_recStopping` blocks taps until `onstop`. `onerror` only calls stopRecording — `onstop` finalizes.
- **Uploads once per version**: `_compositeVersion` (bumped on every re-render/edit) and `_gifKey` (photos+filter+delay). Never reset upload flags on screen entry.
- **No session restore on reload** — a kiosk refresh must give a clean guest.
- **Video frame guide** uses `vidWidth/vidHeight` in video mode (`--crop-ratio`), photo cell ratio otherwise.
- **Drive base64**: FileReader + slice after `base64,` (recorder MIME types contain commas; spreading bytes into fromCharCode overflows the stack).
- **Home layout**: no `justify-content:center` on the scrolling #home (top overflow is unreachable); 4 columns when 7 layouts are on; landscape caps card height.
- **Brand**: `BRAND` / `FILE_PREFIX` constants — guest-facing name is PNG Booth.
- **Regression suite**: `python3 tests/regression.py` (serve on :3003 first). Run it before every push.

### 31. v6.2 feedback round (2026-10-25)
- **Stories / Messenger need a regular MP4.** MediaRecorder writes fragmented MP4 and a .gif imports as a still. `_socialMp4()` remuxes recordings (mediabunny 1.61.3 from jsDelivr, no re-encode); `_gifVideoBlob()` encodes the GIF frames to H.264 MP4 (WebCodecs) and that is the GIF guest link. Both fall back to the original file if mediabunny can't load.
- **Save screen** shows photo + GIF side by side with GIF speed; no Photo/GIF toggle. Print is removed entirely.
- **Looking good**: Filter/Frame sections hide when there is nothing to choose; one frame is applied automatically; retake thumbnails show the chosen filter.
- **Custom logo** size comes from `--logo-s` (slider, max 300%) and `--logo-ar` with an explicit width, capped at 92vw / 30vh so Start never leaves an iPad screen. The built-in wordmark still uses `zoom`, capped at 200%.

---

## Architecture

- **Single file app:** All code in `index.html`. No build step.
- **5 screens:** `#home`, `#camera`, `#preview`, `#gif-screen`, `#video-preview`, `#thankyou`
- **Filters:** Pixel manipulation in `applyPixelFilter()`. 14 built-in + custom filters with 13 adjustable params.
- **Composite:** `buildComposite()` draws each photo into a cell canvas, applies pixel filter, stamps onto main canvas with sharp corners (no rounding).
- **GIF:** `gifenc` (v1.0.3) via dynamic `import()` from unpkg CDN. Pure-JS encoder — no Web Workers, no CORS issues, works on ALL browsers including iOS Safari. Replaced `gif.js` in v4.8.
- **Video:** MediaRecorder from canvas stream + audio tracks. Supports overlay compositing.
- **Guest links:** Supabase project `hando-booth` (ref `wdzsjgwhhohxlrzxojgq`, HandoCrafted org, free plan). Bucket `booth` (public read, anon insert-only, see `supabase/booth-storage.sql`). Free projects pause after ~7 idle days — a daily Vercel cron (`keepalive/`, project `conex1/png-booth-keepalive`, 03:17 UTC) calls `keepalive()`. Redeploy with `vercel deploy --prod --cwd keepalive --scope conex1`; test with `vercel crons run /api/keepalive --scope conex1` from `keepalive/`. Old v5.4 bucket `photos` (273 guest photos, Apr–May 2026) is kept for old links but has no anon policies — never re-add list/upload rules to it.
- **Telegram:** Operator archive of photos/GIFs/videos via Bot API. Config stored in localStorage (`hb_tg_bot_token`, `hb_tg_chat_id`). Not used for guest links since v6.0.
- **Layouts:** single (1), double (2), strip (3), mini (3 at 1.5×4"), strip4 (4), quad (4), video. Mini is a compact 3-strip.
- **Layout sizes:** Final print size set in inches at 300 DPI. Presets: 4×6, 3×4, 2×6, 1.5×4. Cell sizes auto-computed from final dimensions minus gaps and padding.
- **Dev server:** Node.js static server at `.claude/serve.js`, port 3003.
- **Admin:** Triple-tap logo → password `hando2025`. Logo size (`hb_logo_scale`), per-layout sizes (`hb_layout_sizes_v2`), countdown, sounds, overlays, colors, background, camera, features.

---

## Pending Features

1. ~~Share flow~~ ✅ Implemented (QR + claim page + EmailJS)
2. ~~Print button~~ Removed in v6.2 at the client's request
3. Individual photo retake (tap photo in strip to re-capture that slot)
4. ~~Admin mode~~ ✅ Implemented
5. Fix and re-enable frame overlays
6. **Upload recorded videos to Supabase photo gallery** — currently only photos/GIFs are uploaded; videos should also be saved to the server for QR sharing
