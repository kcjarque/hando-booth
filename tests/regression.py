"""Booth regression suite — one check per bug fixed in PRODUCTION_REVIEW.md.

Drives the real app in Chromium with a fake camera + microphone. Telegram
and Supabase are mocked at the network layer (nothing is sent). Google Drive
was removed in v6.3; old Drive settings stay in localStorage and any request
to it is logged so the tests can prove nothing goes there.

Run (static server on :3003 serving this folder):
    python3 -m http.server 3003 &
    python3 tests/regression.py [base_url]

Needs: pip install playwright && playwright install chromium
"""
import glob
import json
import re
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3003/'
FAKE_MEDIA = ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream']
PORTRAIT, LANDSCAPE = (820, 1180), (1180, 820)
results = []



def mp4_info(data):
    """Top-level boxes + ffprobe codecs for an MP4 byte string."""
    import struct, subprocess, tempfile
    boxes, i = [], 0
    while i + 8 <= len(data):
        size, typ = struct.unpack('>I4s', data[i:i + 8])
        if size == 1: size = struct.unpack('>Q', data[i + 8:i + 16])[0]
        if size < 8: break
        boxes.append(typ.decode('latin1')); i += size
    with tempfile.NamedTemporaryFile(suffix='.mp4') as f:
        f.write(data); f.flush()
        r = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'stream=codec_type,codec_name', '-of', 'json', f.name], capture_output=True, text=True)
    streams = {st['codec_type']: st['codec_name'] for st in json.loads(r.stdout or '{}').get('streams', [])}
    return {'boxes': boxes, 'streams': streams}


def mp4_ok(data, audio):
    info = mp4_info(data); b = info['boxes']
    good = 'moof' not in b and 'moov' in b and 'mdat' in b and b.index('moov') < b.index('mdat') and info['streams'].get('video') == 'h264'
    return good and (info['streams'].get('audio') == 'aac' if audio else True)


def scenario(name):
    def wrap(fn):
        try:
            fn()
        except Exception as e:
            check(name + ' (crashed)', False, str(e).splitlines()[0][:160])
        return fn
    return wrap


def check(name, ok, detail=''):
    results.append((name, bool(ok), detail))
    print(('PASS ' if ok else 'FAIL ') + name + (f' — {detail}' if detail else ''))


def launch(p):
    # Full Chromium in new-headless mode: the default headless shell has no
    # microphone, which makes getUserMedia({audio:true}) hang forever.
    exes = glob.glob('/Users/*/Library/Caches/ms-playwright/chromium-*/chrome-mac*/*.app/Contents/MacOS/*')
    kw = {'executable_path': sorted(exes)[-1]} if exes else {}
    return p.chromium.launch(args=['--headless=new'] + FAKE_MEDIA, **kw)


