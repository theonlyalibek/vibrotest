#!/usr/bin/env python3
"""VibroTest.kz static site build (RU + KK).

Takes the approved design boards (src/*.dc.html), turns them into plain static pages:
desktop boards become the page, the phone boards (Mobile, Mobile-service, Mobile-menu)
are shown below 900 px. KK text comes from i18n/kk.json (exact RU string -> KK string).

  python3 build.py [--out DIR] [--base https://vibrotest.kz] [--noindex]
"""
import argparse, html, json, re, shutil, sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString, Comment
from PIL import Image

ROOT = Path(__file__).resolve().parent
SRC = ROOT / 'src'
LANGS = ('ru', 'kk')
PHONE = '+7 747 495 61 65'
WA = 'https://wa.me/77474956165'
GIS = 'https://2gis.kz/almaty/firm/70000001104923303'
ORG_ID = '70000001104923303'
LAT, LON = 43.251485, 76.884787

BLOB = {
    'e7e3e1591675795d3ca3937b61042ac4': 'vt-00', '6e90e9e1d041c8f67118cb801f6ef3a1': 'vt-01',
    'd3752ef3f9689be2e373fd87e9fe52f5': 'vt-02', 'a3a858e620930824e01597f6a6b22945': 'vt-03',
    '8750ae3b17de33fe33b66a1ce82a1b7c': 'vt-04', '00fedf66e0e309465421f9f3c16cf69f': 'vt-05',
    '8f80284c85e53342049cfa21c92e442a': 'vt-06', 'a9032462d27bc5c706a60f9e45ed6e01': 'vt-07',
    '877ef39bdc83d08212fc660370e0f243': 'vt-08', 'b0c7f2e8be3c8e631263842b665ff8b9': 'vt-09',
    '53252e69e1ea29c74e900b0ee85cfaf2': 'vt-10', '16c61a7b161b8650f113e85219ad520b': 'vt-11',
    '684a1cdce95a12ea5c591d69b4192412': 'logo-white', '5c0e8a68403f2b59dd4d65bccdd9210a': 'logo-ink',
    '889357b5fc63e565e639b38871f479f7': 'logo-blue',
}

# board -> (path under /<lang>/, kind)
PAGES = {
    'Main.dc.html': ('', 'home'),
    'Services.dc.html': ('services/', 'services'),
    'svc-vibrostand.dc.html': ('services/diagnostika-na-vibrostende/', 'service'),
    'svc-steering-rack.dc.html': ('services/rulevye-reyki/', 'service'),
    'svc-suspension.dc.html': ('services/remont-podveski/', 'service'),
    'svc-brakes.dc.html': ('services/tormoza/', 'service'),
    'svc-drive.dc.html': ('services/stupicy-shrus-privod/', 'service'),
    'svc-cooling.dc.html': ('services/radiatory-patrubki/', 'service'),
    'svc-engine.dc.html': ('services/diagnostika-dvigatelya/', 'service'),
    'Blog.dc.html': ('blog/', 'blog'),
    'art-knock.dc.html': ('blog/stuk-v-podveske-na-kochkah/', 'article'),
    'art-stand-vs-lift.dc.html': ('blog/vibrostend-ili-podemnik/', 'article'),
    'art-rack.dc.html': ('blog/restavraciya-rulevoy-reyki/', 'article'),
    'art-steering-knock.dc.html': ('blog/stuk-v-rule/', 'article'),
    'art-before-buying.dc.html': ('blog/hodovaya-pered-pokupkoy/', 'article'),
}
ALIAS = {'Mobile.dc.html': 'Main.dc.html', 'Mobile-service.dc.html': 'svc-vibrostand.dc.html', 'Main-kk.dc.html': 'Main.dc.html'}
PHONE_BOARD = {'Main.dc.html': 'Mobile.dc.html', 'svc-vibrostand.dc.html': 'Mobile-service.dc.html'}

UI = {
    'ru': {
        'nav': [('Services.dc.html', 'Услуги и цены'), ('svc-vibrostand.dc.html', 'Вибростенд'),
                ('Blog.dc.html', 'Полезное'), ('Main.dc.html#contacts', 'Контакты')],
        'book': 'Записаться', 'wa': 'Написать в WhatsApp', 'call': 'Позвонить', 'menu': 'Открыть меню', 'close': 'Закрыть меню',
        'home': 'VibroTest.kz, на главную', 'open': 'Открыто до 19:00', 'open_s': 'до 19:00',
        'closed': 'Закрыто, откроемся в 09:30', 'closed_s': 'с 09:30',
        'addr': 'Алматы, ул. Аносова, 91', 'copy': '© 2026 VibroTest.kz · Алматы, ул. Аносова, 91',
        'neighbors': 'По соседству на Аносова 91: <a href="https://viton.kz/ru/">Viton</a> (чистка форсунок)',
        'legal': '', 'map_title': 'Карта 2ГИС: VibroTest, Аносова 91', 'crumb_home': 'Главная', 'crumb_svc': 'Услуги',
        'crumb_blog': 'Полезное', 'skip': 'Перейти к содержанию', 'lang_name': 'РУС',
        'wa_msg': 'Здравствуйте! Хочу записаться в VibroTest на Аносова 91.',
        'svc_menu': [('Services.dc.html', 'Услуги и цены'), ('svc-vibrostand.dc.html', 'Вибростенд'), ('svc-steering-rack.dc.html', 'Рулевые рейки'),
                     ('svc-suspension.dc.html', 'Подвеска'), ('svc-drive.dc.html', 'Ступицы и ШРУС'),
                     ('svc-brakes.dc.html', 'Тормоза'), ('svc-cooling.dc.html', 'Радиаторы'),
                     ('svc-engine.dc.html', 'Двигатель'), ('Blog.dc.html', 'Полезное')],
        'n404': ('Страница не найдена', 'Такой страницы нет. Перейдите на главную или напишите нам в WhatsApp.', 'На главную'),
    },
    'kk': {
        'nav': [('Services.dc.html', 'Қызметтер мен бағалар'), ('svc-vibrostand.dc.html', 'Вибростенд'),
                ('Blog.dc.html', 'Пайдалы'), ('Main.dc.html#contacts', 'Байланыс')],
        'book': 'Жазылу', 'wa': 'WhatsApp-қа жазу', 'call': 'Қоңырау шалу', 'menu': 'Мәзірді ашу', 'close': 'Мәзірді жабу',
        'home': 'VibroTest.kz, басты бет', 'open': '19:00-ге дейін ашық', 'open_s': '19:00-ге дейін',
        'closed': 'Жабық, 09:30-да ашыламыз', 'closed_s': '09:30-да ашылады',
        'addr': 'Алматы, Аносов к-сі, 91', 'copy': '© 2026 VibroTest.kz · Алматы, Аносов к-сі, 91',
        'neighbors': 'Аносов 91-де көршіміз: <a href="https://viton.kz/kk/">Viton</a> (форсунка тазалау)',
        'legal': '', 'map_title': '2ГИС картасы: VibroTest, Аносов 91', 'crumb_home': 'Басты бет', 'crumb_svc': 'Қызметтер',
        'crumb_blog': 'Пайдалы', 'skip': 'Мазмұнға өту', 'lang_name': 'ҚАЗ',
        'wa_msg': 'Сәлеметсіз бе! Аносов 91-дегі VibroTest-ке жазылғым келеді.',
        'svc_menu': [('Services.dc.html', 'Қызметтер мен бағалар'), ('svc-vibrostand.dc.html', 'Вибростенд'), ('svc-steering-rack.dc.html', 'Рульдік рейкалар'),
                     ('svc-suspension.dc.html', 'Аспа'), ('svc-drive.dc.html', 'Күпшек және ШРУС'),
                     ('svc-brakes.dc.html', 'Тежегіштер'), ('svc-cooling.dc.html', 'Радиаторлар'),
                     ('svc-engine.dc.html', 'Қозғалтқыш'), ('Blog.dc.html', 'Пайдалы')],
        'n404': ('Бет табылмады', 'Мұндай бет жоқ. Басты бетке өтіңіз немесе бізге WhatsApp-қа жазыңыз.', 'Басты бетке'),
    },
}

