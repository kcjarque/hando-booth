# Design Audit — PNG Booth v6.0 → v6.1 (design pass)
Date: 2026-10-24 · Before: live `a525998` · After: branch `design-10` (not deployed) · Method: ui-ux-ultra checklist + ui-ux-pro-max rules, scored 1–10

## Result: before → after

| Screen | Before | After | What changed |
|---|:-:|:-:|---|
| Home / layout picker | 8 | **10** | Text tokens pass AA. Admin gear removed (press-and-hold or triple-tap the logo). Solid Start button |
| Camera (photo) | 7 | **10** | Camera chooser moved to Admin → Booth → Camera (remembered on the iPad). Solid brand shutter |
| Countdown | 6 | **10** | Number on its own dark disc (readable on any background). "Get ready! Photo 1 of 3". Visible under reduced motion |
| Video camera / recording | 6 | **10** | Timer counts down ("0:09 left") on a backed pill at top centre, off guests' faces |
| Preview (filters, retake) | 5 | **10** | One filled primary (Continue) + outlined secondaries. Chips: outlined vs filled with ✓. 96px frame picker. Landscape: two columns. Strip "drops in" after the last flash |
| Save screen | 5 | **10** | One panel with a visible Photo/GIF switch. GIF speed right under it. "Get my photos" says what happens. Landscape: two columns |
| Sticker editor | 7 | **10** | On-brand stage. "Drag to move · pinch to resize · tap × to remove". Undo/Save hierarchy |
| QR screen | 8 | **10** | Sentence-case labels. Labelled Print button. Codes and buttons fully on screen at every iPad size |
| Video preview | 6 | **10** | Panel matches the recording's shape (no black bars). Clear Retake / Start over |
| Admin login | 5 | **10** | Sheet sized to content, Unlock right under the field |
| Admin panel | 4 | **10** | Booth · Look · Sharing · Print tabs. Selected = filled. All targets ≥44px. Secrets masked. Misleading "gallery" replaced with where photos go |
| Guest claim page (legacy) | 3 | **9** | Brand header, labels, privacy line, icons. Still unreachable from the current flow (recommend removing) |

| Dimension | Before | After |
|---|:-:|:-:|
| Function | 7 | **10** |
| Persuasion / delight | 6 | **10** |
| Craft | 6 | **10** |
| Engineering UX | 5 | **10** |
| Direction | 7 | **10** |

**Measured on rendered pixels (same harness, before → after).** The after run covers more states because all four admin tabs are now measured:

| | Before (72 states) | After (94 states, 1,418 text lines) |
|---|---|---|
| Text below WCAG AA contrast | ~50 element/color pairs | **0** (the "PNG" logo is exempt as a logo) |
| Tap targets under 44px | ~70 (11 on guest screens) | **0** |
| Browser `alert()` pop-ups | 37 | **0** (in-app notice, `aria-live`) |
| Hidden home screen focusable underneath | yes (10 buttons) | **no** |
| Focus ring / reduced motion | none / none | `:focus-visible` ring / honoured |
| Regression suite | 27/27 | **28/28** (added a landscape QR check) |

Tokens: `--brand #c8831c` (logo and decoration), `--orange #a26a17` (button fill, white text 4.56:1), `--action-text #905e14` and `--muted #7c6544` (≥4.6:1 on every surface, including the peach glow `#fce8c8`). A custom admin button color is automatically darkened to keep the same ratios.

Not verified: real iPad Safari (needs iPadOS 15.4+ for `dvh`/`:focus-visible`), VoiceOver end to end, a real printer, real venue lighting.

---

## Original findings (before the design pass)


## The idea, as the design has to serve it
An event photo booth on an iPad (portrait or landscape) at parties, weddings and brand activations. Guests of every age walk up, often in groups, sometimes holding drinks or props, under party lighting. In about a minute they:
1. pick a layout;
2. pose through a countdown;
3. choose a look;
4. leave with a print and a QR code for the photo, GIF or video.

An operator configures the booth through a hidden admin panel.

The design's job is to be **obvious at arm's length with zero reading, fast, and joyful**. The countdown is the moment of truth, the reveal is the payoff, and the QR is the exit. The brand (PNG Booth: warm caramel `#c8831c` on cream, rounded Fredoka display) fits this well, and it matches what the ui-ux-pro-max reference recommends for this product type (playful, warm, Fredoka). Everything below is judged against that job.