def new_page(browser, size=PORTRAIT, uploads=None, camera=True):
    ctx = browser.new_context(viewport={'width': size[0], 'height': size[1]},
                              permissions=['camera', 'microphone'] if camera else [])
    ctx.add_init_script("""
      localStorage.setItem('hb_tg_bot_token', '123456:TEST');
      localStorage.setItem('hb_tg_chat_id', '-100123');
      localStorage.setItem('hb_gdrive_url', 'https://script.google.com/macros/s/TEST/exec');
      localStorage.setItem('hb_gdrive_token', 'test');
      localStorage.setItem('hb_countdown', '3');
    """)
    ctx.set_default_timeout(15000)
    page = ctx.new_page()
    page.dialogs = []
    page.on('dialog', lambda d: (page.dialogs.append(d.message), d.dismiss()))
    page.errors = []
    page.on('pageerror', lambda e: page.errors.append(str(e)))
    log = uploads if uploads is not None else []

    def tg(route):
        url = route.request.url
        method = url.rsplit('/', 1)[-1].split('?')[0]
        if method != 'getFile':
            log.append('telegram:' + method)
            page.tg_bodies.append((method, route.request.post_data_buffer or b''))
        body = {'ok': True, 'result': {'file_path': 'x/file.jpg'}} if method == 'getFile' else \
               {'ok': True, 'result': {'document': {'file_id': 'D'}, 'animation': {'file_id': 'A'}, 'video': {'file_id': 'V'}}}
        route.fulfill(status=200, content_type='application/json', body=json.dumps(body))

    def drive(route):
        data = json.loads(route.request.post_data or '{}')
        log.append('drive:%s:%d' % (data.get('mimeType'), len(data.get('fileData', ''))))
        route.fulfill(status=200, content_type='application/json', body='{"ok":true,"fileName":"f","folder":"d"}')

    def supabase(route):
        req = route.request
        ext = req.url.rsplit('.', 1)[-1]
        if page.sb['fail'] > 0:
            page.sb['fail'] -= 1
            log.append('supabase-fail:' + ext)
            route.fulfill(status=500, content_type='application/json', body='{"error":"test outage"}')
            return
        log.append('supabase:%s:%s:%s' % (req.method, ext, req.headers.get('content-type', '')))
        page.files.append((ext, req.post_data_buffer or b''))
        route.fulfill(status=200, content_type='application/json', body='{"Key":"k"}')

    sb_state = page.sb = {'fail': 0}
    page.files = []
    page.tg_bodies = []

    def app_html(route):
        resp = route.fetch()
        html = resp.text()
        # Always point at a fake project — tests must never write to the real bucket
        html = re.sub(r"const SUPABASE_URL\s*=\s*'[^']*';", "const SUPABASE_URL = 'https://test.supabase.co';", html)
        html = re.sub(r"const SUPABASE_ANON_KEY\s*=\s*'[^']*';", "const SUPABASE_ANON_KEY = 'anon-test-key';", html)
        route.fulfill(response=resp, body=html, headers={**resp.headers, 'content-type': 'text/html'})

    page.route(BASE, app_html)
    page.add_init_script("""
      window.__qr = [];
      Object.defineProperty(window, 'QRCode', { configurable: true,
        set(v) { const W = function (el, o) { window.__qr.push(typeof o === 'string' ? o : o.text); return new v(el, o); };
                 // qrcode.js attaches methods/constants via the global after this runs
                 W.CorrectLevel = v.CorrectLevel;
                 W.prototype = v.prototype; Object.defineProperty(window, 'QRCode', { value: W, writable: true, configurable: true }); },
        get() { return undefined; } });
    """)
    page.route('https://api.telegram.org/**', tg)
    page.route('https://script.google.com/**', drive)
    page.route('https://*.supabase.co/**', supabase)
    page.goto(BASE, wait_until='load')
    page.wait_for_timeout(500)
    return page


def screen(page):
    return page.evaluate("document.querySelector('.screen.active').id")


def start(page, layout):
    page.evaluate(f"document.querySelector('.layout-card[data-layout=\"{layout}\"]').click()")
    page.click('.start-btn')
    page.wait_for_function("document.querySelector('.screen.active').id === 'camera'", timeout=15000)
    page.wait_for_timeout(700)


def capture(page):
    page.click('#shutter')
    page.wait_for_function("document.querySelector('.screen.active').id === 'preview'", timeout=40000)
    page.wait_for_function("!!compositeDataUrl", timeout=15000)


def to_save_screen(page):
    page.click('#preview .btn-warm[onclick="continueFlow()"]')
    page.wait_for_function("document.querySelector('.screen.active').id === 'gif-screen'")
    page.wait_for_function("photos.length < 2 || (!!gifUrl && !gifWorking)", timeout=30000)  # one photo: no GIF
    page.wait_for_timeout(1200)


def in_view(page, selector):
    return page.evaluate(f"""(() => {{ const r = document.querySelector({json.dumps(selector)}).getBoundingClientRect();
      return r.top >= 0 && r.bottom <= innerHeight && r.height > 0; }})()""")