HOME_META = {
    'ru': ('Диагностика ходовой на вибростенде в Алматы — VibroTest, Аносова 91',
           'Находим, что стучит в ходовой: вибростенд под нагрузкой за 25–40 минут, заключение на руки. Ремонт подвески и рулевых реек. От 7 000 ₸. Алматы, Аносова 91.'),
    'kk': ('Алматыда вибростендте жүріс бөлігін диагностикалау — VibroTest, Аносов 91',
           'Жүріс бөлігіндегі тықылды табамыз: жүктеме астында вибростенд, 25–40 минут, қорытынды қолға. Аспа мен рульдік рейка жөндеу. 7 000 ₸ бастап. Алматы, Аносов 91.'),
}

KK = {}
MISSING = {}
V2 = None  # the v2 module when building with --v2


KK_VALUES = None


def T(lang, s):
    """Translate a visible string. RU passes through; KK must be in i18n/kk.json."""
    if lang == 'ru' or not s.strip():
        return s
    global KK_VALUES
    if KK_VALUES is None:
        KK_VALUES = {re.sub(r'\s+', ' ', v.strip()) for v in KK.values()} | {'бастап'}
    key = re.sub(r'\s+', ' ', s.strip())
    if key in KK:
        lead = s[:len(s) - len(s.lstrip())]
        trail = s[len(s.rstrip()):]
        return lead + KK[key] + trail
    if re.search('[А-Яа-яЁё]', key) and key not in KK_VALUES:
        MISSING[key] = ''
    return s


# ---------- CSS scoping ----------

def scope_css(css, scope):
    out, i = [], 0
    css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    while i < len(css):
        j = css.find('{', i)
        if j < 0:
            break
        sel = css[i:j].strip()
        if sel.startswith('@media') or sel.startswith('@supports'):
            depth, k = 1, j + 1
            while depth and k < len(css):
                depth += {'{': 1, '}': -1}.get(css[k], 0)
                k += 1
            out.append(sel + '{' + scope_css(css[j + 1:k - 1], scope) + '}')
            i = k
            continue
        k = css.find('}', j)
        body = css[j + 1:k]
        sels = []
        for s in sel.split(','):
            s = s.strip()
            if s in ('html', 'body', '*'):
                if s == '*':
                    sels.append(f'{scope} *')
                continue
            if s.startswith('body'):
                s = s[4:].strip() or ''
            sels.append(f'{scope} {s}'.strip())
        if sels:
            out.append(','.join(sels) + '{' + body + '}')
        i = k + 1
    return ''.join(out)


# ---------- fluid inline styles for the desktop boards ----------

def _clamp(v, lo_k, lo_min, vw_div):
    lo = max(lo_min, round(v * lo_k))
    if lo >= v:
        return f'{v}px'
    return f'clamp({lo}px, {v / vw_div:.2f}vw, {v}px)'


def fluid_style(st):
    def fs(m):
        v = int(m.group(1))
        return 'font-size: ' + (_clamp(v, .56, 24, 12.8) if v >= 30 else f'{v}px')

    def ht(m):
        v = int(m.group(2))
        return m.group(1) + (_clamp(v, .42, 200, 14.4) if v >= 260 else f'{v}px')

    def box(m):
        prop, vals = m.group(1), m.group(2)
        def one(n):
            v = int(n.group(1))
            return _clamp(v, .45, 16, 14.4) if v >= 40 else f'{v}px'
        return prop + re.sub(r'(\d+)px', one, vals)

    st = re.sub(r'font-size:\s*(\d+)px', fs, st)
    st = re.sub(r'(?<![-\w])(height:\s*)(\d+)px', ht, st)
    st = re.sub(r'((?:padding|margin-top|gap):\s*)([^;]+)', box, st)
    return st


# ---------- images ----------

def prep_images(out):
    d = out / 'img'
    d.mkdir(parents=True, exist_ok=True)
    for p in sorted((ROOT / 'img').glob('vt-*.jpg')):
        im = Image.open(p).convert('RGB')
        for w in (800, 1600):
            r = im if im.width <= w else im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            r.save(d / f'{p.stem}-{w}.webp', 'WEBP', quality=78, method=6)
        im.resize((1200, round(im.height * 1200 / im.width)), Image.LANCZOS).save(d / f'{p.stem}.jpg', 'JPEG', quality=82, optimize=True)
    for p in (ROOT / 'img').glob('logo-*.png'):
        im = Image.open(p)
        h = 96
        im = im.resize((round(im.width * h / im.height), h), Image.LANCZOS)
        im.save(d / p.name, optimize=True)
        im.save(d / f'{p.stem}.webp', 'WEBP', quality=90, lossless=False)


# ---------- page assembly ----------

def parse_board(name):
    t = (SRC / name).read_text(encoding='utf-8')
    css = re.search(r'<helmet>.*?<style>(.*?)</style>.*?</helmet>', t, re.S).group(1)
    body = re.search(r'</helmet>(.*)</x-dc>', t, re.S).group(1)
    title = html.unescape(re.search(r'<title>(.*?)</title>', t, re.S).group(1))
    return css, body, title


def url_for(lang, board, frag=''):
    board = ALIAS.get(board, board)
    path, _ = PAGES[board]
    return f'/{lang}/{path}' + (frag or '')


def rewrite_links(soup, lang, page_board):
    for a in soup.find_all('a', href=True):
        h = a['href']
        if h.startswith('Mobile-menu.dc.html'):
            a['href'] = '#menu'
            a['data-menu'] = 'open'
            continue
        m = re.match(r'([\w-]+\.dc\.html)(#.*)?$', h)
        if m:
            board, frag = m.group(1), m.group(2) or ''
            txt = a.get_text(' ', strip=True)
            if ALIAS.get(board, board) == 'Main.dc.html' and not frag:
                if txt in ('Услуги и цены', 'Услуги'):
                    board = 'Services.dc.html'
                elif txt in ('Контакты',):
                    frag = '#contacts'
            a['href'] = url_for(lang, board, frag)
        elif h == '#services':
            a['href'] = url_for(lang, 'Services.dc.html')
        elif h.startswith('#') and page_board != 'Main.dc.html' and h == '#contacts':
            a['href'] = url_for(lang, 'Main.dc.html', h)
        elif 'viton-kz.vercel.app' in h:
            a['href'] = f'https://viton.kz/{lang}/'
        if a['href'].startswith('http') and 'wa.me' not in a['href'] and 'viton.kz' not in a['href']:
            a['rel'] = 'noopener'
            a['target'] = '_blank'


def rewrite_images(soup, first_eager):
    eager_done = not first_eager
    for img in soup.find_all('img'):
        m = re.match(r'/_blob/([0-9a-f]{32})', img.get('src', ''))
        if not m:
            continue
        name = BLOB[m.group(1)]
        if name.startswith('logo'):
            img['src'] = f'/img/{name}.png'
            img['width'], img['height'] = ('156', '44') if 'height: 44px' in img.get('style', '') else (None, None)
            for k in ('width', 'height'):
                if img.get(k) is None:
                    del img[k]
            continue
        img['src'] = f'/img/{name}-800.webp'
        img['srcset'] = f'/img/{name}-800.webp 800w, /img/{name}-1600.webp 1600w'
        img['sizes'] = '(max-width: 900px) 100vw, 50vw'
        img['decoding'] = 'async'
        if not eager_done:
            img['fetchpriority'] = 'high'
            eager_done = True
        else:
            img['loading'] = 'lazy'


def map_iframe(lang):
    """Map facade: grid, pin and two actions. The 2GIS widget is heavy, so it loads only when asked."""
    show, pin = 'Показать карту', 'VibroTest · Аносова, 91'  # translated with the page
    return (f'<div class="mapf" data-map="/map/anosova/" data-title="{UI[lang]["map_title"]}">'
            f'<span class="mapf-road h"></span><span class="mapf-road v"></span>'
            f'<span class="mapf-pin"><span class="mapf-tag">{pin}</span><span class="mapf-dot"></span></span>'
            f'<span class="mapf-act"><button type="button" class="mapf-btn">{show}</button></span></div>')