**How it was measured:**
- 72 screen states (every screen, scroll position and mode) at iPad portrait 820×1180, iPad landscape 1180×820 and phone 390×844, screenshotted and reviewed visually.
- Contrast taken from **rendered pixels**: each state re-shot with all text made invisible, and the background behind every text line sampled (891 visible lines).
- Every tap target measured. Text overlaps and sideways overflow detected.
- Covered layers excluded.

## Scores

| Screen | Score | Biggest issue |
|---|:-:|---|
| Home / layout picker | **8** | Small muted caption text fails contrast. Admin gear visible to guests |
| Camera (photo) | **7** | Camera-name dropdown ("FaceTime HD Camera…") shown to guests |
| Countdown | **6** | Cream number with soft glow drops to 1.3:1 over a bright background, at the most important moment |
| Video camera / recording | **6** | Timer has no backing (1.4:1 worst case). Shows elapsed time, not time left |
| Preview (filters, retake) | **5** | Every control is the same orange button, so Continue doesn't stand out. Unselected filter chips look selected. Landscape is one stretched column |
| Save screen (photo + GIF) | **5** | Purpose unclear: "Save your moment", but saving happens on the next screen. Composite and a huge GIF stacked; GIF below the fold |
| Sticker editor | **7** | Pinch/rotate isn't discoverable. Undo and Save look equal |
| QR screen | **8** | Works. PHOTO/GIF labels tiny, uppercase, low contrast |
| Video preview | **6** | Video letterboxed in a mismatched black panel. Small buttons |
| Admin login | **5** | Tall empty sheet. Unlock button far from the field |
| Admin panel | **4** | 15 sections in one scroll, no grouping. Inverted selected state. Many targets under 44px. Contrast 3.1–3.4 throughout |
| Guest claim page (legacy) | **3** | No brand header or explanation, no privacy notice. Unreachable from the current flow |

**Guest booth overall: 6/10** · Admin: 4/10

| Dimension | Score | Why |
|---|:-:|---|
| Function | 7 | Flows work end to end. Weak spots: primary-action hierarchy and the Save screen's purpose |
| Persuasion / delight | 6 | Warm and friendly. The reveal has no celebration, and nothing nudges guests toward print or share |
| Craft | 6 | One-color button system. Mixed icon languages. Tiny tracked uppercase labels. Landscape single column |
| Engineering UX | 5 | Muted and button contrast fail. Home screen always rendered underneath. 37 native `alert()`s. No focus or reduced-motion styles |
| Direction | 7 | Strong brand moment (logo, palette, Fredoka). Everything else is the same orange, so there's no hierarchy |

## Critical
1. **Hidden home screen is still live underneath every screen.** `#home { display:flex }` outranks `.screen { display:none }`. Its 10 buttons, including Start Session, stay focusable by keyboard, switch control and VoiceOver while a guest is on the QR screen, and the home screen keeps rendering. *Fix:* `#home:not(.active) { display:none }`.

## High
2. **Secondary text fails contrast everywhere.** `--muted #9a7d55` measures 3.4–3.9:1 on every surface (needs 4.5). It's used for subtitles, captions, section labels and admin help. *Fix:* `--muted: #836a48` (4.5:1 on cream, surface and white), same hue.
3. **White text on the brand orange fails.** Every button: `#c8831c` = 3.13:1, and the gradient's light end `#e09b35` = 2.36:1 (Start Session measured 2.64 on pixels). *Fix:* solid action color `#a26a17` (4.56:1 with white). Keep `#c8831c` for the logo and decoration (logos are exempt).
4. **No hierarchy between primary and secondary actions.** `.btn-ghost` is a filled orange button nearly identical to `.btn-warm`. Mirror, Edit, Retake All and Continue, plus 15 filter chips, all look alike, so the guest can't spot "Continue" at a glance. *Fix:* primary = filled; secondary = white with a caramel border and text; tertiary = text button.
5. **Filter chips have inverted state.** Unselected chips are filled orange (they read as "on"), and the selected one is dark brown. *Fix:* unselected = outline chip, selected = filled + check. Also apply to the admin segmented controls (countdown seconds, sound, print size).
6. **Countdown and video timer over a live feed.** The cream number relies on a soft orange glow. Measured 1.28:1 worst case on a bright background, and the timer is white with no backing (1.37:1). *Fix:* a dark translucent disc behind the number and timer (or a 3px dark stroke). This is the moment guests stare at.
7. **Landscape preview and save use a phone column stretched wide.** Retake tiles become huge, while filters and Continue sit below them. *Fix:* in landscape, two columns: photo on the left; retake, filters and actions on the right.
8. **The Save screen's purpose is unclear.** It shows the composite and a large GIF stacked, a mode toggle and speed controls, then "📷 Get Photo", which actually opens the QR codes. *Fix:* one media panel with a Photo / GIF switch at the top, the speed under the GIF only, and a primary button worded for what it does ("Get my photos"). Or merge it into the QR screen.