with sync_playwright() as p:
    b = launch(p)

    @scenario('C3 — home screen fits iPad portrait + landscape')
    def _():
        for size in (PORTRAIT, LANDSCAPE, (1024, 768)):
            pg = new_page(b, size)
            r = pg.evaluate("""() => ({ logo: document.querySelector('.logo-wrap').getBoundingClientRect().top,
                                         start: document.querySelector('.start-btn').getBoundingClientRect().bottom })""")
            check(f'home fits {size[0]}x{size[1]}', r['logo'] >= 0 and r['start'] <= size[1], json.dumps(r))
            pg.context.close()


    @scenario('C4 — leaving mid-countdown stops the session')
    def _():
        pg = new_page(b)
        start(pg, 'strip')
        pg.click('#shutter'); pg.wait_for_timeout(1200)
        pg.click('#camera .icon-btn')
        pg.wait_for_timeout(9000)
        st = pg.evaluate("({ s: document.querySelector('.screen.active').id, cd: document.getElementById('countdown').classList.contains('show'), n: photos.length })")
        check('X mid-countdown: stays home, no ghost photos', st == {'s': 'home', 'cd': False, 'n': 0}, json.dumps(st))
        pg.context.close()


    @scenario('H7 — retake one photo, close camera, Retake All -> full new set')
    def _():
        pg = new_page(b)
        start(pg, 'strip'); capture(pg)
        pg.evaluate("document.querySelectorAll('.retake-thumb')[2].click()")
        pg.wait_for_function("document.querySelector('.screen.active').id === 'camera'")
        pg.click('#camera .icon-btn'); pg.wait_for_timeout(400)
        back = screen(pg)
        pg.click('#preview .btn-ghost[onclick="retake()"]')  # Retake All
        pg.wait_for_function("document.querySelector('.screen.active').id === 'camera'"); pg.wait_for_timeout(600)
        capture(pg)
        filled = pg.evaluate("photos.filter(Boolean).length + '/' + photos.length")
        check('retake -> X -> Retake All gives 3 new photos', back == 'preview' and filled == '3/3', f'back={back} photos={filled}')
        pg.context.close()


    @scenario('H1 — Back/Continue does not re-upload; a real change uploads once more')
    def _():
        ups = []
        pg = new_page(b, uploads=ups)
        start(pg, 'strip'); capture(pg); to_save_screen(pg)
        first = list(ups)
        for _ in range(2):
            pg.click('#gif-screen .btn-ghost[onclick="backToPreview()"]'); pg.wait_for_timeout(300)
            pg.click('#preview .btn-warm[onclick="continueFlow()"]'); pg.wait_for_timeout(2500)
        after_back = list(ups)
        check('Back/Continue x2 adds no uploads', len(after_back) == len(first), f'{len(first)} -> {len(after_back)}: {after_back}')
        pg.click('#gif-screen .btn-ghost[onclick="backToPreview()"]'); pg.wait_for_timeout(300)
        pg.evaluate("setFilter('bw')"); pg.wait_for_timeout(2500)
        to_save_screen(pg)
        pg.wait_for_timeout(2500)
        added = ups[len(after_back):]
        check('changed filter uploads the new photo + GIF once', len(added) == len(first), f'{added}')
        check('nothing is sent to Google Drive (removed)', not any(u.startswith('drive') for u in ups), str(ups))
        check('save screen primary action visible (portrait)', in_view(pg, '#gif-screen .btn-warm[onclick="doGetQR()"]'))
        pg.context.close()


    @scenario('H6 — primary actions visible without scrolling, landscape')
    def _():
        pg = new_page(b, LANDSCAPE)
        start(pg, 'strip4'); capture(pg)
        check('preview Continue visible (landscape)', in_view(pg, '#preview .btn-warm[onclick="continueFlow()"]'))
        pg.context.close()


    @scenario('H2 — reload on the save screen starts a fresh guest')
    def _():
        pg = new_page(b)
        start(pg, 'single'); capture(pg); to_save_screen(pg)
        pg.reload(); pg.wait_for_timeout(1200)
        st = pg.evaluate("({ s: document.querySelector('.screen.active').id, n: photos.length })")
        check('reload returns to a clean home screen', st == {'s': 'home', 'n': 0}, json.dumps(st))
        pg.context.close()


    @scenario('H3 + C5 — video frame matches recording; double-tap stop is ignored')
    def _():
        pg = new_page(b, LANDSCAPE)
        start(pg, 'video')
        ratio = pg.evaluate("""(() => { const r = document.querySelector('.cam-crop-guide').getBoundingClientRect();
          return { guide: +(r.width / r.height).toFixed(3), target: +(vidWidth / vidHeight).toFixed(3) }; })()""")
        check('video frame guide matches recording ratio', abs(ratio['guide'] - ratio['target']) < 0.02, json.dumps(ratio))
        pg.locator('#rec-btn').click(force=True); pg.wait_for_timeout(2000)
        pg.evaluate("document.getElementById('rec-btn').click(); document.getElementById('rec-btn').click();")
        pg.wait_for_function("document.querySelector('.screen.active').id === 'video-preview'", timeout=15000)
        blob1 = pg.evaluate("_recordedBlob && _recordedBlob.size")
        pg.wait_for_timeout(12000)
        st = pg.evaluate("({ rec: _mediaRecorder && _mediaRecorder.state, s: document.querySelector('.screen.active').id, same: (_recordedBlob && _recordedBlob.size) === %d })" % (blob1 or -1))
        check('double-tap stop: no hidden 2nd recording', st == {'rec': 'inactive', 's': 'video-preview', 'same': True}, json.dumps(st))
        pg.context.close()


    @scenario('C4 (video) — leaving mid-recording does not jump to a preview later')
    def _():
        pg = new_page(b)
        start(pg, 'video')
        pg.locator('#rec-btn').click(force=True); pg.wait_for_timeout(1500)
        pg.click('#camera .icon-btn')
        pg.wait_for_timeout(12000)
        check('X mid-recording: stays home', screen(pg) == 'home', screen(pg))
        pg.context.close()


    @scenario('M3 — camera denied: stay on home, Start button usable again')
    def _():
        ctx = b.new_context(viewport={'width': PORTRAIT[0], 'height': PORTRAIT[1]})
        pg = ctx.new_page(); dialogs = []
        pg.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
        pg.add_init_script("navigator.mediaDevices.getUserMedia = () => Promise.reject(Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' }));")
        pg.goto(BASE); pg.wait_for_timeout(500)
        pg.click('.start-btn'); pg.wait_for_timeout(1500)
        st = pg.evaluate("({ s: document.querySelector('.screen.active').id, disabled: document.querySelector('.start-btn').disabled, label: document.querySelector('.start-btn').textContent.trim(), notice: document.getElementById('toast').classList.contains('show') ? document.getElementById('toast').textContent.slice(0, 40) : '' })")
        check('camera denied: stays home with in-app guidance (no browser pop-up)', st['s'] == 'home' and not st['disabled'] and 'Start' in st['label'] and 'Camera' in st['notice'] and not dialogs, json.dumps(st))
        ctx.close()


    @scenario('C1/C2 — guest QR codes use permanent Supabase links, uploaded once')
    def _():
        ups = []
        pg = new_page(b, uploads=ups)
        start(pg, 'strip'); capture(pg); to_save_screen(pg)
        pg.wait_for_timeout(2500)
        pg.click('#gif-screen .btn-warm[onclick="doGetQR()"]')
        pg.wait_for_function("document.querySelectorAll('#qr-photo canvas, #qr-gif canvas').length === 2", timeout=30000)
        qr = pg.evaluate('window.__qr')
        prefix = 'https://test.supabase.co/storage/v1/object/public/booth/'
        check('photo + GIF QR point at public Supabase files (GIF as MP4 for Stories)', len(qr) == 2 and all(u.startswith(prefix) for u in qr) and qr[0].endswith('.jpg') and qr[1].endswith('.mp4'), str(qr))
        check('no QR contains a Telegram URL or token', not any('telegram' in u or '/bot' in u for u in qr), str(qr))
        sb = [u for u in ups if u.startswith('supabase')]
        check('one guest-link upload each for photo and GIF', sorted(x.split(':')[2] for x in sb) == ['jpg', 'mp4'], str(sb))
        gifmp4 = [b for e, b in pg.files if e == 'mp4']
        check('GIF video is a regular H.264 MP4 (not fragmented, moov first)', gifmp4 and mp4_ok(gifmp4[0], audio=False), mp4_info(gifmp4[0]) if gifmp4 else 'none')
        anim = [b for m, b in pg.tg_bodies if m == 'sendAnimation']
        check('Telegram GIF caption says the speed', anim and b'Medium speed (0.5 s per photo)' in anim[0], anim[0].split(b'name="caption"')[-1].split(b'\r\n--')[0].decode('utf-8', 'replace').strip() if anim else 'no sendAnimation')
        check('QR codes fully on screen (portrait)', all(in_view(pg, sel) for sel in ('#qr-photo', '#qr-gif')))
        pg.set_viewport_size({'width': LANDSCAPE[0], 'height': LANDSCAPE[1]}); pg.wait_for_timeout(400)
        check('QR codes fully on screen (landscape)', all(in_view(pg, sel) for sel in ('#qr-photo', '#qr-gif')))
        pg.set_viewport_size({'width': PORTRAIT[0], 'height': PORTRAIT[1]}); pg.wait_for_timeout(400)
        pg.click('#thankyou .btn-ghost[onclick="showScreen(\'gif-screen\')"]'); pg.wait_for_timeout(300)  # Back to save screen
        pg.click('#gif-screen .btn-warm[onclick="doGetQR()"]'); pg.wait_for_timeout(2500)
        sb2 = [u for u in ups if u.startswith('supabase')]
        check('Get Photo again reuses the same links', len(sb2) == len(sb) and pg.evaluate('window.__qr.slice(-2)') == qr, str(sb2))
        pg.context.close()

    @scenario('C1 — failed guest upload shows Retry, and Retry recovers')
    def _():
        ups = []
        pg = new_page(b, uploads=ups)
        start(pg, 'single'); capture(pg)
        pg.sb['fail'] = 99  # outage while the photo uploads in the background
        to_save_screen(pg)
        pg.click('#gif-screen .btn-warm[onclick="doGetQR()"]')
        pg.wait_for_selector('#qr-photo button', timeout=60000)
        label = pg.inner_text('#qr-photo button')
        pg.sb['fail'] = 0
        pg.click('#qr-photo button')
        pg.wait_for_function("!!document.querySelector('#qr-photo canvas')", timeout=30000)
        check('upload failure -> "tap to retry" -> QR', 'retry' in label.lower() and pg.evaluate('window.__qr').__len__() >= 1, label)
        pg.context.close()

    @scenario('C1 — video QR uses a Supabase link; archive still sent')
    def _():
        ups = []
        pg = new_page(b, uploads=ups)
        start(pg, 'video')
        pg.locator('#rec-btn').click(force=True); pg.wait_for_timeout(2000)
        pg.locator('#rec-btn').click(force=True)
        pg.wait_for_function("document.querySelector('.screen.active').id === 'video-preview'", timeout=15000)
        pg.wait_for_function("window.__qr.length >= 1 && !!document.querySelector('#video-qr canvas')", timeout=30000)
        pg.wait_for_timeout(1500)
        qr = pg.evaluate('window.__qr')
        vids = [u for u in ups if u.startswith('supabase')]
        check('video QR fully on screen', in_view(pg, '#video-qr'))
        vids = [b for e, b in pg.files if e == 'mp4']
        check('recorded video re-packaged as a regular MP4 with audio (Instagram / Messenger)', vids and mp4_ok(vids[0], audio=True), mp4_info(vids[0]) if vids else 'none')
        check('video QR is a public Supabase file', len(qr) == 1 and qr[0].startswith('https://test.supabase.co/storage/v1/object/public/booth/') and qr[0].rsplit('.', 1)[-1] in ('mp4', 'webm'), str(qr))
        check('video archived to Telegram once, guest link once, nothing to Google Drive', len(vids) == 1 and sum(u.startswith('telegram:sendVideo') or u.startswith('telegram:sendDocument') for u in ups) == 1 and not any(u.startswith('drive') for u in ups), str(ups))
        pg.context.close()

    @scenario('Feedback — save screen shows photo + GIF together with GIF speed; no print on QR screen')
    def _():
        pg = new_page(b)
        start(pg, 'strip'); capture(pg); to_save_screen(pg)
        both = all(in_view(pg, sel) for sel in ('#export-panel', '#gif-panel'))
        speed = pg.evaluate("getComputedStyle(document.getElementById('gif-controls')).display !== 'none'") and in_view(pg, '#gif-controls .delay-row')
        check('photo and GIF on one screen, GIF speed visible', both and speed, f'both={both} speed={speed}')
        pg.click('#gif-screen .btn-warm[onclick="doGetQR()"]'); pg.wait_for_timeout(800)
        check('no Print button on "Enjoy your photo"', pg.evaluate("![...document.querySelectorAll('#thankyou button')].some(b => /print/i.test(b.textContent))"))
        pg.context.close()

    @scenario('Feedback — Looking good: hint text and filtered retake thumbnails')
    def _():
        pg = new_page(b)
        start(pg, 'strip'); capture(pg); pg.wait_for_timeout(800)
        check('hint reads "Tap a photo to retake"', pg.evaluate("document.getElementById('retake-hint').textContent") == 'Tap a photo to retake')
        pg.evaluate("setFilter('bw')"); pg.wait_for_timeout(1500)
        gray = pg.evaluate("""(async () => { const im = document.querySelector('#retake-strip .retake-thumb img'); await im.decode();
          const c = document.createElement('canvas'); c.width = 40; c.height = 30; const x = c.getContext('2d'); x.drawImage(im, 0, 0, 40, 30);
          const d = x.getImageData(0, 0, 40, 30).data; let diff = 0; for (let i = 0; i < d.length; i += 4) diff += Math.abs(d[i] - d[i + 1]) + Math.abs(d[i + 1] - d[i + 2]);
          return diff / (d.length / 4); })()""")
        check('retake thumbnails show the chosen filter (B&W → grey)', gray < 6, f'avg channel spread {gray:.1f}')
        pg.evaluate("setFilter('none')"); pg.wait_for_timeout(800)
        check('back to None restores the original thumbnails', pg.evaluate("[...document.querySelectorAll('#retake-strip .retake-thumb img')].every((im, i) => im.src === photos[i])"))
        pg.context.close()

    @scenario('Feedback — frames: none hidden, one used automatically, several shown')
    def _():
        pg = new_page(b)
        start(pg, 'strip'); capture(pg); pg.wait_for_timeout(600)
        check('several frames → Frame picker shown', pg.evaluate("getComputedStyle(document.getElementById('frame-section')).display !== 'none'"))
        pg.evaluate("STOCK_OVERLAYS.forEach((o, i) => o.enabled = i === 1); overlays = []; saveStockEnabled(); showPreviewScreen()"); pg.wait_for_timeout(800)
        one = pg.evaluate("({ hidden: getComputedStyle(document.getElementById('frame-section')).display === 'none', used: activeOverlay && activeOverlay.id })")
        check('one frame → used automatically, no picker', one['hidden'] and one['used'] == pg.evaluate("STOCK_OVERLAYS[1].id"), json.dumps(one))
        pg.evaluate("STOCK_OVERLAYS.forEach(o => o.enabled = false); saveStockEnabled(); showPreviewScreen()"); pg.wait_for_timeout(800)
        none = pg.evaluate("({ hidden: getComputedStyle(document.getElementById('frame-section')).display === 'none', used: activeOverlay })")
        check('no frames → Frame section hidden', none['hidden'] and none['used'] is None, json.dumps(none))
        pg.evaluate("BUILTIN_FILTERS.forEach(f => f.id !== 'none' && setFilterVisible(f.id, false))"); pg.wait_for_timeout(300)
        check('no filters to choose → Filter section hidden', pg.evaluate("getComputedStyle(document.getElementById('filter-section')).display === 'none'"))
        pg.context.close()

    @scenario('Feedback — custom logo can go bigger')
    def _():
        pg = new_page(b)
        check('logo size slider goes to 300%', pg.evaluate("document.getElementById('logo-size-slider').max") == '300')
        pg.context.close()
        # A small square logo file must grow with the slider, and 300% must still fit the screen
        for size in (PORTRAIT, LANDSCAPE, (1024, 768)):
            pg = new_page(b, size)
            r = pg.evaluate("""async () => {
              const c = document.createElement('canvas'); c.width = c.height = 200;
              c.getContext('2d').fillRect(0, 0, 200, 200); applyHomeLogo(c.toDataURL());
              const img = document.querySelector('.logo-wrap img'); await img.decode();
              const at = async pct => { setLogoScale(pct); await new Promise(r => requestAnimationFrame(r)); return img.getBoundingClientRect(); };
              const a = await at(100), b = await at(300), home = document.getElementById('home');
              return { w100: Math.round(a.width), w300: Math.round(b.width), left: b.left, right: b.right, vw: innerWidth,
                       start: document.querySelector('.start-btn').getBoundingClientRect().bottom, scroll: home.scrollHeight - home.clientHeight };
            }""")
            check(f'custom logo 300% bigger and fits {size[0]}x{size[1]}',
                  r['w300'] > r['w100'] * 1.2 and r['left'] >= 0 and r['right'] <= r['vw'] and r['start'] <= size[1] and r['scroll'] <= 0, json.dumps(r))
            pg.context.close()

    @scenario('v6.3 — sound and Start survive a stuck iPad audio context')
    def _():
        import base64, io, struct, wave
        buf = io.BytesIO(); w = wave.open(buf, 'wb'); w.setnchannels(1); w.setsampwidth(2); w.setframerate(22050)
        w.writeframes(b''.join(struct.pack('<h', 8000 if (i // 20) % 2 else -8000) for i in range(11025))); w.close()
        wav = 'data:audio/wav;base64,' + base64.b64encode(buf.getvalue()).decode()
        # iOS after a screen lock / another app: the context reports 'suspended' (or 'running'
        # with a frozen clock) and resume() never settles. A fresh context works.
        stick = """(mode) => {
          window.__stuck = new WeakSet([_audioCtx]); window.__played = [];
          const st = Object.getOwnPropertyDescriptor(BaseAudioContext.prototype, 'state').get;
          const ct = Object.getOwnPropertyDescriptor(BaseAudioContext.prototype, 'currentTime').get;
          Object.defineProperty(BaseAudioContext.prototype, 'state', { configurable: true, get() { return __stuck.has(this) ? (mode === 'silent' ? 'running' : 'suspended') : st.call(this); } });
          Object.defineProperty(BaseAudioContext.prototype, 'currentTime', { configurable: true, get() { return __stuck.has(this) ? 1.25 : ct.call(this); } });
          const res = AudioContext.prototype.resume; AudioContext.prototype.resume = function () { return __stuck.has(this) ? new Promise(() => {}) : res.call(this); };
          [AudioBufferSourceNode, OscillatorNode].forEach(C => { const s0 = C.prototype.start;
            C.prototype.start = function (...a) { __played.push(__stuck.has(this.context) ? 'stuck' : st.call(this.context)); return s0.apply(this, a); }; });
          const t = document.createElement('button'); t.id = 'tst'; t.onclick = () => previewSound();
          t.style.cssText = 'position:fixed;top:0;left:0;z-index:99999;width:120px;height:60px'; document.body.appendChild(t);
        }"""
        for case in ('start', 'suspended', 'silent'):
            pg = new_page(b)
            pg.evaluate("w => { localStorage.setItem('hb_sound_preset', 'custom'); localStorage.setItem('hb_sound_custom', w); }", wav)
            pg.reload(); pg.wait_for_timeout(500)
            pg.mouse.click(5, 5); pg.wait_for_timeout(500)        # first tap: audio on, sound decoded
            pg.evaluate(stick, case); pg.wait_for_timeout(4500 if case == 'silent' else 1200)
            if case == 'start':
                pg.evaluate("_customSoundBuffer = null; 0")       # iOS replaced the context: decode again
                pg.evaluate("document.querySelector('.layout-card[data-layout=\"strip\"]').click()")
                pg.click('.start-btn'); pg.wait_for_timeout(3000)
                check('stuck audio: Start still opens the camera', screen(pg) == 'camera', screen(pg))
            else:
                pg.click('#tst'); pg.wait_for_timeout(800)
                played = pg.evaluate('__played')
                check(f'stuck audio ({case}): Preview sound plays on a working context', played and 'stuck' not in played and played[-1] == 'running', str(played))
            pg.context.close()
        # Healthy audio is not rebuilt on every tap
        pg = new_page(b)
        pg.mouse.click(5, 5); pg.wait_for_timeout(300)
        first = pg.evaluate('_audioCtx')
        pg.evaluate("window.__ctx0 = _audioCtx; 0")
        for _ in range(3):
            pg.wait_for_timeout(2500); pg.mouse.click(5, 5)
        check('healthy audio context is kept across taps', pg.evaluate("_audioCtx === __ctx0 && _audioCtx.state === 'running'"))
        pg.context.close()

    @scenario('v6.3 — sticker editor Back returns to Looking good')
    def _():
        pg = new_page(b)
        start(pg, 'strip'); capture(pg)
        pg.click('#preview-edit-btn'); pg.wait_for_function("document.querySelector('.screen.active').id === 'editor-screen'")
        pg.evaluate("editorAddSticker('⭐'); 0")
        pg.click('#editor-screen .home-btn[onclick="closeEditor()"]'); pg.wait_for_timeout(300)
        check('Back from Add stickers goes to Looking good', screen(pg) == 'preview', screen(pg))
        pg.context.close()

    @scenario('v6.3 — single photo: no GIF anywhere')
    def _():
        ups = []
        pg = new_page(b, uploads=ups)
        start(pg, 'single'); capture(pg)
        pg.click('#preview .btn-warm[onclick="continueFlow()"]')
        pg.wait_for_function("document.querySelector('.screen.active').id === 'gif-screen'"); pg.wait_for_timeout(2500)
        r = pg.evaluate("""() => ({ gifPanel: !!document.getElementById('gif-panel').offsetParent,
                                    speed: !!document.getElementById('gif-controls').offsetParent,
                                    photo: !!document.getElementById('export-panel').offsetParent,
                                    sub: document.getElementById('gif-screen-sub').textContent })""")
        check('single: save screen shows only the photo', r['photo'] and not r['gifPanel'] and not r['speed'] and 'GIF' not in r['sub'], str(r))
        pg.click('#gif-screen .btn-warm[onclick="doGetQR()"]')
        pg.wait_for_function("window.__qr.length >= 1", timeout=30000); pg.wait_for_timeout(1500)
        qr = pg.evaluate('window.__qr')
        check('single: one QR, no GIF made or uploaded', len(qr) == 1 and qr[0].endswith('.jpg') and not any('sendAnimation' in u or ':mp4:' in u for u in ups), f'{qr} {ups}')
        pg.context.close()
        # Strip still gets its GIF
        pg = new_page(b)
        start(pg, 'strip'); capture(pg); to_save_screen(pg)
        check('strip: GIF still shown', pg.evaluate("!!document.getElementById('gif-panel').offsetParent && !document.getElementById('gif-screen').classList.contains('no-gif')"))
        pg.context.close()

    @scenario('v6.3 — admin adds and removes sticker emojis')
    def _():
        pg = new_page(b)
        pg.evaluate("""() => { const i = document.getElementById('admin-emoji-input'); i.value = '🎂 hi 🌸👨‍👩‍👧🇵🇭 ❤️'; addStickerEmojis(); removeStickerEmoji(0); }""")
        lst = pg.evaluate('_stickerEmojis')
        check('typed emojis added whole (family, flag), text and duplicates skipped, × removes',
              lst[-4:] == ['🎂', '🌸', '👨‍👩‍👧', '🇵🇭'] and '❤️' not in lst and 'h' not in lst and len(lst) == 15, str(lst))
        pg.reload(); pg.wait_for_timeout(400)
        start(pg, 'strip'); capture(pg)
        pg.click('#preview-edit-btn'); pg.wait_for_function("document.querySelector('.screen.active').id === 'editor-screen'")
        bar = pg.evaluate("[...document.querySelectorAll('#sticker-bar .sticker-btn:not(.custom-sticker-btn)')].map(b => b.textContent)")
        check('editor sticker bar uses the saved emoji list after reload', bar == lst, str(bar))
        check('admin has no Google Drive settings', pg.evaluate("!document.getElementById('admin-panel').textContent.includes('Google Drive') && !document.getElementById('gdrive-url')"))
        pg.context.close()

    @scenario('H5 + M5 — brand and favicon')
    def _():
        pg = new_page(b)
        title = pg.title()
        visible_hando = pg.evaluate("document.body.innerText.toLowerCase().includes('hando')")
        icon = pg.request.get(BASE.rstrip('/') + '/icon.svg')
        touch = pg.request.get(BASE.rstrip('/') + '/apple-touch-icon.png')
        check('brand is PNG Booth everywhere guests look', title == 'PNG Booth' and not visible_hando, f'title={title} hando_visible={visible_hando}')
        check('favicon + apple-touch-icon load', icon.ok and 'svg' in icon.headers.get('content-type', '') and touch.ok and 'png' in touch.headers.get('content-type', ''))
        check('no uncaught page errors', not pg.errors, '; '.join(pg.errors))
        pg.context.close()


    b.close()

failed = [r for r in results if not r[1]]
print(f'\n{len(results) - len(failed)}/{len(results)} passed')
sys.exit(1 if failed else 0)