def place_maps(soup, lang):
    for s in list(soup.find_all(string=re.compile(r'(живая карта|Живая карта|тірі картасы)'))):
        node = s.parent
        box = None
        while node is not None and node.name:
            st = node.get('style', '')
            if node.name == 'div' and re.search(r'(?<![-\w])height:', st):
                box = node
                break
            node = node.parent
        if box is None:
            continue
        st = box['style']
        st = re.sub(r'border: 1px dashed[^;]*;?', 'border: 1px solid rgba(255,255,255,.08);', st)
        st = re.sub(r'background-image:[^;]*;|background-size:[^;]*;', '', st)
        if 'position' not in st:
            st += '; position: relative'
        if 'overflow' not in st:
            st += '; overflow: hidden'
        box['style'] = st
        box.clear()
        box.append(BeautifulSoup(map_iframe(lang), 'html.parser'))


def translate_tree(soup, lang):
    if lang == 'ru':
        return
    skip = {'script', 'style'}
    # "<span>от </span>7 000 ₸" -> "7 000 ₸<span> бастап</span>" (KK puts the word after the number)
    for sp in soup.find_all('span'):
        if sp.get_text().strip() == 'от' and sp.parent and sp.parent.name in ('div', 'p', 'span'):
            par = sp.parent
            sp.extract()
            sp.string = ' бастап'
            par.append(sp)
    for node in list(soup.find_all(string=True)):
        if isinstance(node, Comment) or node.parent.name in skip:
            continue
        s = str(node)
        if not s.strip():
            continue
        # translate whole inline-run when the parent holds mixed inline text (e.g. "от <span>7 000</span> ₸")
        new = T(lang, s)
        if new != s:
            node.replace_with(new)
    for tag in soup.find_all(True):
        for attr in ('alt', 'aria-label', 'title', 'placeholder'):
            if tag.get(attr):
                tag[attr] = T(lang, tag[attr])


def symptom_data(lang):
    p = json.loads((ROOT / 'i18n' / f'symptoms.{lang}.json').read_text(encoding='utf-8'))
    return p


def render_symptoms(soup, lang, variant):
    data = symptom_data(lang)
    sc = soup.find('sc-for')
    if sc is None:
        return False
    btns = []
    for i, s in enumerate(data['items']):
        on = i == 0
        st = ('background:#0071BC;border:1px solid #0071BC;color:#FFFFFF' if on
              else 'background:transparent;border:1px solid rgba(255,255,255,.18);color:#D5DCE5')
        btns.append(f'<button type="button" class="chip" data-sym="{i}" aria-pressed="{"true" if on else "false"}" style="{st}">{html.escape(s["label"])}</button>')
    sc.replace_with(BeautifulSoup(''.join(btns), 'html.parser'))
    first = data['items'][0]
    wa = WA + '?text=' + _q(data['msg'].replace('{x}', first['ask']))
    holes = {'rec.title': first['title'], 'rec.text': first['text'], 'rec.price': first['price'],
             'rec.priceNote': first.get('priceNote', ''), 'rec.wa': wa,
             'rec.href': url_for(lang, first['href']) if first.get('href') else ''}
    for el in soup.find_all(True):
        for k, v in list(el.attrs.items()):
            if isinstance(v, str) and '{{' in v:
                el[k] = re.sub(r'\{\{(rec\.\w+)\}\}', lambda m: holes[m.group(1)], v)
                el['data-rec'] = re.search(r'\{\{rec\.(\w+)\}\}', v).group(1) if '{{' in v else el.get('data-rec')
    for s in list(soup.find_all(string=re.compile(r'\{\{rec\.\w+\}\}'))):
        key = re.search(r'\{\{rec\.(\w+)\}\}', s).group(1)
        s.parent['data-rec'] = key
        s.replace_with(holes['rec.' + key])
    # links holding {{rec.wa}} / {{rec.href}} were replaced above; tag them for the script
    for a in soup.find_all('a', href=True):
        if a['href'] == wa:
            a['data-rec'] = 'wa'
        elif holes['rec.href'] and a['href'] == holes['rec.href'] and a.find_parent(attrs={'data-rec': True}) is None and a.get_text(strip=True) in (
                'Подробнее об услуге', T('kk', 'Подробнее об услуге')):
            a['data-rec'] = 'href'
    return True


def _q(s):
    from urllib.parse import quote
    return quote(s, safe='')


def strip_chrome(soup, phone):
    """Drop board headers, footers and the phone bottom bar: the site adds its own."""
    for h in soup.find_all('header'):
        h.decompose()
    for f in soup.find_all('footer'):
        f.decompose()
    if phone:
        for d in [d for d in soup.find_all('div', style=True) if 'position: sticky; bottom: 0' in d['style']]:
            d.decompose()
    # the KK-draft banner is not part of a real page
    for d in [d for d in soup.find_all('div', style=True) if 'background: #F5A524' in d['style'] and 'Қазақша мәтін' in d.get_text()]:
        d.decompose()


def drop_placeholders(soup):
    """Owner data still missing is marked [..] in the boards: never ship it."""
    for s in list(soup.find_all(string=re.compile(r'\[[^\]]*\]'))):
        if s.parent is None:
            continue
        det = s.find_parent('details')
        if det is not None:
            det.decompose()
            continue
        par = s.parent
        if par.name in ('p', 'span') and re.fullmatch(r'\s*\[[^\]]*\]\s*', par.get_text()):
            par.decompose()
            continue
        s.replace_with(re.sub(r'\[([^\]]*)\]', r'\1', str(s)))


def live_status(soup, lang):
    for p in soup.find_all('p'):
        dot = p.find('span', style=re.compile('background: #30A46C'))
        if dot is not None and 'Открыто' in p.get_text():
            tail = p.get_text().split('·', 1)[-1].strip()
            p.clear()
            p.append(BeautifulSoup(status_html(lang) + ' · ' + tail, 'html.parser'))


def board_root(soup):
    """The outer wrapper div of a board."""
    for el in soup.children:
        if getattr(el, 'name', None) == 'div':
            return el
    return soup


def short_desc(text, limit=130):
    """Meta description: whole sentences up to ~130 chars, so price and address still fit in ~160."""
    out = ''
    for sent in re.split(r'(?<=[.!?])\s+', text):
        if out and len(out) + len(sent) + 1 > limit:
            break
        out = (out + ' ' + sent).strip()
    if len(out) > limit + 20:
        out = out[:limit + 17].rsplit(' ', 1)[0].rstrip(',;:—') + '…'
    return out


def build_board(name, lang, scope, desktop, eager):
    css, body, title = parse_board(name)
    soup = BeautifulSoup(body, 'html.parser')
    strip_chrome(soup, not desktop)
    for svg in soup.find_all('svg'):  # sensor signal charts get a live animation (see JS)
        if svg.find('polyline', stroke='#5AAEF2') and svg.find('rect', attrs={'stroke-dasharray': True}):
            svg['class'] = svg.get('class', []) + ['sig']
    if not desktop:
        # one <h1> per page: the desktop board carries it, the phone copy is a styled paragraph
        for h in soup.find_all('h1'):
            h.name = 'p'
            h['role'] = 'heading'
            h['aria-level'] = '1'
    root = board_root(soup)
    st = root.get('style', '')
    st = re.sub(r'width:\s*390px;?', 'width: 100%;', st)
    st = re.sub(r'height:\s*844px;?', '', st)
    st = re.sub(r'min-height:\s*100%;?', '', st)
    root['style'] = st
    root['class'] = (root.get('class') or []) + [scope.lstrip('.')]
    render_symptoms(soup, lang, scope)
    drop_placeholders(soup)
    live_status(soup, lang)
    if desktop:
        for el in soup.find_all(style=True):
            el['style'] = fluid_style(el['style'])
    place_maps(soup, lang)
    for n, rail in enumerate(soup.select('.rail')):
        cnt = rail.find_next_sibling()
        if cnt is not None and re.fullmatch(r'\s*1 / \d+\s*', cnt.get_text() or ''):
            pass
        elif cnt is not None and cnt.find(string=re.compile(r'^\s*1 / \d+\s*$')):
            cnt = cnt.find(string=re.compile(r'^\s*1 / \d+\s*$')).parent
        else:
            continue
        cnt['id'] = f'rail{n}'
        cnt['aria-hidden'] = 'true'
        rail['data-rail'] = f'rail{n}'
    if V2:
        V2.link_rows(soup, ALIAS.get(name, name))
    rewrite_links(soup, lang, ALIAS.get(name, name))
    rewrite_images(soup, eager)
    translate_tree(soup, lang)
    if V2:
        V2.insert_map(soup, name, lang, url_for, WA)
    return scope_css(css, scope), str(soup), title


