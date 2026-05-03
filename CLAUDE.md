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

---

## Architecture

- **Single file app:** All code in `index.html`. No build step.
- **5 screens:** `#home`, `#camera`, `#preview`, `#gif-screen`, `#video-preview`, `#thankyou`
- **Filters:** Pixel manipulation in `applyPixelFilter()`. 14 built-in + custom filters with 13 adjustable params.
- **Composite:** `buildComposite()` draws each photo into a cell canvas, applies pixel filter, stamps onto main canvas with sharp corners (no rounding).
- **GIF:** `gifenc` (v1.0.3) via dynamic `import()` from unpkg CDN. Pure-JS encoder — no Web Workers, no CORS issues, works on ALL browsers including iOS Safari. Replaced `gif.js` in v4.8.
- **Video:** MediaRecorder from canvas stream + audio tracks. Supports overlay compositing.
- **Telegram:** Photo/GIF/video uploads sent to a Telegram chat via Bot API. Config stored in localStorage (`hb_tg_bot_token`, `hb_tg_chat_id`). Replaced Supabase in v5.5.
- **Layout sizes:** Final print size set in inches (4×6 or 2×3) at 300 DPI. Cell sizes auto-computed from final dimensions minus gaps and padding.
- **Dev server:** Node.js static server at `.claude/serve.js`, port 3003.
- **Admin:** Triple-tap logo → password `hando2025`. Logo size (`hb_logo_scale`), per-layout sizes (`hb_layout_sizes_v2`), countdown, sounds, overlays, colors, background, camera, features.

---

## Pending Features

1. ~~Share flow~~ ✅ Implemented (QR + claim page + EmailJS)
2. ~~Print button~~ ✅ Implemented (`window.print` with `@media print` CSS)
3. Individual photo retake (tap photo in strip to re-capture that slot)
4. ~~Admin mode~~ ✅ Implemented
5. Fix and re-enable frame overlays
6. **Upload recorded videos to Supabase photo gallery** — currently only photos/GIFs are uploaded; videos should also be saved to the server for QR sharing
