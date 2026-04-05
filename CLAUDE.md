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

---

## Architecture

- **Single file app:** All code in `index.html`. No build step.
- **5 screens:** `#home`, `#camera`, `#preview`, `#gif-screen`, (pending: `#thankyou`)
- **Filters:** Pixel manipulation in `applyPixelFilter()`. Filters: `none`, `bw`, `sepia`, `warm`, `cool`.
- **Composite:** `buildComposite()` draws each photo into a cell canvas, applies pixel filter, clips to rounded rect, stamps onto main canvas.
- **GIF:** `gif.js` CDN + worker blob URL workaround.
- **Dev server:** Node.js static server at `.claude/serve.js`, port 3000.

---

## Pending Features

1. Share flow: "Get Your Photo" button → intake form modal → download + QR code → thank-you screen
2. Print button (`window.print` with `@media print` CSS)
3. Individual photo retake (tap photo in strip to re-capture that slot)
4. Admin mode (triple-tap logo → password `hando2025` → overlay management)
5. Fix and re-enable frame overlays