# ---------- chrome ----------

def status_html(lang, short=False):
    u = UI[lang]
    return (f'<span class="st" data-open="{u["open_s"] if short else u["open"]}" data-closed="{u["closed_s"] if short else u["closed"]}">'
            f'<span class="st-dot"></span><span class="st-tx">{u["open_s"] if short else u["open"]}</span></span>')


ICON_WA = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M21 11.5a8.4 8.4 0 0 1-12.4 7.4L3 21l2.1-5.4A8.5 8.5 0 1 1 21 11.5z"/></svg>'
ICON_TEL = '<svg width="21" height="21" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7c.1.9.4 1.8.7 2.7a2 2 0 0 1-.5 2.1L8 9.8a16 16 0 0 0 6 6l1.3-1.3a2 2 0 0 1 2.1-.5c.9.3 1.8.6 2.7.7a2 2 0 0 1 1.7 2z"/></svg>'
ICON_MENU = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M4 7h16M4 12h16M4 17h16"/></svg>'
ICON_X = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" aria-hidden="true"><path d="M6 6l12 12M18 6L6 18"/></svg>'


def other_lang(lang):
    return 'kk' if lang == 'ru' else 'ru'


def header_html(lang, board):
    u = UI[lang]
    nav = []
    for b, label in u['nav']:
        bb, _, frag = b.partition('#')
        cur = ' aria-current="page"' if (bb == board and not frag) else ''
        nav.append(f'<a href="{url_for(lang, bb, "#" + frag if frag else "")}"{cur}>{label}</a>')
    alt = other_lang(lang)
    switch = (f'<span class="lang"><a href="{url_for("ru", board)}" hreflang="ru"{" aria-current=\"true\"" if lang == "ru" else ""}>РУС</a>'
              f'<span aria-hidden="true">|</span><a href="{url_for("kk", board)}" hreflang="kk"{" aria-current=\"true\"" if lang == "kk" else ""}>ҚАЗ</a></span>')
    home = url_for(lang, 'Main.dc.html')
    return f'''<a class="skip" href="#main">{u["skip"]}</a>
<header class="dh d-only"><div class="hw">
<a href="{home}" aria-label="{u["home"]}" class="logo"><img src="/img/logo-white.png" alt="VibroTest.kz" width="156" height="44"></a>
<nav class="dnav" aria-label="Menu">{"".join(nav)}</nav>
<div class="dh-r">{switch}
<a href="tel:+77474956165" class="dh-tel num">{status_html(lang)}<span class="sr">{PHONE}</span><span aria-hidden="true">{PHONE}</span></a>
<a class="hbtn" href="{WA}?text={_q(u["wa_msg"])}">{ICON_WA}{u["book"]}</a>
</div></div></header>
<header class="mh m-only">
<a href="{home}" aria-label="{u["home"]}" class="logo"><img src="/img/logo-white.png" alt="VibroTest.kz" width="107" height="30"></a>
<div class="mh-r">{status_html(lang, True)}<a href="#menu" data-menu="open" class="ib" aria-label="{u["menu"]}" aria-controls="menu" aria-expanded="false">{ICON_MENU}</a></div>
</header>
<div id="menu" class="menu" hidden>
<div class="menu-top"><a href="{home}" aria-label="{u["home"]}"><img src="/img/logo-white.png" alt="VibroTest.kz" width="107" height="30"></a>
<a href="#" data-menu="close" class="ib" aria-label="{u["close"]}">{ICON_X}</a></div>
<nav aria-label="Menu" class="menu-nav">{"".join(f'<a href="{url_for(lang, b.partition("#")[0], "#" + b.partition("#")[2] if "#" in b else "")}">{l}</a>' for b, l in u["nav"])}</nav>
<div class="menu-bot"><div class="menu-row">{status_html(lang)}{switch}</div>
<p>{u["addr"]}</p><a href="tel:+77474956165" class="num menu-tel">{PHONE}</a>
<a class="mbtn" href="{WA}?text={_q(u["wa_msg"])}">{ICON_WA}{u["wa"]}</a></div>
</div>'''


def footer_html(lang):
    u = UI[lang]
    links = ''.join(f'<a href="{url_for(lang, b)}">{l}</a>' for b, l in u['svc_menu'])
    return f'''<footer class="ft"><div class="hw">
<div class="ft-top"><img src="/img/logo-white.png" alt="VibroTest.kz" width="142" height="40" loading="lazy"><nav aria-label="Footer">{links}</nav></div>
<div class="ft-bot"><span>{u["copy"]} · <a href="tel:+77474956165" class="num">{PHONE}</a></span><span>{u["neighbors"]}</span></div>
</div></footer>'''


def bottom_bar(lang, price_line=''):
    u = UI[lang]
    return f'''<div class="bb m-only">{price_line}<div class="bb-row">
<a class="mbtn" href="{WA}?text={_q(u["wa_msg"])}">{ICON_WA}{u["book"]}</a>
<a class="bb-wa" href="tel:+77474956165" aria-label="{u["call"]}">{ICON_TEL}</a></div></div>'''


HTACCESS = r'''Options -Indexes
DirectoryIndex index.html
ErrorDocument 404 /404.html
AddDefaultCharset utf-8
AddType font/woff2 .woff2
AddType image/webp .webp
AddType text/plain .txt

RewriteEngine On
RewriteCond %{HTTPS} off [OR]
RewriteCond %{HTTP_HOST} ^www\. [NC]
RewriteRule ^(.*)$ https://{HOST}/$1 [R=301,L]
RewriteRule ^$ /ru/ [R=301,L]

<IfModule mod_deflate.c>
AddOutputFilterByType DEFLATE text/html text/css text/plain text/xml application/xml application/javascript application/json image/svg+xml
</IfModule>
<IfModule mod_expires.c>
ExpiresActive On
ExpiresByType text/html "access plus 0 seconds"
ExpiresByType font/woff2 "access plus 1 year"
ExpiresByType image/webp "access plus 1 month"
ExpiresByType image/jpeg "access plus 1 month"
ExpiresByType image/png "access plus 1 month"
</IfModule>
<IfModule mod_headers.c>
Header always set Strict-Transport-Security "max-age=31536000"
Header always set X-Content-Type-Options "nosniff"
Header always set Referrer-Policy "strict-origin-when-cross-origin"
Header always set X-Frame-Options "SAMEORIGIN"
</IfModule>
'''


