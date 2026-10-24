"""Booth regression suite — one check per bug fixed in PRODUCTION_REVIEW.md.

Drives the real app in Chromium with a fake camera + microphone. Telegram,
Google Drive and Supabase are mocked at the network layer (nothing is sent).

Run (static server on :3003 serving this folder):
    python3 -m http.server 3003 &
    python3 tests/regression.py [base_url]

Needs: pip install playwright && playwright install chromium
"""
import glob
import json
import sys
from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else 'http://localhost:3003/'
FAKE_MEDIA = ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream']
PORTRAIT, LANDSCAPE = (820, 1180), (1180, 820)
results = []


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
        route.fulfill(status=200, content_type='application/json', body='{"Key":"k"}')

    sb_state = page.sb = {'fail': 0}

    def app_html(route):
        resp = route.fetch()
        html = resp.text()
        html = html.replace("const SUPABASE_URL      = '';", "const SUPABASE_URL      = 'https://test.supabase.co';")
        html = html.replace("const SUPABASE_ANON_KEY = '';", "const SUPABASE_ANON_KEY = 'anon-test-key';")
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
    page.wait_for_function("!!gifUrl && !gifWorking", timeout=30000)
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


    @scenario('H4 — Google Drive accepts a video-sized (4 MB) blob')
    def _():
        ups = []
        pg = new_page(b, uploads=ups)
        res = pg.evaluate("""async () => { const u = URL.createObjectURL(new Blob([new Uint8Array(4 * 1024 * 1024)], { type: 'video/mp4;codecs=avc1.42001f,mp4a.40.2' }));
          const r = await uploadToGDrive(u, 'video/mp4', 'test.mp4', 'test'); return r && r.ok; }""")
        check('Drive upload of a 4 MB video (real recorder MIME)', res is True and any(x.startswith('drive:video/mp4') and int(x.rsplit(':', 1)[1]) > 5_000_000 for x in ups), str(ups))
        pg.context.close()


    @scenario('M3 — camera denied: stay on home, Start button usable again')
    def _():
        ctx = b.new_context(viewport={'width': PORTRAIT[0], 'height': PORTRAIT[1]})
        pg = ctx.new_page(); dialogs = []
        pg.on('dialog', lambda d: (dialogs.append(d.message), d.dismiss()))
        pg.add_init_script("navigator.mediaDevices.getUserMedia = () => Promise.reject(Object.assign(new Error('Permission denied'), { name: 'NotAllowedError' }));")
        pg.goto(BASE); pg.wait_for_timeout(500)
        pg.click('.start-btn'); pg.wait_for_timeout(1500)
        st = pg.evaluate("({ s: document.querySelector('.screen.active').id, disabled: document.querySelector('.start-btn').disabled, label: document.querySelector('.start-btn').textContent.trim() })")
        check('camera denied: stays home with guidance', st['s'] == 'home' and not st['disabled'] and 'Start' in st['label'] and dialogs, json.dumps(st))
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
        check('photo + GIF QR point at public Supabase files', len(qr) == 2 and all(u.startswith(prefix) for u in qr) and qr[0].endswith('.jpg') and qr[1].endswith('.gif'), str(qr))
        check('no QR contains a Telegram URL or token', not any('telegram' in u or '/bot' in u for u in qr), str(qr))
        sb = [u for u in ups if u.startswith('supabase')]
        check('one guest-link upload each for photo and GIF', sorted(x.split(':')[2] for x in sb) == ['gif', 'jpg'], str(sb))
        check('QR codes fully on screen (portrait)', all(in_view(pg, sel) for sel in ('#qr-photo', '#qr-gif')))
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
        check('video QR is a public Supabase file', len(qr) == 1 and qr[0].startswith('https://test.supabase.co/storage/v1/object/public/booth/') and qr[0].rsplit('.', 1)[-1] in ('mp4', 'webm'), str(qr))
        check('video archived to Telegram + Drive once, guest link once', len(vids) == 1 and sum(u.startswith('telegram:sendVideo') or u.startswith('telegram:sendDocument') for u in ups) == 1 and sum(u.startswith('drive:video') and int(u.rsplit(':', 1)[1]) > 10_000 for u in ups) == 1, str(ups))
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