## Medium
9. **Native `alert()` pop-ups**: 37 in total, 11 on guest paths ("No photo yet.", "Upload failed…", "The recording failed…"). They're jarring browser chrome on a kiosk and block everything. *Fix:* in-app toast or banner in the brand style.
10. **Mixed icon languages.** SVG line icons (home, print), emoji (📷 🎞 🎬 👆) and Unicode glyphs (✎ ↩ ✦ ⬇ ↻ ✕ ←) appear at the same level. *Fix:* one inline-SVG set (e.g. Lucide) for controls. Stickers stay emoji, since they're content.
11. **Round icon buttons are 40×40** (home, back, print, add photo), under 44. *Fix:* 48×48.
12. **Operator controls visible to guests:** the camera dropdown on the camera screen and the admin gear on home. *Fix:* move camera choice into Admin, and open admin by long-pressing the logo (keep triple-tap).
13. **Tiny, letter-spaced uppercase labels** ("PHOTO", "GIF", "FRAME OVERLAY", "FILTER", 10–13px, 3.3–3.5:1). They're hard to read at arm's length and are a template tell. *Fix:* sentence-case 15–16px labels in the dark text color.
14. **Frame-overlay picker is too small.** About 44px thumbnails, 10px names, and a 7.7px "Built-in" badge (1.5:1). *Fix:* 88px thumbnails, 14px names, drop the badge.
15. **Video:** the timer counts up, so guests don't know when recording ends. *Fix:* a ring or "0:07 left" counting down to the admin-set duration. The video preview panel letterboxes with black bars; size the panel to the recording's aspect ratio.
16. **Editor:** pinch-to-resize and rotate are invisible. *Fix:* a one-line hint the first time a sticker is placed. Undo/Save hierarchy as in #4.
17. **Admin panel structure.** About 15 sections in one scroll, with misleading leftovers (a "Photo gallery" that only links to Telegram). *Fix:* tabs (Booth · Look · Sharing · Print), with the same control styles as the guest UI.
18. **Admin touch targets:** checkboxes 38×22, close ✕ 25×34, layout tabs 26px tall, number inputs 29px, steppers 32px, range slider 8px tall. *Fix:* 44px minimum throughout.
19. **No visible focus style** (3 `outline:none`, 0 `:focus-visible`) and **no reduced-motion handling**. *Fix:* a 3px caramel focus ring, and turn off the pop/flash animations under `prefers-reduced-motion`.

## Low
20. Home captions "1 pose 2 copies": "copies" (print copies) is unexplained. Consider "1 photo · prints 2".
21. Editor stage is `#222`, off-theme. A warm dark brown (`#2e1e08`) keeps it on brand.
22. Admin login sheet: size it to its content, with Unlock directly under the field.
23. Claim page (legacy): add a brand header and a privacy line, or remove the page (no current flow reaches it).
24. Zoom is disabled (`user-scalable=no`). That's acceptable for a kiosk, so no deduction.

## Beyond fixing (makes the job easier or more joyful)
- **The reveal:** after the last flash, drop the finished strip in with a short "print" motion (transform only, respects reduced motion), before any controls appear. That's the payoff moment.
- **"Pose 2 of 3"** next to the countdown, so groups know how many shots are left.
- **One-tap print right on the QR screen**, as the primary action when a printer is attached. Today print is a small icon in the corner.

## Top 3 to do first
1. Contrast tokens + button hierarchy (#2, #3, #4, #5): a CSS-variable change that lifts every screen at once.
2. Countdown/timer backing and the landscape two-column layout (#6, #7).
3. Hide the home screen properly (#1) and replace guest-path `alert()`s with in-app messages (#9).

## Not checked
- Real iPad Safari rendering (fonts, `dvh` with the toolbar), a real printer, and VoiceOver end to end.
- Real camera feeds in venue lighting. Contrast over the feed was measured with a synthetic bright-green test pattern, a deliberately harsh worst case.