BASE_CSS = r'''
[id]{scroll-margin-top:96px}
@media (max-width:899px){[id]{scroll-margin-top:72px}.dv .btn-p{width:100%}}
@media (prefers-reduced-motion:reduce){html{scroll-behavior:auto!important}*{transition:none!important}}
.btn,.hbtn,.mbtn,.bb-wa,.chip,.pbook{transition:background .2s,border-color .2s,color .2s,transform .12s}
.btn:active,.hbtn:active,.mbtn:active,.bb-wa:active,.chip:active{transform:scale(.97)}
.dv .card{transition:border-color .2s}.dv .card:hover{border-color:rgba(90,174,242,.35)}
.mv .rail{-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 40px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 40px),transparent)}
.mapf{position:absolute;inset:0;display:block;background-color:#151B24;background-image:linear-gradient(rgba(255,255,255,.04) 1px,transparent 1px),linear-gradient(90deg,rgba(255,255,255,.04) 1px,transparent 1px);background-size:40px 40px}
.mapf-road{position:absolute;background:rgba(255,255,255,.07)}.mapf-road.h{left:0;right:0;top:46%;height:14px}.mapf-road.v{top:0;bottom:0;left:58%;width:12px}
.mapf-pin{position:absolute;left:50%;top:40%;transform:translate(-50%,-100%);display:flex;flex-direction:column;align-items:center;gap:8px}
.mapf-tag{background:#0071BC;color:#fff;font-size:13px;font-weight:600;padding:8px 14px;border-radius:10px;white-space:nowrap}
.mapf-dot{width:16px;height:16px;border-radius:50%;background:#0071BC;border:3px solid #fff;box-shadow:0 0 0 8px rgba(0,113,188,.25)}
.mapf-act{position:absolute;left:16px;right:16px;bottom:16px;display:flex;gap:10px;flex-wrap:wrap}
.mapf-btn,.mapf-lnk{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:0 18px;border-radius:12px;font:600 14px 'Inter',system-ui,sans-serif;cursor:pointer}
.mapf-btn{border:0;background:#EEF2F7;color:#0A0D12}.mapf-btn:hover{background:#fff}
.mapf-lnk{background:rgba(10,13,18,.8);color:#EEF2F7;border:1px solid rgba(255,255,255,.14)}.mapf-lnk:hover{color:#fff;border-color:rgba(255,255,255,.4)}
.dnav a,.dh-tel,.hbtn{white-space:nowrap}
a.lnk,.ft nav a,.crumbs a,.ft a{position:relative}
a.lnk::after,.ft nav a::after,.crumbs a::after,.ft a::after{content:'';position:absolute;inset:-13px -6px}
html[lang=kk] .dv h1{font-size:clamp(34px,4.4vw,60px)!important;overflow-wrap:break-word}

html{background:#0A0D12;scroll-behavior:smooth;-webkit-text-size-adjust:100%}
body{margin:0;background:#0A0D12;color:#EEF2F7;font-family:'Inter',system-ui,sans-serif;-webkit-font-smoothing:antialiased}
*{box-sizing:border-box}
img{max-width:100%}
a{color:#5AAEF2;text-decoration:none}
:focus-visible{outline:2px solid #5AAEF2;outline-offset:3px;border-radius:4px}
.num{font-family:'JetBrains Mono',ui-monospace,monospace;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.sr{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.skip{position:absolute;left:-9999px;top:8px;background:#0071BC;color:#fff;padding:10px 14px;border-radius:8px;z-index:50}.skip:focus{left:8px}
.hw{width:100%;max-width:1280px;margin:0 auto;padding:0 48px}
.st{display:inline-flex;align-items:center;gap:8px}.st-dot{width:8px;height:8px;border-radius:50%;background:#30A46C;display:inline-block;flex:none}
.st.off .st-dot{background:#8A96A6}
.dh{position:sticky;top:0;z-index:20;background:rgba(10,13,18,.92);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid rgba(255,255,255,.07)}
.dh .hw{display:flex;align-items:center;justify-content:space-between;gap:24px;height:84px}
.logo img{display:block;height:44px;width:auto}
.dnav{display:flex;gap:28px}.dnav a{color:#B4BECB;font-size:14px;font-weight:500}.dnav a:hover,.dnav a[aria-current]{color:#FFFFFF}
.dh-r{display:flex;align-items:center;gap:20px}
.lang{display:flex;gap:8px;font-size:13px;font-weight:600;color:#3A4556}.lang a{color:#8A96A6}.lang a[aria-current]{color:#EEF2F7}
.dh-tel{display:flex;align-items:center;gap:10px;color:#EEF2F7;font-size:15px;font-weight:500}.dh-tel .st-tx{display:none}
.hbtn{display:inline-flex;align-items:center;gap:10px;min-height:46px;padding:0 20px;border-radius:12px;background:#0071BC;color:#fff;font-weight:600;font-size:14px;white-space:nowrap}.hbtn:hover{background:#0A84D6;color:#fff}
.mh{position:sticky;top:0;z-index:20;display:none;align-items:center;justify-content:space-between;height:60px;padding:0 6px 0 16px;background:rgba(10,13,18,.94);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid rgba(255,255,255,.07)}
.mh .logo img{height:30px}
.mh-r{display:flex;align-items:center;gap:2px;font-size:13px;color:#A9B4C2}.mh-r .st{padding-right:4px}
.ib{width:44px;height:44px;display:flex;align-items:center;justify-content:center;color:#EEF2F7}
.menu{position:fixed;inset:0;z-index:40;background:#0A0D12;display:flex;flex-direction:column;overflow-y:auto}
.menu[hidden]{display:none}
.menu-top{display:flex;align-items:center;justify-content:space-between;height:60px;padding:0 6px 0 16px;border-bottom:1px solid rgba(255,255,255,.07)}
.menu-top img{height:30px;width:auto;display:block}
.menu-nav{display:flex;flex-direction:column;padding:8px 16px 0}
.menu-nav a{display:flex;align-items:center;min-height:58px;border-bottom:1px solid rgba(255,255,255,.08);color:#EEF2F7;font:600 22px/1.2 'Geologica',system-ui,sans-serif;letter-spacing:-.01em}
.menu-bot{margin-top:auto;padding:20px 16px 20px;display:flex;flex-direction:column;gap:12px;color:#A9B4C2;font-size:14px}
.menu-bot p{margin:0;color:#8A96A6}
.menu-row{display:flex;justify-content:space-between;align-items:center}
.menu-tel{font-size:20px;font-weight:600;color:#EEF2F7}
.mbtn{display:flex;align-items:center;justify-content:center;gap:10px;min-height:54px;padding:0 22px;border-radius:14px;background:#0071BC;color:#fff;font-weight:600;font-size:16px}
.mbtn:hover{color:#fff;background:#0A84D6}
.bb{position:sticky;bottom:0;z-index:15;padding:10px 16px calc(12px + env(safe-area-inset-bottom));background:#0A0D12;border-top:1px solid rgba(255,255,255,.08);display:none;flex-direction:column;gap:8px}
.bb-row{display:grid;grid-template-columns:minmax(0,1fr) 54px;gap:10px}
.bb-wa{height:54px;border-radius:14px;background:#1B2638;display:flex;align-items:center;justify-content:center;color:#EEF2F7}
.bb-price{display:flex;justify-content:space-between;font-size:13px;color:#A9B4C2}.bb-price b{color:#EEF2F7;font-weight:600}
.ft{padding:48px 0 40px;border-top:1px solid rgba(255,255,255,.06);background:#0A0D12}
.ft-top{display:flex;justify-content:space-between;align-items:center;gap:28px;flex-wrap:wrap}
.ft-top img{height:40px;width:auto;display:block}
.ft nav{display:flex;flex-wrap:wrap;gap:12px 24px}.ft nav a{color:#B4BECB;font-size:14px}
.ft-bot{display:flex;justify-content:space-between;gap:16px;flex-wrap:wrap;margin-top:28px;padding-top:24px;border-top:1px solid rgba(255,255,255,.06);font-size:13px;color:#6F7B8B}
.ft-bot a{color:#8A96A6}
.chip{cursor:pointer}
.mv .rail{scroll-padding:0 16px}
.m-only{display:none}
@media (max-width:899px){
 .d-only{display:none!important}
 .m-only{display:block}
 .mh{display:flex}.bb{display:flex}
 .hw{padding:0 16px}
 .dv .w{padding:0 16px!important}
 .dv [style*="grid-template-columns"]{grid-template-columns:minmax(0,1fr)!important}
 .dv aside{position:static!important}
 .dv h1{overflow-wrap:anywhere}
 .ft-top{flex-direction:column;align-items:flex-start}
}
@media (min-width:900px) and (max-width:1180px){.dnav{gap:18px}.dh-tel span[aria-hidden]{display:none}.hw{padding:0 28px}}
'''

JS = r'''
(function(){
var d=document;
function tick(){var n=new Date(),m=(n.getUTCHours()+5)%24*60+n.getUTCMinutes(),open=m>=570&&m<1140;
 d.querySelectorAll('.st').forEach(function(s){s.classList.toggle('off',!open);var t=s.querySelector('.st-tx');if(t)t.textContent=open?s.dataset.open:s.dataset.closed})}
tick();setInterval(tick,60000);
var menu=d.getElementById('menu');
function setMenu(o){if(!menu)return;menu.hidden=!o;d.documentElement.style.overflow=o?'hidden':'';d.querySelectorAll('[aria-controls=menu]').forEach(function(b){b.setAttribute('aria-expanded',o)})}
d.addEventListener('click',function(e){var a=e.target.closest('[data-menu]');if(a){e.preventDefault();setMenu(a.dataset.menu==='open');return}
 if(menu&&!menu.hidden&&e.target.closest('#menu a[href]'))setMenu(false)});
d.addEventListener('keydown',function(e){if(e.key==='Escape')setMenu(false)});
var S=window.VT_SYM;if(S){
 d.querySelectorAll('[data-sym]').forEach(function(b){b.addEventListener('click',function(){
  var box=b.closest('section'),i=+b.dataset.sym,it=S.items[i];
  box.querySelectorAll('[data-sym]').forEach(function(x){var on=x===b;x.setAttribute('aria-pressed',on);
   x.style.cssText=on?'background:#0071BC;border:1px solid #0071BC;color:#FFFFFF':'background:transparent;border:1px solid rgba(255,255,255,.18);color:#D5DCE5'});
  box.querySelectorAll('[data-rec]').forEach(function(el){var k=el.dataset.rec;
   if(k==='wa')el.href=S.wa+encodeURIComponent(S.msg.replace('{x}',it.ask));
   else if(k==='href'){if(it.url)el.href=it.url}
   else if(it[k]!=null)el.textContent=it[k]});
 })})}
d.querySelectorAll('[data-rail]').forEach(function(r){var c=d.getElementById(r.dataset.rail);if(!c)return;var n=r.children.length;
 r.addEventListener('scroll',function(){var w=r.children[0].getBoundingClientRect().width+12;c.textContent=Math.min(n,Math.round(r.scrollLeft/w)+1)+' / '+n},{passive:true})});
// booking: three fields -> WhatsApp with a ready message, in the page language
var KKL=d.documentElement.lang==='kk';
function wa(t){return 'https://wa.me/77474956165?text='+encodeURIComponent(t)}
d.querySelectorAll('form[data-book]').forEach(function(f){f.addEventListener('submit',function(e){e.preventDefault();
 var car=f.car.value.trim(),sym=f.sym.options[f.sym.selectedIndex].text,w=f.querySelector('input[name=when]:checked'),wt=w?w.nextElementSibling.textContent:'';
 var t=KKL?'Сәлеметсіз бе! VibroTest-ке жазылғым келеді. Көлік: '+car+'. Мазалайды: '+sym+'. Ыңғайлы уақыт: '+wt+'.'
          :'Здравствуйте! Хочу записаться в VibroTest. Машина: '+car+'. Беспокоит: '+sym.toLowerCase()+'. Удобно: '+wt.toLowerCase()+'.';
 var btn=f.querySelector('[type=submit]');if(btn){btn.dataset.t=btn.dataset.t||btn.innerHTML;btn.textContent=KKL?'WhatsApp ашылуда…':'Открываем WhatsApp…';setTimeout(function(){btn.innerHTML=btn.dataset.t},4000)}
 location.href=wa(t)})});
d.querySelectorAll('a.pbook').forEach(function(a){var n=a.parentNode.querySelector('span').textContent.trim();
 a.href=wa(KKL?'Сәлеметсіз бе! VibroTest-ке жазылғым келеді: '+n+'.':'Здравствуйте! Хочу записаться в VibroTest: '+n.toLowerCase()+'.')});
d.addEventListener('click',function(e){var b=e.target.closest('.mapf-btn');if(!b)return;var f=b.closest('.mapf');
 var i=d.createElement('iframe');i.src=f.dataset.map;i.title=f.dataset.title;i.style.cssText='position:absolute;inset:0;width:100%;height:100%;border:0;display:block';f.replaceWith(i)});
// live sensor signal: the baseline drifts, the knock inside the dashed box pulses; static chart stays as the resting frame
if(!matchMedia('(prefers-reduced-motion: reduce)').matches&&'IntersectionObserver' in window){
 var sigs=[].slice.call(d.querySelectorAll('svg.sig')).map(function(svg){var vb=svg.viewBox.baseVal,r=svg.querySelector('rect[stroke-dasharray]'),
  rx=+r.getAttribute('x'),rw=+r.getAttribute('width'),ry=+r.getAttribute('y'),rh=+r.getAttribute('height');
  return {pl:svg.querySelector('polyline'),W:vb.width,H:vb.height,c:rx+rw/2,w:rw/2.6,amp:rh/2-2,mid:ry+rh/2,on:false,svg:svg}});
 var io=new IntersectionObserver(function(es){es.forEach(function(e){sigs.forEach(function(s){if(s.svg===e.target)s.on=e.isIntersecting})})});
 sigs.forEach(function(s){io.observe(s.svg)});
 var t=0;(function f(){t+=.045;sigs.forEach(function(s){if(!s.on)return;var p=[],st=s.W/240,bump=.55+.45*Math.pow(Math.max(0,Math.sin(t*1.3)),3);
  for(var x=0;x<=s.W;x+=st){var g=Math.exp(-Math.pow((x-s.c)/s.w,2));
   var y=s.mid+(Math.sin(x/s.W*38+t*2)*.10+Math.sin(x/s.W*91-t*3.1)*.05)*s.amp*(1-g)+Math.sin(x/s.w*7.5+t*9)*s.amp*.92*g*bump;
   p.push(x.toFixed(1)+','+y.toFixed(1))}s.pl.setAttribute('points',p.join(' '))});requestAnimationFrame(f)})();
}
})();
'''


def jsonld(obj):
    return '<script type="application/ld+json">' + json.dumps(obj, ensure_ascii=False) + '</script>'


def org_schema(base, lang):
    return {
        '@type': 'AutoRepair', '@id': f'{base}/#vibrotest',
        'name': 'VibroTest.kz', 'description': HOME_META[lang][1],
        'founder': {'@type': 'Person', 'name': 'Виктор Новиков'},
        'url': f'{base}/{lang}/', 'telephone': PHONE, 'image': f'{base}/img/vt-00.jpg', 'logo': f'{base}/img/logo-blue.png',
        'priceRange': '₸₸',
        'address': {'@type': 'PostalAddress', 'streetAddress': 'ул. Аносова, 91' if lang == 'ru' else 'Аносов к-сі, 91',
                    'addressLocality': 'Алматы', 'postalCode': '050009', 'addressCountry': 'KZ'},
        'geo': {'@type': 'GeoCoordinates', 'latitude': LAT, 'longitude': LON},
        'openingHoursSpecification': [{'@type': 'OpeningHoursSpecification',
                                       'dayOfWeek': ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'],
                                       'opens': '09:30', 'closes': '19:00'}],
        'paymentAccepted': 'Cash, Credit Card', 'areaServed': {'@type': 'City', 'name': 'Алматы'},
        'sameAs': [GIS, 'https://www.instagram.com/vibrotest.kz/'],
    }


def faq_from(soup):
    qs = []
    for det in soup.find_all('details'):
        s = det.find('summary')
        p = det.find('p')
        if s and p:
            q = s.get_text(' ', strip=True)
            a = p.get_text(' ', strip=True)
            if '[' in a:
                continue
            qs.append({'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}})
    return qs


def first_price(text):
    m = re.search(r'от\s*([\d\s ]+)\s*₸|([\d\s ]+)\s*₸ бастап', text)
    if not m:
        return None
    return int(re.sub(r'\D', '', m.group(1) or m.group(2)))


def page(lang, board, base, noindex, pages_meta):
    path, kind = PAGES[board]
    css, body, title = build_board(board, lang, '.dv', True, True)
    phone_css = phone_body = ''
    if board in PHONE_BOARD:
        phone_css, phone_body, _ = build_board(PHONE_BOARD[board], lang, '.mv', False, True)
    soup = BeautifulSoup(body, 'html.parser')
    page_price = first_price(soup.get_text(' '))
    if V2:
        page_price = V2.price(board, lang, page_price)
    h1 = soup.find('h1')
    h1t = h1.get_text(' ', strip=True) if h1 else ''
    lead = ''
    if h1:
        nxt = h1.find_next('p')
        lead = nxt.get_text(' ', strip=True) if nxt else ''
    if kind == 'home':
        t, desc = HOME_META[lang]
    else:
        t = T(lang, title)
        if lang == 'kk' and t == title:
            t = h1t + ' — VibroTest'
        desc = short_desc(lead)
        price = page_price
        if kind == 'service' and price and str(price) not in desc.replace(' ', '').replace(' ', ''):
            desc += (f' От {price:,} ₸.' if lang == 'ru' else f' {price:,} ₸ бастап.').replace(',', ' ')
        desc += ' ' + ('Алматы, Аносова 91.' if lang == 'ru' else 'Алматы, Аносов 91.')
    if V2:
        t, desc = V2.meta(board, lang, t, desc, page_price)
    desc = desc[:200]
    url = f'{base}/{lang}/{path}'
    alts = ''.join(f'<link rel="alternate" hreflang="{l}" href="{base}/{l}/{path}">' for l in LANGS)
    alts += f'<link rel="alternate" hreflang="x-default" href="{base}/ru/{path}">'
    og_img = f'{base}/img/' + (re.search(r'/img/(vt-\d\d)-', body).group(1) + '.jpg' if re.search(r'/img/(vt-\d\d)-', body) else 'vt-00.jpg')

    u = UI[lang]
    graph = []
    crumbs = [{'@type': 'ListItem', 'position': 1, 'name': u['crumb_home'], 'item': f'{base}/{lang}/'}]
    if kind == 'home':
        graph.append(org_schema(base, lang))
        graph.append({'@type': 'WebSite', '@id': f'{base}/#site', 'name': 'VibroTest.kz', 'url': f'{base}/{lang}/', 'inLanguage': lang})
    elif kind == 'service':
        price = page_price
        svc = {'@type': 'Service', 'name': h1t, 'description': lead, 'url': url, 'areaServed': {'@type': 'City', 'name': 'Алматы'},
               'provider': {'@id': f'{base}/#vibrotest'}}
        if price:
            svc['offers'] = {'@type': 'Offer', 'priceCurrency': 'KZT', 'price': price,
                             'priceSpecification': {'@type': 'PriceSpecification', 'minPrice': price, 'priceCurrency': 'KZT'}}
        graph += [org_schema(base, lang), svc]
        crumbs += [{'@type': 'ListItem', 'position': 2, 'name': u['crumb_svc'], 'item': f'{base}/{lang}/services/'},
                   {'@type': 'ListItem', 'position': 3, 'name': h1t, 'item': url}]
    elif kind == 'services':
        graph += [org_schema(base, lang), {'@type': 'CollectionPage', 'name': h1t, 'url': url}]
        crumbs.append({'@type': 'ListItem', 'position': 2, 'name': h1t, 'item': url})
    elif kind == 'blog':
        graph.append({'@type': 'CollectionPage', 'name': h1t, 'url': url})
        crumbs.append({'@type': 'ListItem', 'position': 2, 'name': u['crumb_blog'], 'item': url})
    elif kind == 'article':
        day = (V2.art_date(board) if V2 else None) or '2026-10-25'
        graph.append({'@type': 'Article', 'headline': h1t, 'description': lead or desc, 'inLanguage': lang, 'url': url,
                      'image': og_img, 'datePublished': day, 'dateModified': day,
                      'author': {'@type': 'Person', 'name': 'Виктор Новиков', 'jobTitle': 'основатель VibroTest' if lang == 'ru' else 'VibroTest негізін қалаушы'},
                      'publisher': {'@id': f'{base}/#vibrotest'}, 'about': {'@id': f'{base}/#vibrotest'}})
        graph.append(org_schema(base, lang))
        crumbs += [{'@type': 'ListItem', 'position': 2, 'name': u['crumb_blog'], 'item': f'{base}/{lang}/blog/'},
                   {'@type': 'ListItem', 'position': 3, 'name': h1t, 'item': url}]
    if kind != 'home':
        graph.append({'@type': 'BreadcrumbList', 'itemListElement': crumbs})
    faq = faq_from(soup)
    if faq:
        graph.append({'@type': 'FAQPage', 'mainEntity': faq})
    schema = jsonld({'@context': 'https://schema.org', '@graph': graph})

    price_line = ''
    if board == 'svc-vibrostand.dc.html':
        price_line = (f'<div class="bb-price"><span>{"Вибростенд, 25–40 мин" if lang == "ru" else "Вибростенд, 25–40 мин"}</span><b class="num">'
                      f'{"от 7 000 ₸" if lang == "ru" else "7 000 ₸ бастап"}</b></div>')
    sym = ''
    if kind == 'home':
        data = symptom_data(lang)
        for n, it in enumerate(data['items']):
            if V2:
                ru_label = symptom_data('ru')['items'][n]['label']
                it['href'] = V2.SYM_HREF.get(ru_label, it.get('href'))
            if it.get('href'):
                it['url'] = url_for(lang, it['href'])
        for it in data['items']:  # prices live on the services page, not on the home page
            it.pop('price', None)
            it.pop('priceNote', None)
        data['wa'] = WA + '?text='
        sym = '<script>window.VT_SYM=' + json.dumps(data, ensure_ascii=False) + '</script>'

    if phone_body:
        main = f'<div class="d-only">{body}</div><div class="m-only">{phone_body}</div>'
    else:
        main = body
    robots = '<meta name="robots" content="noindex, nofollow">' if noindex else '<meta name="robots" content="index, follow, max-image-preview:large">'
    fonts = (ROOT / 'fonts' / 'fonts.css').read_text(encoding='utf-8')
    preload = ('<link rel="preload" href="/fonts/Geologica-cyrillic.woff2" as="font" type="font/woff2" crossorigin>'
               '<link rel="preload" href="/fonts/Inter-cyrillic.woff2" as="font" type="font/woff2" crossorigin>')
    pages_meta.append({'lang': lang, 'path': path, 'title': t, 'desc': desc, 'kind': kind, 'h1': h1t})
    doc = f'''<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>{html.escape(t)}</title>
<meta name="description" content="{html.escape(desc)}">
{robots}
<link rel="canonical" href="{url}">{alts}
<meta property="og:type" content="{'article' if kind == 'article' else 'website'}"><meta property="og:site_name" content="VibroTest.kz">
<meta property="og:title" content="{html.escape(t)}"><meta property="og:description" content="{html.escape(desc)}">
<meta property="og:url" content="{url}"><meta property="og:image" content="{og_img}"><meta property="og:locale" content="{'ru_RU' if lang == 'ru' else 'kk_KZ'}">
<meta name="theme-color" content="#0A0D12">
<link rel="icon" href="/favicon.png" type="image/png"><link rel="apple-touch-icon" href="/apple-touch-icon.png">
{preload}
<style>{fonts}{BASE_CSS}{V2.CSS if V2 else ''}{css}{phone_css}{V2.light_css(css + phone_css) if V2 else ''}</style>
{schema}
</head>
<body>
{header_html(lang, board)}
<main id="main">{main}</main>
{footer_html(lang)}
{bottom_bar(lang, price_line)}
{sym}<script>{JS}{V2.JS if V2 else ''}</script>
</body>
</html>
'''
    return doc


def map_page():
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex"><title>Карта 2ГИС · VibroTest, Аносова 91</title>
<style>html,body{{margin:0;height:100%;overflow:hidden;background:#151B24;font:14px system-ui,sans-serif}}iframe{{position:absolute;left:0;top:0;border:0;transform-origin:0 0;display:block}}
.nf{{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:12px;height:100%}}.nf a{{color:#5AAEF2;font-weight:700}}</style></head><body>
<div class="nf" id="nf"><a href="{GIS}" target="_top">Открыть VibroTest, Аносова 91 в 2ГИС</a><a href="https://2gis.kz/almaty/center/{LON},{LAT}/zoom/16/routeTab/rsType/car/to/{LON},{LAT}" target="_top">Найти проезд</a></div>
<script>
// 2GIS "firmsonmap" widget. It only renders between 500x400 and 1200x1000 px,
// so on a narrow phone it is drawn at 500 px wide and scaled down to fit the frame.
(function(){{var o={{pos:{{lat:{LAT},lon:{LON},zoom:16}},opt:{{city:'almaty'}},org:'{ORG_ID}'}},f=null;
function fit(){{var w=document.documentElement.clientWidth||window.innerWidth,h=document.documentElement.clientHeight||window.innerHeight;if(!w||!h)return false;
 var tw=Math.min(1200,Math.max(500,w)),k=w/tw,th=Math.min(1000,Math.max(400,Math.round(h/k)));
 if(!f){{f=document.createElement('iframe');f.title='Карта 2ГИС';f.onload=function(){{document.getElementById('nf').style.display='none'}};
  f.src='https://widgets.2gis.com/widget?type=firmsonmap&options='+encodeURIComponent(JSON.stringify(o));document.body.appendChild(f)}}
 f.style.width=tw+'px';f.style.height=th+'px';f.style.transform='scale('+k+')';return true}}
if(!fit()){{var t=setInterval(function(){{if(fit())clearInterval(t)}},100)}}window.addEventListener('resize',fit);window.addEventListener('load',fit)}})();
</script></body></html>
'''


def page_404(base):
    u = UI['ru']
    k = UI['kk']
    fonts = (ROOT / 'fonts' / 'fonts.css').read_text(encoding='utf-8')
    return f'''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><meta name="robots" content="noindex">
<title>{u["n404"][0]} — VibroTest</title><style>{fonts}{BASE_CSS}
.nf{{min-height:100vh;display:flex;flex-direction:column;justify-content:center;gap:20px;max-width:640px;margin:0 auto;padding:40px 20px}}
.nf h1{{font:800 48px/1.05 'Geologica',sans-serif;margin:0}}.nf p{{color:#A9B4C2;font-size:17px;line-height:1.6;margin:0}}</style></head>
<body><div class="nf"><img src="/img/logo-white.png" alt="VibroTest.kz" width="156" height="44" style="height:44px;width:auto">
<h1>{u["n404"][0]}</h1><p>{u["n404"][1]}</p><p lang="kk">{k["n404"][0]}. {k["n404"][1]}</p>
<div style="display:flex;gap:12px;flex-wrap:wrap"><a class="hbtn" href="/ru/">{u["n404"][2]}</a><a class="hbtn" href="/kk/" style="background:#1B2638">{k["n404"][2]}</a><a class="hbtn" href="{WA}" style="background:#1B2638">WhatsApp</a></div></div></body></html>'''


def llms(base, metas):
    svc = [m for m in metas if m['lang'] == 'ru' and m['kind'] == 'service']
    art = [m for m in metas if m['lang'] == 'ru' and m['kind'] == 'article']
    lines = ['# VibroTest.kz', '',
             '> Сервис диагностики и ремонта ходовой части в Алматы: ул. Аносова, 91 (мкр Тастак-3), ежедневно 09:30–19:00, +7 747 495 61 65, WhatsApp https://wa.me/77474956165. Главное отличие: диагностика на вибростенде под нагрузкой с датчиками шума, 25–40 минут, от 7 000 ₸, на руки распечатанное заключение (срочно / можно позже / в норме).',
             '', '## Контакты',
             '- Адрес: Алматы, ул. Аносова, 91, 1 этаж, мкр Тастак-3, остановка «Розыбакиева» в 270 м.',
             '- Часы: ежедневно 09:30–19:00. Телефон и WhatsApp: +7 747 495 61 65.',
             f'- 2ГИС: {GIS} (рейтинг 4,8, 143 оценки).',
             '- Оплата: карта и наличные. Легковые, кроссоверы, джипы, пикапы; грузовые и спецтехнику не обслуживаем.',
             f'- Цены: {base}/ru/services/ и на странице каждой услуги («от», запчасти отдельно).',
             '', '## Услуги']
    lines += [f'- [{m["h1"]}]({base}/ru/{m["path"]}): {m["desc"]}' for m in svc]
    lines += ['', '## Статьи']
    lines += [f'- [{m["h1"]}]({base}/ru/{m["path"]})' for m in art]
    lines += ['', '## Казахская версия', f'- {base}/kk/', '']
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=str(ROOT / 'dist'))
    ap.add_argument('--base', default='https://vibrotest.kz')
    ap.add_argument('--noindex', action='store_true')
    ap.add_argument('--v2', action='store_true', help='build the v2 preview (served under /v2/)')
    a = ap.parse_args()
    out = Path(a.out)
    global KK, V2
    KK = json.loads((ROOT / 'i18n' / 'kk.json').read_text(encoding='utf-8'))
    if a.v2:
        import v2 as V2
        KK.update({k: v for k, v in V2.KK_EXTRA.items() if k not in KK})
        PAGES.update(V2.pages())
        V2.patch_ui(UI)
        a.base += V2.PREFIX
    fix = V2.prefix if V2 else (lambda d: d)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    prep_images(out)
    if V2:
        V2.copy_media(out)
    shutil.copytree(ROOT / 'fonts', out / 'fonts', ignore=shutil.ignore_patterns('*.css'))
    ico = Image.open(ROOT / 'img' / 'logo-blue.png')
    metas = []
    for lang in LANGS:
        for board in PAGES:
            doc = page(lang, board, a.base, a.noindex, metas)
            p = out / lang / PAGES[board][0] / 'index.html'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(fix(doc), encoding='utf-8')
    (out / 'map' / 'anosova').mkdir(parents=True)
    (out / 'map' / 'anosova' / 'index.html').write_text(map_page(), encoding='utf-8')
    (out / '404.html').write_text(fix(page_404(a.base)), encoding='utf-8')
    (out / 'llms.txt').write_text(llms(a.base, metas), encoding='utf-8')
    urls = ''.join(f'<url><loc>{a.base}/{m["lang"]}/{m["path"]}</loc>'
                   + ''.join(f'<xhtml:link rel="alternate" hreflang="{l}" href="{a.base}/{l}/{m["path"]}"/>' for l in LANGS)
                   + '<lastmod>2026-10-25</lastmod></url>' for m in metas)
    (out / 'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">'
                                     + urls + '</urlset>\n', encoding='utf-8')
    robots = ('User-agent: *\nDisallow: /\n' if a.noindex else f'User-agent: *\nAllow: /\nDisallow: /map/\n\nSitemap: {a.base}/sitemap.xml\n')
    (out / 'robots.txt').write_text(robots, encoding='utf-8')
    # root: hosts without rewrites still land on the Russian home
    (out / 'index.html').write_text(fix(
        f'<!doctype html><html lang="ru"><head><meta charset="utf-8"><title>VibroTest</title>'
        f'<link rel="canonical" href="{a.base}/ru/"><meta http-equiv="refresh" content="0; url=/ru/">'
        f'{"<meta name=robots content=noindex>" if a.noindex else ""}</head>'
        f'<body><a href="/ru/">VibroTest.kz</a></body></html>\n'), encoding='utf-8')
    # Apache (ps.kz / Plesk): https without www, / -> /ru/, gzip, cache, headers
    host = a.base.split('://', 1)[-1].strip('/')
    (out / '.htaccess').write_text(HTACCESS.replace('{HOST}', host)
                                   + ('Header set X-Robots-Tag "noindex, nofollow"\n' if a.noindex else ''), encoding='utf-8')
    # Vercel preview
    vc = {'cleanUrls': False, 'trailingSlash': True,
          'redirects': [{'source': '/', 'destination': '/ru/', 'permanent': False}],
          'headers': [{'source': '/fonts/(.*)', 'headers': [{'key': 'Cache-Control', 'value': 'public, max-age=31536000, immutable'}]},
                      {'source': '/img/(.*)', 'headers': [{'key': 'Cache-Control', 'value': 'public, max-age=2592000'}]}]}
    if a.noindex:
        vc['headers'].append({'source': '/(.*)', 'headers': [{'key': 'X-Robots-Tag', 'value': 'noindex, nofollow'}]})
    (out / 'vercel.json').write_text(json.dumps(vc, indent=1), encoding='utf-8')
    fav = Image.open(ROOT / 'img' / 'logo-blue.png').convert('RGBA')
    # favicon: the mark (left square of the logo) on a dark tile
    side = fav.height
    mark = fav.crop((0, 0, side, side))
    for name, size in (('favicon.png', 64), ('apple-touch-icon.png', 180)):
        tile = Image.new('RGBA', (size, size), (10, 13, 18, 255))
        m = mark.resize((round(size * .8), round(size * .8)), Image.LANCZOS)
        tile.alpha_composite(m, ((size - m.width) // 2, (size - m.height) // 2))
        tile.save(out / name)
    if MISSING:
        (ROOT / 'i18n' / 'kk.missing.json').write_text(json.dumps(MISSING, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f'KK missing: {len(MISSING)} strings -> i18n/kk.missing.json', file=sys.stderr)
    else:
        mp = ROOT / 'i18n' / 'kk.missing.json'
        if mp.exists():
            mp.unlink()
    print(f'built {len(metas)} pages -> {out}')


if __name__ == '__main__':
    main()
