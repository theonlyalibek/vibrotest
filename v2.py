"""v2 additions to the build: the service landing pages and the «Где стучит?» car map.

build.py imports this only with --v2; the current site at the root stays as it is.
"""
import html, json, re
from pathlib import Path
from bs4 import BeautifulSoup
from v2_svc import SVC
from v2_art import ART, DO_H

ROOT = Path(__file__).resolve().parent
LANDINGS = json.loads((ROOT / 'i18n' / 'v2-pages.json').read_text(encoding='utf-8'))
KK_EXTRA = json.loads((ROOT / 'i18n' / 'kk-v2.json').read_text(encoding='utf-8'))
# SEO articles written by tools/v2_articles.py
ARTICLES = json.loads((ROOT / 'i18n' / 'v2-articles.json').read_text(encoding='utf-8'))
KK_EXTRA.update(json.loads((ROOT / 'i18n' / 'kk-v2-art.json').read_text(encoding='utf-8')))
KK_EXTRA.update(json.loads((ROOT / 'i18n' / 'kk-v2-extra.json').read_text(encoding='utf-8')))
PREFIX = '/v2'

# price-row name -> landing board, so rows on the services and category pages link to the landing
ROW_LINK = {}
for p in LANDINGS:
    for r in p['rows']:
        ROW_LINK.setdefault(r, p['board'])
ROW_LINK['Стенд и двигатель перед покупкой'] = 'l-pered-pokupkoy.dc.html'
ROW_LINK['Диагностика ходовой на вибростенде'] = 'svc-vibrostand.dc.html'
ROW_LINK['Компьютерная диагностика двигателя'] = 'svc-engine.dc.html'

_KK = json.loads((ROOT / 'i18n' / 'kk.json').read_text(encoding='utf-8'))
STORY_END = {h for r in ('Вы видите все неисправности и решаете сами, что менять', 'Как проходит диагностика') for h in (r, _KK.get(r, r))}
SERVICES_H2 = {h for r in ('С чем приезжают', 'С чем приезжают к нам') for h in (r, _KK.get(r, r))}
DIAG_H2 = {h for r in ('Как проходит диагностика',) for h in (r, _KK.get(r, r))}
# home copy: plainer headings and one name for the booking button (ru, kk)
RETITLE = {
    'Запишитесь за минуту': ('Запись на диагностику', 'Диагностикаға жазылу'),
    'Ремонтируем ходовую машин от 2010 года, включая новые китайские': ('Машины от 2010 года, в том числе китайские', '2010 жылдан бергі көліктер, оның ішінде қытайлық'),
    'Мастера ищут стук руками и на слух, а не наугад': ('Мастера ищут стук руками и на слух', 'Шеберлер тықылды қолмен және құлақпен іздейді'),
    'Записаться в WhatsApp': ('Записаться на диагностику', 'Диагностикаға жазылу'),
}
PRICE_FAQ = (('Сколько стоит диагностика?', 'Цена зависит от кузова: седан, кроссовер, джип или пикап. Все цены на странице', 'Услуги и цены'),
             ('Диагностика қанша тұрады?', 'Баға шанаққа байланысты: седан, кроссовер, джип немесе пикап. Барлық бағалар мына бетте:', 'Қызметтер мен бағалар'))

# symptom picker on the home page: send people to the narrow page when there is one
SYM_HREF = {'Стук или люфт в руле': 'l-tyagi.dc.html', 'Хруст при повороте': 'l-shrus.dc.html',
            'Гул растёт со скоростью': 'l-stupica.dc.html', 'Машину раскачивает': 'l-amortizatory.dc.html',
            'Перед покупкой авто': 'l-pered-pokupkoy.dc.html'}


def pages():
    out = {p['board']: (f'services/{p["slug"]}/', 'service') for p in LANDINGS}
    out.update({a['board']: (f'blog/{a["slug"]}/', 'article') for a in ARTICLES})
    out.update({'contacts.dc.html': ('contacts/', 'page'), 'privacy.dc.html': ('privacy/', 'page')})
    return out


def copy_media(out):
    """Real photos and videos from the shop, served only by the v2 build."""
    import shutil
    shutil.copytree(ROOT / 'media', out / 'media', dirs_exist_ok=True)


VIDEOS = {'art-lixiang-l7.dc.html': (
    ('lixiang-l7-do', ('LiXiang L7 до ремонта: подвеска снизу', 'LiXiang L7 жөндеуге дейін: аспа астынан')),
    ('lixiang-l7-osmotr', ('LiXiang L7 до ремонта: рычаги и стойки', 'LiXiang L7 жөндеуге дейін: рычагтар мен тіректер')),
    ('lixiang-l7-reyka', ('LiXiang L7: реставрация рулевой рейки', 'LiXiang L7: рульдік рейканы қалпына келтіру')),
    ('lixiang-l7-rychagi', ('LiXiang L7: старые и новые рычаги, установка', 'LiXiang L7: ескі және жаңа рычагтар, орнату')))}


def videos(board, base, lang):
    """VideoObject entries for an article's own workshop videos."""
    day = art_date(board)
    return [{'@type': 'VideoObject', 'name': t[lang == 'kk'], 'description': t[lang == 'kk'],
             'thumbnailUrl': f'{base}/media/{v}.jpg', 'contentUrl': f'{base}/media/{v}.mp4',
             'uploadDate': day, 'publisher': {'@id': f'{base}/#vibrotest'}} for v, t in VIDEOS.get(board, ())]


def art_date(board):
    return next((a['date'] for a in ARTICLES if a['board'] == board), None)


def blog_cards(soup, lang, url_for):
    """Blog: the new articles go first in the card grid, in the same card markup."""
    grid = soup.select_one('.g3')
    first = grid.find('a', class_='card') if grid else None
    if first is None:
        return
    i = 0 if lang == 'ru' else 1
    old = re.search(r'/img/(vt-\d+)-800', first.img['src']).group(1)
    for a in ARTICLES:
        c = BeautifulSoup(str(first), 'html.parser').a
        c['href'] = url_for(lang, a['board'])
        img = c.img
        img['src'] = img['src'].replace(old, a['img'])
        img['srcset'] = img['srcset'].replace(old, a['img'])
        img['alt'] = a['alt'] if lang == 'ru' else _KK.get(a['alt'], a['alt'])
        if a.get('src'):
            img['src'] = a['src']
            img['alt'] = a['alt2'][i]
            for k in ('srcset', 'sizes'):
                img.attrs.pop(k, None)
        c.find(class_='meta').string = f"{a['cat'][i] or _KK.get(a['cat'][0], a['cat'][0])} · {a['min']} минут"
        c.h3.string = a['h1'][i]
        first.insert_before(c)


def link_rows(soup, current):
    """Wrap the name in each price row with a link to its landing page."""
    for row in soup.select('.prow'):
        first = row.find('span')
        if first is None or first.find('a'):
            continue
        name = first.get_text(' ', strip=True)
        target = ROW_LINK.get(name)
        if not target or target == current:
            continue
        a = soup.new_tag('a', href=target)
        a['class'] = 'plink'
        for c in list(first.contents):
            a.append(c.extract())
        first.append(a)


def services_list(soup, lang):
    """«Услуги»: each row leads to its service page; the prices live there, next to the full description."""
    more = ('Подробнее', 'Толығырақ')[lang != 'ru']
    for row in soup.select('.prow'):
        card = row.find_parent(class_='card')
        link = row.find('a', class_='plink')
        lnk = card.find('a', class_='lnk') if card else None
        href = link['href'] if link else (lnk['href'] if lnk else None)
        for x in row.select('.num, .pbook'):
            x.decompose()
        if not href:
            continue
        if link:
            link.unwrap()
        row.append(BeautifulSoup(f'<a class="pgo" href="{href}">{more}<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" aria-hidden="true"><path d="M9 6l6 6-6 6"/></svg></a>', 'html.parser'))
        row['class'] = row.get('class', []) + ['prow-go']
    h1 = soup.find('h1')
    lead = h1.find_next('p') if h1 else None
    if lead:
        lead.string = SVC_LEAD[lang != 'ru']
    # the «start here» card: name and what you get, the price is on its page
    for num in soup.find_all('span', class_='num'):
        if num.find_parent('section') is (h1.find_parent('section') if h1 else None):
            num.decompose()


SVC_LEAD = ('Выберите услугу: на её странице цена работы, как мы её делаем и ответы на частые вопросы. Запчасти считаем отдельно, точную сумму мастер называет после диагностики.',
            'Қызметті таңдаңыз: оның бетінде жұмыс бағасы, қалай істейтініміз және жиі сұрақтарға жауап бар. Қосалқы бөлшектер бөлек, нақты соманы шебер диагностикадан кейін айтады.')


# ---------- «Где стучит?» ----------

T2 = {
    'h': ('Что не так с машиной?', 'Көлікте не ақау?'),
    'sub': ('Выберите узел: покажем частые симптомы и цену работы. Точно скажет только диагностика.',
            'Түйінді таңдаңыз: жиі белгілер мен жұмыс бағасын көрсетеміз. Нақтысын тек диагностика айтады.'),
    'book': ('Записаться', 'Жазылу'),
    'swipe': ('Листайте вправо', 'Оңға қарай сырғытыңыз'),
    'sub_home': ('Выберите узел: покажем частые симптомы и чем мы поможем. Точно скажет только диагностика.',
                 'Түйінді таңдаңыз: жиі белгілер мен қалай көмектесетінімізді көрсетеміз. Нақтысын тек диагностика айтады.'),
    'all': ('Все услуги', 'Барлық қызметтер'),
    'from': ('от {p}', '{p} бастап'),
    'unsure': ('Не знаете, где проблема? Начните с диагностики на вибростенде', 'Ақау қайда екенін білмейсіз бе? Вибростендтегі диагностикадан бастаңыз'),
    'wa': ('Здравствуйте! Хочу записаться в VibroTest: {x}.', 'Сәлеметсіз бе! VibroTest-ке жазылғым келеді: {x}.'),
    'aria': ('Схема автомобиля с узлами ходовой', 'Жүріс бөлігі түйіндері бар көлік сызбасы'),
}

# x, y in the 1000x340 drawing; links: (board, ru, kk)
NODES = [
    ('stab', 380, 220, ('Стабилизатор', 'Стабилизатор'),
     ('Мелкий стук на неровностях и брусчатке.', 'Кедір-бұдыр мен тас төсемде ұсақ тықыл.'), 3000,
     [('l-stabilizator.dc.html', 'Стойки и втулки стабилизатора', 'Стабилизатор тіректері мен втулкалары')]),
    ('arms', 320, 280, ('Рычаги и сайлентблоки', 'Рычагтар мен сайлентблоктар'),
     ('Глухой удар на ямах, машину уводит при торможении.', 'Шұңқырда күңгірт соққы, тежегенде көлікті бір жаққа тартады.'), 3000,
     [('l-saylentbloki.dc.html', 'Замена сайлентблоков', 'Сайлентблоктарды ауыстыру'), ('l-rychagi.dc.html', 'Замена рычагов', 'Рычагтарды ауыстыру')]),
    ('strut', 285, 165, ('Амортизаторы и опоры', 'Амортизаторлар мен тіректер'),
     ('Машину раскачивает после кочки, скрип при повороте руля на месте.', 'Кедір-бұдырдан кейін көлік тербеледі, орнында руль бұрғанда шиқылдайды.'), 10000,
     [('l-amortizatory.dc.html', 'Замена амортизаторов', 'Амортизаторларды ауыстыру')]),
    ('hub', 215, 262, ('Ступица и ШРУС', 'Күпшек және ШРУС'),
     ('Гул растёт со скоростью или хруст при повороте.', 'Гуіл жылдамдықпен күшейеді немесе бұрылғанда сықырлайды.'), 5000,
     [('l-stupica.dc.html', 'Подшипник ступицы', 'Күпшек подшипнигі'), ('l-shrus.dc.html', 'Замена ШРУСа', 'ШРУС-ты ауыстыру')]),
    ('steer', 128, 250, ('Рулевое управление', 'Рульдік басқару'),
     ('Стук отдаёт в руль, люфт, руль тяжёлый.', 'Тықыл рульге беріледі, люфт бар, руль ауыр.'), 3000,
     [('l-tyagi.dc.html', 'Рулевые тяги и наконечники', 'Рульдік тартқыштар мен ұштықтар'), ('svc-steering-rack.dc.html', 'Рулевые рейки', 'Рульдік рейкалар')]),
    ('cool', 70, 195, ('Радиатор и патрубки', 'Радиатор және патрубкалар'),
     ('Лужа под машиной, запах антифриза, мотор греется.', 'Көлік астында шалшық, антифриз иісі, қозғалтқыш қызады.'), 3000,
     [('svc-cooling.dc.html', 'Радиаторы и патрубки', 'Радиаторлар мен патрубкалар')]),
    ('engine', 200, 170, ('Двигатель', 'Қозғалтқыш'),
     ('Горит Check Engine, мотор троит или тянет хуже.', 'Check Engine жанады, қозғалтқыш дірілдейді немесе нашар тартады.'), 5000,
     [('svc-engine.dc.html', 'Диагностика двигателя', 'Қозғалтқыш диагностикасы')]),
    ('rear', 690, 226, ('Задняя подвеска', 'Артқы аспа'),
     ('Задняя часть «гуляет» на скорости, стук сзади на кочках.', 'Жылдамдықта артқы жағы «ойнайды», кедір-бұдырда артта тықыл.'), 3000,
     [('l-saylentbloki.dc.html', 'Плавающие сайлентблоки', 'Қалқымалы сайлентблоктар'), ('svc-suspension.dc.html', 'Ремонт подвески', 'Аспаны жөндеу')]),
    ('brakes', 790, 262, ('Тормоза', 'Тежегіштер'),
     ('Скрип, биение в руль или педаль при торможении.', 'Тежегенде шиқыл, рульге немесе педальға соғу.'), 5000,
     [('svc-brakes.dc.html', 'Колодки и диски', 'Төлкелер мен дискілер')]),
    # not a part of the car: chip only, no dot on the drawing
    ('buy', None, None, ('Проверка перед покупкой', 'Сатып алар алдында тексеру'),
     ('Ходовая на вибростенде и двигатель сканером за один приезд, заключение на руки.', 'Бір келгенде жүріс бөлігі вибростендте, қозғалтқыш сканермен, қорытынды қолға.'), 12000,
     [('l-pered-pokupkoy.dc.html', 'Проверка авто перед покупкой', 'Көлікті сатып алар алдында тексеру')]),
]

CAR = '''<svg class="km-car" viewBox="0 0 1000 340" aria-hidden="true" focusable="false">
<path class="km-body" d="M60,250 L60,200 Q64,182 96,176 L330,148 Q352,146 372,134 L470,84 Q484,76 504,76 L748,76 Q770,76 786,90 L866,150 Q880,160 905,164 L935,170 Q950,174 950,190 L950,250 L870,250 A80,80 0 0 0 710,250 L295,250 A80,80 0 0 0 135,250 Z"/>
<path class="km-glass" d="M392,140 L478,92 Q488,86 500,86 L600,86 L600,140 Z M616,86 L744,86 Q760,86 772,98 L832,140 L616,140 Z"/>
<g class="km-xray">
<rect x="74" y="184" width="22" height="50" rx="4"/>
<rect x="128" y="160" width="150" height="58" rx="10" stroke-dasharray="5 6"/>
<path d="M215,262 L262,160 M790,262 L768,174 M110,244 L250,244 M215,262 L372,214 M215,262 L340,268 M690,226 L790,262 M640,236 L760,236"/>
</g>
<g class="km-wheel"><circle cx="215" cy="262" r="58"/><circle cx="215" cy="262" r="28"/><circle cx="790" cy="262" r="58"/><circle cx="790" cy="262" r="28"/></g>
<path class="km-trim" d="M600,86 L600,232 M392,140 L380,232 M832,140 L840,232"/><path class="km-light" d="M62,196 L92,190 L96,204 L64,208 Z M936,178 L948,182 L948,200 L934,198 Z"/>
<path class="km-road" d="M20,322 L980,322"/>
</svg>'''

CSS = '''
.km{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:40px;align-items:start}
.km-hd{display:flex;flex-direction:column;gap:14px;margin-bottom:32px}
.km-hd h2{font:800 clamp(30px,3.4vw,46px)/1.06 'Geologica',system-ui,sans-serif;letter-spacing:-.02em;margin:0}
.km-hd p{color:#A9B4C2;font-size:17px;line-height:1.6;margin:0;max-width:640px}
.km-fig{position:relative;border-radius:16px;background:#0E131A;border:1px solid rgba(255,255,255,.08);padding:28px 20px 18px}
.km-car{display:block;width:100%;height:auto}
.km-body{fill:#141B25;stroke:#3A4757;stroke-width:2.5}
.km-glass{fill:#0E1520;stroke:#2B3644;stroke-width:2}
.km-xray *{fill:none;stroke:#2F6EA3;stroke-width:2;opacity:.55}
.km-wheel circle{fill:#0B1018;stroke:#56647A;stroke-width:3}
.km-wheel circle:nth-child(2n){fill:none;stroke:#2B3644}
.km-trim{fill:none;stroke:#252F3C;stroke-width:2}.km-light{fill:#5AAEF2;opacity:.5}
.km-fig{overflow:hidden}
.km-road{stroke:#2B3644;stroke-width:2;stroke-dasharray:2 10}
.km-dots{position:absolute;inset:28px 20px 18px}
.km-dot{position:absolute;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:0;padding:0;background:transparent;cursor:pointer;display:flex;align-items:center;justify-content:center;font:600 12px 'JetBrains Mono',monospace;color:#FFFFFF}
.km-dot::before{content:'';position:absolute;inset:7px;border-radius:50%;background:#0071BC;box-shadow:0 0 0 2px #0A0D12}
.km-dot::after{content:'';position:absolute;inset:7px;border-radius:50%;border:2px solid #5AAEF2;opacity:0;animation:kmPulse 2.6s ease-out infinite}
.km-dot span{position:relative}
.km-dot[aria-pressed=true]::before{background:#FFFFFF}.km-dot[aria-pressed=true] span{color:#0071BC}
.km-dot[aria-pressed=true]::after{animation-duration:1.4s}
.km-dot:focus-visible{outline:2px solid #5AAEF2;outline-offset:2px}
@keyframes kmPulse{0%{transform:scale(1);opacity:.8}100%{transform:scale(2.3);opacity:0}}
.km-list{display:flex;flex-wrap:wrap;gap:8px;margin-top:18px}
.km-chip{min-height:40px;padding:0 14px;border-radius:999px;border:1px solid rgba(255,255,255,.16);background:transparent;color:#D5DCE5;font:500 14px 'Inter',system-ui,sans-serif;cursor:pointer;display:inline-flex;align-items:center;gap:8px}
.km-chip b{font:600 12px 'JetBrains Mono',monospace;color:#5AAEF2}
.km-chip[aria-pressed=true]{background:#0071BC;border-color:#0071BC;color:#FFFFFF}.km-chip[aria-pressed=true] b{color:#FFFFFF}
.km-panel{display:flex;flex-direction:column;gap:16px;padding:32px;border-radius:18px;background:#11161E;border:1px solid rgba(255,255,255,.08);min-height:100%}
.km-panel[hidden]{display:none}
.km-panel .k{font:600 13px 'JetBrains Mono',monospace;color:#5AAEF2}
.km-panel h3{font:700 28px/1.12 'Geologica',system-ui,sans-serif;margin:0}
.km-panel p{color:#A9B4C2;font-size:16px;line-height:1.65;margin:0}
.km-price{font:600 30px 'JetBrains Mono',monospace;letter-spacing:-.02em}
.km-links{display:flex;flex-direction:column;border-top:1px solid rgba(255,255,255,.1)}
.km-links a{display:flex;justify-content:space-between;gap:12px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.1);color:#EEF2F7;font-weight:600}
.km-links a:hover{color:#5AAEF2}
.km-panel .btn{align-self:flex-start;margin-top:auto}
.km-unsure{display:inline-block;margin-top:22px;color:#8A96A6;font-size:15px}
.km-unsure a{color:#5AAEF2}
.km-all{display:inline-flex;align-items:center;gap:8px;margin-top:32px;min-height:52px;padding:0 24px;border-radius:12px;background:#1B2638;color:#EEF2F7!important;font-weight:600;font-size:15px}
.km-all:hover{background:#243248;color:#FFFFFF}
.plink{color:inherit;border-bottom:1px solid currentColor;border-bottom-color:rgba(127,140,160,.45)}
.plink:hover{color:#0071BC}
.prow .plink:hover{color:#5AAEF2}
.km-swipe{display:none}
@media (max-width:899px){.km{display:block}
.km-fig{padding:14px 6px 8px}.km-dots{inset:14px 6px 8px;pointer-events:none}
.km-dot{width:14px;height:14px;margin:-7px 0 0 -7px;font-size:0}.km-dot::before{inset:2px;box-shadow:none;opacity:.55}.km-dot::after{display:none}
.km-dot[aria-pressed=true]{width:30px;height:30px;margin:-15px 0 0 -15px;font-size:11px}.km-dot[aria-pressed=true]::before{inset:5px;opacity:1;background:#FFFFFF;box-shadow:0 0 0 6px rgba(0,113,188,.35)}
.km-dot[aria-pressed=true]::after{display:block;inset:5px}
.km-list{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:16px}
.km-chip{min-height:46px;padding:8px 12px;font-size:14px;line-height:1.25;justify-content:center;text-align:center;border-radius:12px}.km-chip b{font-size:13px}
.km-swipe{display:flex;align-items:center;gap:6px;margin-top:8px;font-size:13px;color:#6F7B8B}
.km-side{margin-top:16px}
.km-panel{padding:22px 20px;gap:12px}.km-panel h3{font-size:22px}.km-price{font-size:24px}.km-panel .btn{width:100%}
.km-unsure{margin-top:16px;font-size:14px}.km-all{margin-top:20px}.km-hd{margin-bottom:18px}.km-hd p{font-size:15px}}

.ft-card{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:64px;align-items:start}
.ft-main{display:flex;flex-direction:column;gap:22px}
.ft-main h2{font:800 clamp(30px,3.6vw,50px)/1.04 'Geologica',system-ui,sans-serif;letter-spacing:-.02em;margin:0}
.ft-main>p{color:#A9B4C2;font-size:17px;line-height:1.65;margin:0}
.ft-steps{list-style:none;margin:4px 0 0;padding:0;counter-reset:st;border-top:1px solid rgba(255,255,255,.1)}
.ft-steps li{counter-increment:st;display:grid;grid-template-columns:28px 1fr;column-gap:12px;row-gap:6px;padding:18px 0;border-bottom:1px solid rgba(255,255,255,.1)}
.ft-steps li::before{content:counter(st);grid-row:span 2;color:#5AAEF2;font-weight:600;font-size:16px;line-height:1.4}
.ft-steps b{font-size:16px;color:#EEF2F7}.ft-steps span{font-size:15px;line-height:1.55;color:#A9B4C2}
.ft-cta{display:flex;align-items:center;gap:26px;flex-wrap:wrap;margin-top:auto}
.ft-cta .lnk{color:#EEF2F7;font-weight:600;font-size:15px;border-bottom:1px solid rgba(255,255,255,.28);padding-bottom:3px}
.ft-side{display:flex;flex-direction:column;gap:16px}
.ft-pic{position:relative;border-radius:14px;overflow:hidden;background:#11161E;aspect-ratio:4/5}
.ft-pic img{width:100%;height:100%;object-fit:cover;display:block}
.ft-get{padding:22px;border-radius:16px;background:#FFFFFF;color:#0B1220;box-shadow:0 10px 30px rgba(0,0,0,.25)}
.ft-get h3{font:700 19px 'Geologica',system-ui,sans-serif;margin:0 0 8px}
.ft-get ul{list-style:none;margin:0;padding:0}
.ft-row{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid #E6EAF0;font-size:15px;line-height:1.45}
.ft-st{flex:none;min-width:104px;padding:4px 10px;border-radius:999px;font-size:13px;font-weight:600;text-align:center}
.ft-st.urgent{background:#FDE8E8;color:#B42318}.ft-st.later{background:#FEF3D7;color:#8A5A00}.ft-st.ok{background:#DDF4E6;color:#17663A}
.ft-get .ft-st{width:142px;min-width:0;padding:5px 8px}.ft-get .ft-row:last-child{border-bottom:0;padding-bottom:6px}.ft-get h3{padding-bottom:12px;border-bottom:1px solid #E6EAF0}
.ft-get p{margin:8px 0 0;padding-top:12px;border-top:1px solid #E6EAF0;font-size:13px;color:#5B6576}
.dots{display:flex;gap:6px;margin-top:14px}.dots span{width:6px;height:6px;border-radius:3px;background:#3A4556;transition:width .2s,background .2s}.dots span.on{width:18px;background:#5AAEF2}
.chips{list-style:none;margin:14px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.chips li{padding:8px 12px;border-radius:10px;background:#11161E;border:1px solid rgba(255,255,255,.08);font-size:14px;color:#D5DCE5}
.chips.cn li{border-color:rgba(90,174,242,.35);color:#EEF2F7}
.chips-h{margin:18px 0 0;font-size:13px;color:#8A96A6}
@media (max-width:899px){.ft-card{grid-template-columns:minmax(0,1fr);gap:20px}
.ft-main{gap:16px}.ft-main>p{font-size:15px}.ft-pic{aspect-ratio:16/10}
.ft-cta{gap:18px}.ft-cta .btn{width:100%}.ft-get{padding:20px 18px;margin-top:12px}.ft-st{min-width:112px}
.ft-card{display:flex;flex-direction:column;gap:16px}.ft-main,.ft-side{display:contents}
.ft-main h2{order:1}.ft-main>p{order:2}.ft-pic{order:3}.ft-steps{order:4}.ft-cta{order:5;margin-top:4px}.ft-get{order:6}
.stack{display:flex!important;flex-direction:column!important;gap:12px!important;overflow:visible!important;margin:16px 0 0!important;padding:0!important}.stack>*{width:auto!important;flex:none!important}
.brands{margin-top:18px;font-size:17px;line-height:1.75;color:#EEF2F7;font-weight:600}.brands i{font-style:normal;color:#4A5568}.brands span{white-space:nowrap}.brands-h{margin-top:22px;margin-bottom:-10px;font-size:14px;color:#8A96A6}
.tap{display:inline-block;padding:12px 0;margin:-12px 0}}
.bb{transition:transform .25s ease,opacity .25s ease}
.bb.bb-off{transform:translateY(110%);opacity:0;pointer-events:none}
@media (prefers-reduced-motion:reduce){.km-dot::after,.km-fig::after{animation:none}.km-fig::after{display:none}}
'''

JS = r'''
// car map: a dot or a chip picks the node and its card shows.
[].forEach.call(document.querySelectorAll('[data-km]'),function(km){
 var btns=km.querySelectorAll('[data-node]'),panels=km.querySelectorAll('.km-panel');
 [].forEach.call(btns,function(b){b.addEventListener('click',function(){var id=b.getAttribute('data-node');
  [].forEach.call(btns,function(x){x.setAttribute('aria-pressed',x.getAttribute('data-node')===id?'true':'false')});
  [].forEach.call(panels,function(p){p.hidden=p.getAttribute('data-panel')!==id})})});
});
[].forEach.call(document.querySelectorAll('[data-km-m]'),function(km){
 var cds=km.querySelectorAll('.km-cd'),pns=km.querySelectorAll('.km-pn'),dots=km.querySelectorAll('.km-dot'),cur='';
 function show(id){cur=id;
  [].forEach.call(cds,function(c){c.setAttribute('aria-expanded',c.getAttribute('data-node')===id?'true':'false')});
  [].forEach.call(pns,function(p){p.hidden=p.getAttribute('data-panel')!==id});
  [].forEach.call(dots,function(d){d.setAttribute('aria-pressed',d.getAttribute('data-node')===id?'true':'false')})}
 [].forEach.call(cds,function(c){c.addEventListener('click',function(){var id=c.getAttribute('data-node');show(cur===id?'':id)})});
 [].forEach.call(km.querySelectorAll('.km-x'),function(x){x.addEventListener('click',function(){show('')})});
});
// carousels with dots: the active dot follows the swipe
[].forEach.call(document.querySelectorAll('[data-dots]'),function(r){var d=r.parentNode.querySelector('.dots');if(!d)return;var dots=d.children;
 r.addEventListener('scroll',function(){var w=r.children[0].getBoundingClientRect().width+(parseFloat(getComputedStyle(r).columnGap)||12),k=r.scrollLeft>=r.scrollWidth-r.clientWidth-4?dots.length-1:Math.min(dots.length-1,Math.round(r.scrollLeft/w));
  [].forEach.call(dots,function(s,j){s.classList.toggle('on',j===k)});r.parentNode.classList.toggle('at-end',k===dots.length-1)},{passive:true})});
// the bottom «Записаться» opens the three-field form when the page has one
(function(){var b=document.querySelector('.bb .mbtn');if(!b)return;b.addEventListener('click',function(e){
 var f=[].filter.call(document.querySelectorAll('form[data-book]'),function(x){return x.offsetParent!==null})[0];if(!f)return;
 e.preventDefault();f.scrollIntoView({behavior:'smooth',block:'center'});setTimeout(function(){var i=f.querySelector('input,select');if(i)i.focus({preventScroll:true})},500)})})();
// phones: the bottom «Записаться / звонок» bar steps aside while another booking button is on screen
(function(){var bb=document.querySelector('.bb');if(!bb||!('IntersectionObserver' in window))return;
 var seen=new Set(),io=new IntersectionObserver(function(es){es.forEach(function(e){e.intersectionRatio>=.5?seen.add(e.target):seen.delete(e.target)});
  bb.classList.toggle('bb-off',seen.size>0)},{threshold:[0,.5,1]});
 [].forEach.call(document.querySelectorAll('main a[href*="wa.me"].btn, main .btn-p, main form[data-book] [type=submit], main .mbtn'),function(b){
  if(b.offsetParent!==null||getComputedStyle(b).display!=='none')io.observe(b)});
})();
'''


def km_phone(lang, url_for, wa, sid, prices, dots, head, tail):
    """Phones: the drawing on top, a swipeable row of part cards; a tapped card opens its panel below the row."""
    i = 0 if lang == 'ru' else 1
    from urllib.parse import quote
    cards, panels = [], []
    for key, x, y, title, text, price, links in NODES:
        t = html.escape(title[i])
        cards.append(f'<button type="button" class="km-cd" data-node="{key}" aria-expanded="false"><b>{t}</b><span>{html.escape(text[i])}</span></button>')
        rows = ''.join(f'<a href="{url_for(lang, b)}">{html.escape(l[i])}</a>' for b, *l in links)
        msg = quote(T2['wa'][i].replace('{x}', title[i].lower() if lang == 'ru' else title[i]), safe='')
        extra = ''
        if prices:
            p = f'{price:,}'.replace(',', ' ') + ' ₸'
            extra = f'<div class="km-pb"><span class="km-price">{T2["from"][i].format(p=p)}</span><a class="btn btn-p" href="{wa}?text={msg}">{T2["book"][i]}</a></div>'
        panels.append(f'<div class="km-pn" data-panel="{key}" hidden><div class="km-pn-h"><b>{t}</b>'
                      f'<button type="button" class="km-x" aria-label="{("Закрыть", "Жабу")[i]}"></button></div>{rows}{extra}</div>')
    dots_off = ''.join(dots).replace('aria-pressed="true"', 'aria-pressed="false"')
    return (f'<section{f' id="{sid}"' if sid else ''} class="km-sec km-m" data-km-m style="padding: 48px 0 24px"><div>'
            f'<div class="km-hd" style="padding: 0 16px"><h2>{T2["h"][i]}</h2></div>'
            f'<div style="padding: 0 16px"><div class="km-fig" role="group" aria-label="{T2["aria"][i]}">{CAR}<div class="km-dots">{dots_off}</div></div></div>'
            f'<div class="km-rw"><div class="km-rail" data-dots>{"".join(cards)}</div>'
            f'<div class="dots km-rd" aria-hidden="true">{"".join("<span class=on></span>" if n == 0 else "<span></span>" for n in range(len(cards)))}</div></div>'
            f'<div style="padding: 0 16px">{"".join(panels)}'
            f'<span class="km-unsure">{head}? <a href="{url_for(lang, "svc-vibrostand.dc.html")}">{tail.strip()}</a></span>'
            + ('' if prices else f'<a class="km-all" href="{url_for(lang, "Services.dc.html")}">{T2["all"][i]}</a>')
            + '</div></div></section>')


def knock_map(lang, url_for, wa, phone=False, sid='', prices=True):
    i = 0 if lang == 'ru' else 1
    from urllib.parse import quote
    dots, chips, panels = [], [], []
    for n, (key, x, y, title, text, price, links) in enumerate(NODES, 1):
        on = n == 1
        t = html.escape(title[i])
        if x is not None:
            dots.append(f'<button type="button" class="km-dot" data-node="{key}" aria-pressed="{"true" if on else "false"}" '
                        f'aria-label="{t}" style="left:{x / 10:.1f}%;top:{y / 3.4:.1f}%"></button>')
        chips.append(f'<button type="button" class="km-chip" data-node="{key}" aria-pressed="{"true" if on else "false"}">{t}</button>')
        p = f'{price:,}'.replace(',', ' ') + ' ₸'
        rows = ''.join(f'<a href="{url_for(lang, b)}"><span>{html.escape(l[i])}</span></a>' for b, *l in links)
        msg = quote(T2['wa'][i].replace('{x}', title[i].lower() if lang == 'ru' else title[i]), safe='')
        panels.append(f'<div class="km-panel" data-panel="{key}"{"" if on else " hidden"}><h3>{t}</h3>'
                      f'<p>{html.escape(text[i])}</p>' + (f'<div class="km-price">{T2["from"][i].format(p=p)}</div>' if prices else '') +
                      f'<div class="km-links">{rows}</div>' + (f'<a class="btn btn-p" href="{wa}?text={msg}">{T2["book"][i]}</a>' if prices else '') + '</div>')
    unsure = T2['unsure'][i]
    head, tail = unsure.rsplit('?', 1) if '?' in unsure else ('', unsure)
    if phone:
        return km_phone(lang, url_for, wa, sid, prices, dots, head, tail)
    return (f'<section{f' id="{sid}"' if sid else ''} class="km-sec" data-km style="padding: {"56px 16px 16px" if phone else "120px 0 0"}"><div class="{"" if phone else "w"}">'
            f'<div class="km-hd"><h2>{T2["h"][i]}</h2><p>{T2["sub" if prices else "sub_home"][i]}</p></div>'
            f'<div class="km"><div><div class="km-fig" role="group" aria-label="{T2["aria"][i]}">{CAR}<div class="km-dots">{"".join(dots)}</div></div>'
            f'<div class="km-list">{"".join(chips)}</div>'
            f'<span class="km-unsure">{head}? <a href="{url_for(lang, "svc-vibrostand.dc.html")}">{tail.strip()}</a></span></div>'
            f'<div class="km-side">{"".join(panels)}</div></div>'
            + ('' if prices else f'<a class="km-all" href="{url_for(lang, "Services.dc.html")}">{T2["all"][i]}</a>')
            + '</div></section>')



# ---------- home: the stand comes first, like the injector card on viton.kz ----------

F = {
    'h': ('Диагностика ходовой на вибростенде', 'Вибростендте жүріс бөлігінің диагностикасы'),
    'p': ('Машина стоит на платформах своим весом, стенд раскачивает подвеску, как на кочках. Датчики шума на рычагах, стойках и тягах показывают, какой узел стучит.',
          'Көлік платформаларда өз салмағымен тұрады, стенд аспаны кедір-бұдырдағыдай тербетеді. Рычагтардағы, тіректер мен тартқыштардағы шу датчиктері қай түйін тықылдайтынын көрсетеді.'),
    'steps': (
        ('Ставим машину на стенд', 'Көлікті стендке қоямыз',
         'Колёса встают на платформы. Подходит седан, кроссовер, джип и пикап.', 'Дөңгелектер платформаларға тұрады. Седан, кроссовер, джип және пикап сияды.'),
        ('Стенд трясёт подвеску', 'Стенд аспаны тербетеді',
         'Как на плохой дороге, только на месте. Датчики слушают каждый узел.', 'Нашар жолдағыдай, бірақ бір орында. Датчиктер әр түйінді тыңдайды.'),
        ('Мастер показывает, что стучит', 'Шебер не тықылдайтынын көрсетеді',
         'Люфт видно своими глазами, без «вроде бы рычаг».', 'Саңылауды өз көзіңізбен көресіз, «рычаг сияқты» деген болжамсыз.'),
        ('Вы получаете акт', 'Сіз акт аласыз',
         'Что срочно, что можно позже, что в норме. Ремонт у нас не обязателен.', 'Не шұғыл, не кейінірек, не қалыпты. Жөндеуді бізде жасау міндетті емес.')),
    'get': ('Что вы получите на руки', 'Қолыңызға не беріледі'),
    'rows': ((('urgent', 'Срочно', 'Стойка стабилизатора, передняя левая'), ('urgent', 'Шұғыл', 'Стабилизатор тірегі, алдыңғы сол жақ')),
             (('later', 'Можно позже', 'Сайлентблок заднего рычага'), ('later', 'Кейінірек болады', 'Артқы рычагтың сайлентблогы')),
             (('ok', 'В норме', 'Рулевая рейка, амортизаторы'), ('ok', 'Қалыпты', 'Рульдік рейка, амортизаторлар'))),
    'cap': ('Так выглядит заключение.', 'Қорытынды осылай көрінеді.'),
    'book': ('Записаться на диагностику', 'Диагностикаға жазылу'),
    'more': ('Как работает стенд', 'Стенд қалай жұмыс істейді'),
    'msg': ('Здравствуйте! Хочу записаться на диагностику на вибростенде.', 'Сәлеметсіз бе! Вибростендте диагностикаға жазылғым келеді.'),
    'alt': ('Колесо автомобиля на платформе вибростенда VibroTest', 'VibroTest вибростенд платформасындағы көлік дөңгелегі'),
}

def stand_feature(lang, url_for, wa, phone=False):
    """The stand and how a visit goes, in one block. The desktop page has the large paper sample right after it,
    so the short «на руки» list stays only on phones."""
    from urllib.parse import quote
    i = 0 if lang == 'ru' else 1
    steps = ''.join(f'<li><b>{st[i]}</b><span>{st[2 + i]}</span></li>' for st in F['steps'])
    rows = ''.join(f'<li class="ft-row"><span class="ft-st {r[i][0]}">{r[i][1]}</span><span>{r[i][2]}</span></li>' for r in F['rows'])
    return (f'<section class="ft-sec" style="padding: {"40px 16px 8px" if phone else "110px 0 0"}"><div class="{"" if phone else "w"}">'
            f'<div class="ft-card"><div class="ft-main"><h2>{F["h"][i]}</h2><p>{F["p"][i]}</p>'
            f'<ol class="ft-steps">{steps}</ol>'
            f'<div class="ft-cta"><a class="btn btn-p" href="{wa}?text={quote(F["msg"][i], safe="")}">{F["book"][i]}</a>'
            f'<a class="lnk" href="{url_for(lang, "svc-vibrostand.dc.html")}">{F["more"][i]}</a></div></div>'
            f'<div class="ft-side"><div class="ft-pic"><img src="/img/vt-01-800.webp" srcset="/img/vt-01-800.webp 800w, /img/vt-01-1600.webp 1600w" '
            f'sizes="(max-width: 900px) 100vw, 40vw" alt="{F["alt"][i]}" loading="lazy" decoding="async">'
            '</div>'
            + (f'<div class="ft-get"><h3>{F["get"][i]}</h3><ul>{rows}</ul><p>{F["cap"][i]}</p></div>' if phone else '')
            + '</div></div></div></section>')


def to_dots(soup):
    """Carousels: dots instead of a «1 / 3» counter."""
    for rail in soup.select('[data-rail]'):
        cnt = soup.find(id=rail['data-rail'])
        n = len([c for c in rail.children if getattr(c, 'name', None)])
        if cnt is None or n < 2:
            continue
        dots = BeautifulSoup('<div class="dots" aria-hidden="true">' + ''.join(
            f'<span{" class=on" if k == 0 else ""}></span>' for k in range(n)) + '</div>', 'html.parser')
        cnt.replace_with(dots)
        rail['data-dots'] = '1'
        del rail['data-rail']


BRANDS = {
    'h': ('Работаем с японскими, корейскими, европейскими и китайскими машинами',
          'Жапон, корей, еуропа және қытай көліктерімен жұмыс істейміз'),
    'cn': ('Li Auto', 'Zeekr', 'Geely', 'Chery', 'Changan', 'Omoda', 'MG', 'Deepal'),
    'rest': ('Toyota', 'Lexus', 'Subaru', 'Honda', 'Hyundai', 'Kia', 'BMW', 'Mercedes-Benz', 'Audi', 'Volkswagen', 'Škoda', 'Volvo'),
    'more': ('и другие', 'және басқалар'),
    'no': ('Грузовые и спецтехнику не обслуживаем.', 'Жүк көліктері мен арнайы техниканы қабылдамаймыз.'),
    'faq': ('Легковые, кроссоверы, джипы и пикапы, в том числе китайские. Грузовые и спецтехнику не берём.',
            'Жеңіл көліктер, кроссоверлер, джиптер мен пикаптар, оның ішінде қытайлық. Жүк көліктері мен арнайы техниканы қабылдамаймыз.'),
}


# every article: (board, slug, ru title, related service boards); the five older ones come from the root build
_OLD_ARTS = (('art-knock.dc.html', 'stuk-v-podveske-na-kochkah', 'Стук в подвеске на кочках: 7 частых причин', ('svc-suspension.dc.html', 'l-stabilizator.dc.html', 'svc-vibrostand.dc.html')),
             ('art-steering-knock.dc.html', 'stuk-v-rule', 'Стучит в руле: рейка, тяги или наконечники', ('svc-steering-rack.dc.html', 'l-tyagi.dc.html')),
             ('art-rack.dc.html', 'restavraciya-rulevoy-reyki', 'Реставрация рулевой рейки или замена: что выбрать', ('svc-steering-rack.dc.html',)),
             ('art-stand-vs-lift.dc.html', 'vibrostend-ili-podemnik', 'Вибростенд или подъёмник: что точнее находит стук', ('svc-vibrostand.dc.html',)),
             ('art-before-buying.dc.html', 'hodovaya-pered-pokupkoy', 'Как проверить ходовую перед покупкой машины', ('l-pered-pokupkoy.dc.html',)))
ALL_ARTS = [(x['board'], x['slug'], tuple(x['h1']), tuple(x.get('svc', ()))) for x in ARTICLES] + \
           [(b, sl, (t, _KK.get(t, t)), svc) for b, sl, t, svc in _OLD_ARTS]
EXTRA_T = {
    'toc': ('Содержание', 'Мазмұны'),
    'read': ('Что ещё почитать', 'Тағы не оқуға болады'),
    'wa': ('Здравствуйте! Пишу с сайта по теме «{t}».', 'Сәлеметсіз бе! Сайттан «{t}» тақырыбы бойынша жазып отырмын.'),
    'arts': ('Статьи по теме', 'Тақырып бойынша мақалалар'),
    'nohelp_h': ('Когда стенд не поможет', 'Стенд қашан көмектеспейді'),
    'nohelp': (('Вибрация на скорости 80–120 км/ч. Чаще всего это балансировка колёс или развал-схождение: их проверяют на балансировочном станке и стенде сход-развала.',
                '80–120 км/сағ жылдамдықтағы діріл. Көбіне бұл дөңгелек теңгерімі немесе развал-схождение: оларды теңгерім станогында және сход-развал стендінде тексереді.'),
               ('Шум двигателя, коробки или выхлопа. Стенд проверяет ходовую и рулевое, для мотора нужна отдельная диагностика.',
                'Қозғалтқыштың, қораптың немесе шығару жүйесінің шуы. Стенд жүріс бөлігі мен рульді тексереді, моторға бөлек диагностика керек.'),
               ('Звук появляется только на холодную или на одной скорости. Тогда мастер едет с вами на короткий тест-драйв.',
                'Дыбыс тек суық күйде немесе бір жылдамдықта шығады. Онда шебер сізбен бірге қысқа тест-драйвқа шығады.')),
}


def art_more(soup, art, c, i):
    """A short «what to do now» plan right before the FAQ, and more questions in it."""
    e = html.escape
    faq_h = {'Частые вопросы', _KK.get('Частые вопросы', 'Жиі қойылатын сұрақтар')}
    fh = next((h for h in art.find_all('h2', recursive=False) if h.get_text(' ', strip=True) in faq_h), None)
    plan = BeautifulSoup(f'<h2>{DO_H[i]}</h2><ol class="doit">' + ''.join(f'<li>{e(x[i])}</li>' for x in c['do']) + '</ol>', 'html.parser')
    if fh is not None:
        fh.insert_before(plan)
    box = next((d.parent for d in art.find_all('details')), None)
    if box is None:
        return
    pm = box.find('svg')
    for q in c['faq']:
        box.append(BeautifulSoup(f'<details><summary>{e(q[0][i])}{pm or ""}</summary><p class="ans">{e(q[1][i])}</p></details>', 'html.parser'))


def article_extras(soup, name, lang, url_for, wa):
    """Articles: a contents list, «Что ещё почитать» after the answer box, and a WhatsApp link that names the topic."""
    i = 0 if lang == 'ru' else 1
    art = soup.find('article', class_='art')
    me = next((x for x in ALL_ARTS if x[0] == name), None)
    if art is None or me is None:
        return
    if name in ART:
        art_more(soup, art, ART[name], i)
    hs = [h for h in art.find_all('h2', recursive=False)]
    if len(hs) >= 3:
        for n, h in enumerate(hs, 1):
            h['id'] = f's{n}'
        toc = BeautifulSoup(f'<nav class="toc" aria-label="{EXTRA_T["toc"][i]}"><b>{EXTRA_T["toc"][i]}</b><ol>'
                            + ''.join(f'<li><a href="#s{n}">{html.escape(h.get_text(" ", strip=True))}</a></li>' for n, h in enumerate(hs, 1))
                            + '</ol></nav>', 'html.parser')
        hs[0].insert_before(toc)
    from urllib.parse import quote
    for a in art.find_all('a', href=re.compile(r'wa\.me')):
        a['href'] = re.sub(r'\?.*$', '', a['href']) + '?text=' + quote(EXTRA_T['wa'][i].format(t=me[2][i]), safe='')
    same = [x for x in ALL_ARTS if x[0] != name and set(x[3]) & set(me[3])]
    rest = [x for x in ALL_ARTS if x[0] != name and x not in same]
    pick = (same + rest)[:3]
    art.append(BeautifulSoup(f'<div class="readmore"><h2>{EXTRA_T["read"][i]}</h2><ul>'
                             + ''.join(f'<li><a href="{url_for(lang, x[0])}">{html.escape(x[2][i])}</a></li>' for x in pick)
                             + '</ul></div>', 'html.parser'))


def service_extras(soup, name, lang, url_for):
    """Service pages: articles that answer the same question; the stand page also says honestly what it will not find."""
    i = 0 if lang == 'ru' else 1
    faq = next((d.find_parent('section') for d in soup.find_all('details') if 'km-it' not in (d.get('class') or [])), None)
    if faq is None:
        return
    arts = [x for x in ALL_ARTS if name in x[3]][:4]
    if name in SVC:
        long_text(soup, faq, SVC[name], i)
    if name == 'svc-vibrostand.dc.html':
        faq.insert_before(BeautifulSoup(
            f'<section class="vt-x" style="padding: 0 0 72px"><div class="w"><h2>{EXTRA_T["nohelp_h"][i]}</h2><ul class="nohelp">'
            + ''.join(f'<li>{html.escape(t[i])}</li>' for t in EXTRA_T['nohelp'])
            + f'</ul><p><a href="{url_for(lang, "svc-engine.dc.html")}">{("Диагностика двигателя", "Қозғалтқыш диагностикасы")[i]}</a></p></div></section>', 'html.parser'))
    if arts:
        faq.insert_before(BeautifulSoup(
            f'<section class="vt-x" style="padding: 0 0 72px"><div class="w"><h2>{EXTRA_T["arts"][i]}</h2><ul class="artlist">'
            + ''.join(f'<li><a href="{url_for(lang, x[0])}">{html.escape(x[2][i])}</a></li>' for x in arts)
            + '</ul></div></section>', 'html.parser'))


def long_text(soup, faq, c, i):
    """Full description before the prices: what the part is, why it wears, a self-check, what moves the price."""
    e = html.escape
    sec = lambda body, last=False: (f'<section class="vt-x svx{" svx-end" if last else ""}" style="padding: clamp(36px, 4.5vw, 64px) 0 {"clamp(45px, 6.94vw, 100px)" if last else "0"}">'
                                    f'<div class="w">{body}</div></section>')
    (h, paras), (wh, wp), (ch, ci, items), (th, rows) = c['d'], c['w'], c['c'], c['t']
    out = sec(f'<h2>{e(h[i])}</h2>' + ''.join(f'<p>{e(p[i])}</p>' for p in paras))
    out += sec(f'<h2>{e(wh[i])}</h2>' + ''.join(f'<p>{e(p[i])}</p>' for p in wp))
    out += sec(f'<h2>{e(ch[i])}</h2><p>{e(ci[i])}</p><ul class="nohelp">' + ''.join(f'<li>{e(x[i])}</li>' for x in items) + '</ul>')
    if 'p' in c:
        ph, pi = c['p']
        out += sec(f'<h2>{e(ph[i])}</h2><ul class="nohelp">' + ''.join(f'<li>{e(x[i])}</li>' for x in pi) + '</ul>')
    head = (('Что влияет', 'Не әсер етеді'), ('Как именно', 'Қалай'))
    out += sec(f'<h2>{e(th[i])}</h2><table class="svx-t"><thead><tr><th>{head[0][i]}</th><th>{head[1][i]}</th></tr></thead><tbody>'
               + ''.join(f'<tr><td>{e(r[i])}</td><td>{e(r[2 + i])}</td></tr>' for r in rows) + '</tbody></table>', last=True)
    price = soup.find('section', class_='prdk')
    (price or faq).insert_before(BeautifulSoup(out, 'html.parser'))
    box = next((d.parent for d in faq.find_all('details')), None)
    if box is None:
        return
    pm = box.find('svg', class_='pm')
    for q in c['f']:
        d = BeautifulSoup(f'<details><summary>{e(q[i])}{pm or ""}</summary><p class="ans">{e(q[2 + i])}</p></details>', 'html.parser')
        box.append(d)


def patch_graph(graph, base, lang):
    """One Person for Viktor on every page, tied to both of his services; the shop gets its 2GIS map."""
    pid = f'{base}/#viktor'
    used = False
    for n in graph:
        if n.get('@type') == 'Article' and n.get('author', {}).get('@type') == 'Person':
            n['author'] = {'@id': pid}
            n['dateModified'] = max(n.get('dateModified', ''), '2026-10-28')
            used = True
        if n.get('@type') == 'AutoRepair' and n.get('@id', '').endswith('#vibrotest'):
            n['founder'] = {'@id': pid}
            n['hasMap'] = 'https://2gis.kz/almaty/firm/70000001104923303'
            used = True
    if used:
        graph.append({'@type': 'Person', '@id': pid, 'name': 'Виктор Новиков',
                      'jobTitle': 'основатель VibroTest и Viton.kz' if lang == 'ru' else 'VibroTest және Viton.kz негізін қалаушы',
                      'worksFor': [{'@id': f'{base}/#vibrotest'}, {'@type': 'AutoRepair', 'name': 'Viton.kz', 'url': 'https://viton.kz/ru/'}],
                      'knowsAbout': ['диагностика ходовой', 'вибростенд', 'ремонт подвески', 'рулевое управление', 'чистка форсунок']})
    return graph


def merge_contacts(soup, phone):
    """Home: the «Ждём на Аносова» block goes; address, phone and hours sit in the footer, as on viton.kz."""
    book = soup.find(id='book')
    addr = book.find_next_sibling('section') if book else None
    if addr is not None and addr.find('a', href=re.compile(r'2gis\.kz/almaty/firm/')):
        addr.decompose()


def brand_chips(soup, lang, phone):
    """Home: the brand list as one compact block of chips, Chinese cars first; no year limit anywhere."""
    i = 0 if lang == 'ru' else 1
    for p in soup.find_all('p'):
        if '2010' in p.get_text():
            p.string = BRANDS['faq'][i]
    sec = next((p.find_parent('section') for p in soup.find_all('p') if 'Li Auto' in p.get_text()), None)
    if sec is None:
        return
    chip = lambda n, cn=False: f'<li{" class=\"cn\"" if cn else ""}>{html.escape(n)}</li>'
    sec.replace_with(BeautifulSoup(
        f'<section class="vt-brands" style="padding: {"8px 16px 40px" if phone else "0 0 110px"}"><div class="{"" if phone else "w"}">'
        f'<h2>{BRANDS["h"][i]}</h2><ul>' + ''.join(chip(n, True) for n in BRANDS['cn']) + ''.join(chip(n) for n in BRANDS['rest'])
        + f'<li class="more">{BRANDS["more"][i]}</li></ul><p>{BRANDS["no"][i]}</p></div></section>', 'html.parser'))

# ---------- the stand page: what you get, when not to drive, the questions competitors leave open ----------

ASOF = (' Цены на октябрь 2026.', ' Бағалар 2026 жылғы қазандағы жағдай бойынша.')
V = {
    'get_h': ('Что вы получите на руки', 'Қолыңызға не беріледі'),
    'get_p': ('Распечатанное заключение. Каждый проверенный узел в нём отмечен одним из трёх цветов: сразу видно, что чинить сейчас, а что подождёт.',
              'Басып шығарылған қорытынды. Тексерілген әр түйін үш түстің бірімен белгіленеді: нені қазір жөндеу керек, нені күтуге болатыны бірден көрінеді.'),
    'legend': ((('urgent', 'Срочно'), 'Люфт уже большой или узел влияет на управление. Лучше не откладывать.'),
               (('later', 'Можно позже'), 'Износ есть, но ездить можно. Следите и планируйте замену.'),
               (('ok', 'В норме'), 'Узел проверен и работает как надо.')),
    'legend_kk': ((('urgent', 'Шұғыл'), 'Саңылау үлкен немесе түйін басқаруға әсер етеді. Кейінге қалдырмаған дұрыс.'),
                  (('later', 'Кейінірек болады'), 'Тозу бар, бірақ жүруге болады. Бақылап, ауыстыруды жоспарлаңыз.'),
                  (('ok', 'Қалыпты'), 'Түйін тексерілді, дұрыс жұмыс істейді.')),
    'paper_h': ('Образец заключения', 'Қорытынды үлгісі'),
    'rows': ((('urgent', 'Стойка стабилизатора, передняя левая', 'люфт'), ('urgent', 'Стабилизатор тірегі, алдыңғы сол жақ', 'саңылау')),
             (('urgent', 'Рулевой наконечник, правый', 'люфт'), ('urgent', 'Рульдік ұштық, оң жақ', 'саңылау')),
             (('later', 'Сайлентблок заднего рычага, левый', 'трещины резины'), ('later', 'Артқы рычагтың сайлентблогы, сол жақ', 'резеңке жарылған')),
             (('later', 'Опора амортизатора, передняя правая', 'скрип'), ('later', 'Амортизатор тірегі, алдыңғы оң жақ', 'сықыр')),
             (('ok', 'Шаровые опоры', ''), ('ok', 'Шар тіректер', '')),
             (('ok', 'Рулевая рейка', ''), ('ok', 'Рульдік рейка', '')),
             (('ok', 'Ступичные подшипники', ''), ('ok', 'Күпшек мойынтіректері', ''))),
    'paper_cap': ('Образец: узлы и отметки условные. В вашем заключении будут узлы вашей машины.',
                  'Үлгі: түйіндер мен белгілер шартты. Сіздің қорытындыңызда өз көлігіңіздің түйіндері болады.'),
    'stop_h': ('Когда со стуком лучше не ехать', 'Тықылмен қашан жүрмеген дұрыс'),
    'stop_p': ('С такими признаками узел может отказать на ходу. Лучше вызвать эвакуатор, чем ехать своим ходом.',
               'Мұндай белгілермен түйін жолда істен шығуы мүмкін. Өз жүрісімен келгеннен гөрі эвакуатор шақырған дұрыс.'),
    'stop': (('Руль стал свободным или машина перестала держать прямую', 'Руль бос болып қалды немесе көлік түзу жүрмейді'),
             ('После удара колесо стоит криво, машину резко тянет в сторону', 'Соққыдан кейін дөңгелек қисық тұр, көлікті бір жаққа қатты тартады'),
             ('Громкий металлический стук в повороте, с каждым днём сильнее', 'Бұрылыста қатты металл тықылы, күн сайын күшейеді'),
             ('Гул или скрежет от колеса, диск после поездки сильно горячий', 'Дөңгелектен гуіл не қыжыр шығады, жүрістен кейін диск қатты ысиды'),
             ('Машина просела на один угол: могла лопнуть пружина', 'Көлік бір бұрышына отырып қалды: серіппе сынуы мүмкін')),
    'when_more': (('Весной, после зимних ям', 'Көктемде, қысқы шұңқырлардан кейін'),
                  ('Перед поездкой в горы, на Медеу или Шымбулак', 'Тауға, Медеу не Шымбұлаққа барар алдында')),
    'faq': ((('Стучит, а стенд ничего не нашёл. Так бывает?', 'Тықылдайды, бірақ стенд ештеңе таппады. Бола ма?'),
             ('Бывает, если звук появляется только на холодную, на определённой скорости или на одной кочке. Тогда мастер едет с вами на короткий тест-драйв по тому маршруту, где стучит.',
              'Болады, егер дыбыс тек суық күйде, белгілі бір жылдамдықта немесе бір ғана кедір-бұдырда шықса. Онда шебер сізбен бірге тықылдайтын жолмен қысқа тест-драйвқа шығады.')),
            (('Что написать при записи?', 'Жазылғанда не жазу керек?'),
             ('Марку и год машины, пробег и когда стучит: на кочках, в повороте, при торможении, на холодную. По марке и году скажем точную цену.',
              'Көліктің маркасы мен жылын, жүрісін және қашан тықылдайтынын: кедір-бұдырда, бұрылыста, тежегенде, суық күйде. Маркасы мен жылы бойынша нақты бағасын айтамыз.'))),
    'wa': ('Здравствуйте! Хочу на диагностику на вибростенде.\nМашина и год: \nПробег: \nКогда стучит: ',
           'Сәлеметсіз бе! Вибростендте диагностикаға жазылғым келеді.\nКөлік және жылы: \nЖүрісі: \nҚашан тықылдайды: '),
}

# the header and bottom-bar booking message: a short form, so the first reply can already name a price
WA_MSG = ('Здравствуйте! Хочу записаться в VibroTest на Аносова 91.\nМашина и год: \nЧто беспокоит: ',
          'Сәлеметсіз бе! Аносов 91-дегі VibroTest-ке жазылғым келеді.\nКөлік және жылы: \nНе мазалайды: ')
META = {
    'svc-vibrostand.dc.html': (
        ('Диагностика ходовой на вибростенде в Алматы — от 7 000 ₸, 25–40 минут',
         'Стенд раскачивает подвеску под нагрузкой, датчики шума показывают, какой узел стучит. 25–40 минут, заключение на руки. От 7 000 ₸. Алматы, Аносова 91.'),
        ('Алматыда вибростендте жүріс бөлігін диагностикалау — 7 000 ₸ бастап, 25–40 минут',
         'Стенд аспаны жүктеме астында тербетеді, шу датчиктері қай түйін тықылдайтынын көрсетеді. 25–40 минут, қорытынды қолға. 7 000 ₸ бастап. Алматы, Аносов 91.')),
}


def patch_ui(ui):
    ui['ru']['wa_msg'], ui['kk']['wa_msg'] = WA_MSG
    for lg in ('ru', 'kk'):
        ui[lg]['nav'] = [('contacts.dc.html', l) if b == 'Main.dc.html#contacts' else (b, l) for b, l in ui[lg]['nav']]


_PRICE_RU = {}


def price(board, lang, p):
    """The KK text has no «от N ₸», so the first «N ₸ бастап» can be a later row: take the RU page's starting price."""
    if lang == 'ru':
        _PRICE_RU[board] = p
        return p
    return _PRICE_RU.get(board, p)


def meta(board, lang, t, desc, price=None):
    m = META.get(board)
    if m:
        return m[0 if lang == 'ru' else 1]
    # service pages: the starting price in the title, the way the landing pages already show it
    if price and board.startswith(('svc-', 'l-')) and '₸' not in t and t.endswith(' — VibroTest'):
        n = f'{price:,}'.replace(',', ' ') + ' ₸'
        t = t[:-len(' — VibroTest')] + (f', от {n}' if lang == 'ru' else f', {n} бастап') + ' — VibroTest'
    return t, desc


def _faq_item(det, q, a):
    new = BeautifulSoup(str(det), 'html.parser').find('details')
    if new.has_attr('open'):
        del new['open']
    s = new.find('summary')
    svg = s.find('svg')
    s.clear()
    s.append(q)
    if svg:
        s.append(svg)
    new.find('p').string = a
    return new


def _sec_by_h2(soup, titles):
    for h in soup.find_all('h2'):
        if h.get_text(' ', strip=True) in titles:
            return h.find_parent('section')
    return None


ACT = {
    'title': ('Акт диагностики', 'Диагностика актісі'),
    'addr': ('Алматы, Аносова 91', 'Алматы, Аносов 91'),
    'meta': ((('Дата', 'Күні'), '27.10.2026'), (('Автомобиль', 'Көлік'), 'Toyota Camry 70'),
             (('Год выпуска', 'Шығарылған жылы'), '2021'), (('Пробег', 'Жүрісі'), ('45 800 км', '45 800 км'))),
    'sheet': ('Диагностический лист', 'Диагностикалық парақ'),
    'cols': (('№', '№'), ('Узел', 'Түйін'), ('Статус', 'Мәртебе'), ('Работа, ₸', 'Жұмыс, ₸')),
    'price': ('3 000', '3 000', '3 000', '10 000', '', '', ''),
    'total': ('Срочно, работа', 'Шұғыл, жұмыс'),
    'parts': ('Запчасти по накладной, цену называем до ремонта', 'Бөлшектер жүкқұжат бойынша, бағасын жөндеуге дейін айтамыз'),
    'sign': (('Мастер', 'Шебер'), ('Клиент', 'Клиент')),
}


def act_html(i, label):
    """The sample handed over after the stand, laid out like the shop's printed act, with the three urgency marks."""
    A = ACT
    meta = ''.join(f'<div><span>{k[i]}</span><b>{v if isinstance(v, str) else v[i]}</b></div>' for k, v in A['meta'])
    rows = ''.join(f'<tr><td class="num">{n}</td><td>{r[i][1]}{f"<em>, {r[i][2]}</em>" if r[i][2] else ""}</td>'
                   f'<td><span class="ft-st {r[i][0]}">{label[r[i][0]]}</span></td><td class="num">{A["price"][n - 1] or "—"}</td></tr>'
                   for n, r in enumerate(V['rows'], 1))
    head = ''.join(f'<th>{c[i]}</th>' for c in A['cols'])
    sign = ''.join(f'<div><span>{s[i]}</span><i></i></div>' for s in A['sign'])
    return (f'<figure class="vt-act"><div class="act-top"><img src="/img/logo-ink.png" alt="VibroTest.kz" width="142" height="40" loading="lazy">'
            f'<span>{A["addr"][i]}<br><span class="num">+7 747 495 61 65</span></span></div>'
            f'<h3>{A["title"][i]}</h3><div class="act-meta">{meta}</div>'
            f'<div class="act-band">{A["sheet"][i]}</div>'
            f'<div class="act-tw"><table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody>'
            f'<tfoot><tr><td colspan="3">{A["total"][i]}</td><td class="num">6 000</td></tr></tfoot></table></div>'
            f'<p class="act-parts">{A["parts"][i]}</p><div class="act-sign">{sign}</div>'
            f'<figcaption>{V["paper_cap"][i]}</figcaption></figure>')


CASE = {
    'board': 'art-lixiang-l7.dc.html',
    'eyebrow': ('Из наших работ', 'Біздің жұмыстардан'),
    'h': ('LiXiang L7: стенд нашёл износ в четырёх местах', 'LiXiang L7: стенд төрт жерден тозу тапты'),
    'p': ('Верхние и нижние рычаги, рулевая рейка, тяги и наконечники. Рейку отреставрировали, остальное заменили. Контрольный прогон на стенде после ремонта: стуков нет.',
          'Жоғарғы және төменгі рычагтар, рульдік рейка, тартқыштар мен ұштықтар. Рейка қалпына келтірілді, қалғаны ауыстырылды. Жөндеуден кейін стендте бақылау тексеруі: тықыл жоқ.'),
    'pics': (('lixiang-l7-osmotr', ('Подвеска LiXiang L7 снизу до ремонта', 'LiXiang L7 аспасы жөндеуге дейін астынан')),
             ('lixiang-l7-hero', ('Рулевая рейка LiXiang L7 на верстаке во время реставрации', 'LiXiang L7 рульдік рейкасы қалпына келтіру кезінде үстелде')),
             ('lixiang-l7-rychagi', ('Старые и новые рычаги LiXiang L7', 'LiXiang L7 ескі және жаңа рычагтары'))),
    'link': ('Смотреть кейс с видео', 'Видеосы бар кейсті қарау'),
}


def case_block(lang, url_for, phone=False, small=False):
    """A real job from the shop, with its own frames: on the home page and on the pages for the parts it touched."""
    i = 0 if lang == 'ru' else 1
    pics = CASE['pics'] if not small else CASE['pics'][1:]
    imgs = ''.join(f'<img src="/media/{f}.jpg" alt="{a[i]}" loading="lazy">' for f, a in pics)
    pad = '40px 16px 0' if phone else 'clamp(54px, 8.33vw, 120px) 0 0'
    return (f'<section class="vt-case{" sm" if small else ""}" style="padding: {pad}"><div class="{"" if phone else "w"}">'
            f'<div class="vc-in"><div class="vc-tx"><span class="vc-eb">{CASE["eyebrow"][i]}</span>'
            f'<h2 class="hd">{CASE["h"][i]}</h2><p>{CASE["p"][i]}</p>'
            f'<a class="lnk" href="{url_for(lang, CASE["board"])}">{CASE["link"][i]}</a></div>'
            f'<div class="vc-pics">{imgs}</div></div></div></section>')


CASE_PAGES = ('svc-steering-rack.dc.html', 'l-rychagi.dc.html', 'l-tyagi.dc.html', 'svc-suspension.dc.html')


def vibro_page(soup, lang, phone):
    from urllib.parse import quote
    i = 0 if lang == 'ru' else 1
    legend = V['legend'] if i == 0 else V['legend_kk']
    leg = ''.join(f'<li><span class="ft-st {k}">{n}</span><span>{x}</span></li>' for (k, n), x in legend)
    label = {k: n for (k, n), _ in legend}
    rows = ''.join(f'<li class="ft-row"><span class="ft-st {r[i][0]}">{label[r[i][0]]}</span>'
                   f'<span>{r[i][1]}{f"<em>, {r[i][2]}</em>" if r[i][2] else ""}</span></li>' for r in V['rows'])
    paper = act_html(i, label)
    stop = ''.join(f'<li>{x[i]}</li>' for x in V['stop'])
    if phone:
        get = (f'<section class="sec"><h2 class="hd h2">{V["get_h"][i]}</h2><p class="vt-p">{V["get_p"][i]}</p>'
               f'<ul class="vt-legend">{leg}</ul>{paper}</section>')
        stop_sec = (f'<section class="sec"><h2 class="hd h2">{V["stop_h"][i]}</h2><p class="vt-p">{V["stop_p"][i]}</p>'
                    f'<ul class="vt-stop">{stop}</ul></section>')
    else:
        get = (f'<section style="padding: clamp(54px, 8.33vw, 120px) 0 0"><div class="w g2" style="gap: clamp(36px, 5.56vw, 80px); align-items: start">'
               f'<div style="display: flex; flex-direction: column; gap: 22px"><h2 class="hd" style="font-size: clamp(25px, 3.44vw, 44px); line-height: 1.06; font-weight: 800">{V["get_h"][i]}</h2>'
               f'<p style="color: #A9B4C2; font-size: 17px; line-height: 1.65">{V["get_p"][i]}</p><ul class="vt-legend">{leg}</ul></div>{paper}</div></section>')
        stop_sec = (f'<section style="padding: clamp(54px, 8.33vw, 120px) 0 0"><div class="w g2" style="gap: clamp(36px, 5.56vw, 80px); align-items: start">'
                    f'<div style="display: flex; flex-direction: column; gap: 22px"><h2 class="hd" style="font-size: clamp(25px, 3.44vw, 44px); line-height: 1.06; font-weight: 800">{V["stop_h"][i]}</h2>'
                    f'<p style="color: #A9B4C2; font-size: 17px; line-height: 1.65">{V["stop_p"][i]}</p></div><ul class="vt-stop">{stop}</ul></div></section>')
    how = _sec_by_h2(soup, {_KK.get(x, x) if i else x for x in ('Как проходит диагностика', 'Как проходит')})
    if how:
        how.insert_after(BeautifulSoup(get, 'html.parser'))
    when = _sec_by_h2(soup, {_KK.get(x, x) if i else x for x in ('Когда стоит приехать', 'Когда приехать')})
    if when:
        lis = when.find_all('li')
        if lis:
            for x in V['when_more']:
                li = BeautifulSoup(str(lis[-1]), 'html.parser').find('li')
                li.string = x[i]
                when.find('ul').append(li)
        when.insert_after(BeautifulSoup(stop_sec, 'html.parser'))
    dets = [d for d in soup.find_all('details') if 'km-it' not in (d.get('class') or [])]
    if dets:
        for q, a in V['faq']:
            dets[-1].parent.append(_faq_item(dets[-1], q[i], a[i]))
    price = _sec_by_h2(soup, {_KK.get(x, x) if i else x for x in ('Цены на диагностику', 'Цены')})
    if price:
        p = price.find('p')
        if p:
            p.append(ASOF[i])
    for a in soup.find_all('a', href=re.compile(r'^https://wa\.me/')):
        a['href'] = a['href'].split('?')[0] + '?text=' + quote(V['wa'][i], safe='')


# ---------- every page in one navy tone: the light price panels go dark too ----------

PRICE_DARK = [(r'solid #0B1220', 'solid rgba(255,255,255,.16)'), (r'#0B1220', '#EEF2F7'), (r'#4A5565', '#A9B4C2'),
              (r'#5B6575', '#8A96A6'), (r'rgba\(11,\s*18,\s*32,\s*\.(\d+)\)', r'rgba(255,255,255,.\1)')]


def one_tone(soup, lang):
    for s in soup.find_all(string=re.compile(r'\s·\s')):
        if s.parent.name not in ('script', 'style'):
            s.replace_with(re.sub(r'\s·\s', ', ', s))
    for sec in soup.find_all('section', style=re.compile(r'background:\s*#F3F5F8', re.I)):
        st = re.sub(r'(?:^|;)\s*(?:background|color|margin-top)\s*:[^;]*', '', sec['style'])
        sec['style'] = st.strip('; ')
        sec['class'] = (sec.get('class') or []) + ['prdk']
        for el in sec.find_all(style=True):
            s = el['style']
            for a, b in PRICE_DARK:
                s = re.sub(a, b, s, flags=re.I)
            el['style'] = s
        p = sec.find('p')
        if p and 'prow' in str(sec) and ASOF[0].strip() not in p.get_text() and ASOF[1].strip() not in p.get_text():
            p.append(ASOF[0 if lang == 'ru' else 1])


VT_CSS = """
.psub{color:#8792A3!important}
.mh-r .st,.dh-tel .st{display:none!important}
.ft-arts{margin-top:28px;padding-top:24px;border-top:1px solid rgba(255,255,255,.06)}
.ft-arts>div{margin-top:10px;columns:3;column-gap:40px}.ft-arts a{display:block;break-inside:avoid;padding:4px 0;font-size:14px;color:#A9B4C2}.ft-arts a:hover{color:#EEF2F7}
@media (max-width:899px){.ft-arts,.ft-ct,.ft-bot{display:none!important}}
.ftm{display:none}
@media (max-width:899px){.ftm{display:block;margin-top:14px}.ft-top nav{display:none!important}
.fm-tag{margin:0 0 22px!important;font-size:14px;line-height:1.5;color:#A9B4C2}
.fm-ct{display:grid!important;gap:4px;padding:0 0 22px!important;margin:0!important;font-size:15px;color:#EEF2F7}
.fm-ct .fc-h{margin-bottom:4px}.fm-tel{font-size:19px;font-weight:700;color:#fff!important;text-decoration:none}
.fm-g{border-top:1px solid rgba(255,255,255,.08);margin:0!important}.fm-g:last-of-type{border-bottom:1px solid rgba(255,255,255,.08)}
.fm-g summary{display:flex!important;align-items:center;justify-content:space-between;padding:17px 0!important;font-size:16px;font-weight:600;color:#EEF2F7;cursor:pointer;list-style:none}
.fm-g summary::-webkit-details-marker{display:none}
.fm-g summary i{position:relative;width:14px;height:14px;flex:none}
.fm-g summary i:before,.fm-g summary i:after{content:"";position:absolute;left:0;top:6px;width:14px;height:2px;border-radius:1px;background:#A9B4C2;transition:transform .2s}
.fm-g summary i:after{transform:rotate(90deg)}.fm-g[open] summary i:after{transform:rotate(0)}
.fm-g>div{display:grid!important;gap:2px;padding:0 0 16px!important}
.fm-g>div a{display:block;padding:7px 0;font-size:15px;line-height:1.4;color:#A9B4C2;text-decoration:none}
.fm-bot{display:grid!important;gap:6px;padding:22px 0 0!important;font-size:13px;color:#7E8A9A}.fm-bot a{color:#A9B4C2}}
.toc{margin:8px 0 4px!important;padding:20px 24px;border-radius:14px;border:1px solid rgba(255,255,255,.08);background:#0F1829}
.toc b{display:block;font-size:15px;margin-bottom:8px;color:#EEF2F7}.toc ol{margin:0!important;padding-left:20px!important;display:flex;flex-direction:column;gap:6px}
.toc a{color:#5AAEF2;font-size:15px}
.readmore{margin-top:36px}.readmore h2{margin-top:0}.readmore ul,.artlist{list-style:none!important;padding:0!important;margin:16px 0 0!important;display:flex;flex-direction:column;border-top:1px solid rgba(255,255,255,.1)}
.readmore li,.artlist li{margin:0!important;padding:0!important;border-bottom:1px solid rgba(255,255,255,.1)}.readmore a,.artlist a{display:block;padding:14px 0;color:#EEF2F7!important;font-weight:600;font-size:16px}
.readmore a:hover,.artlist a:hover{color:#5AAEF2!important}
.vt-x h2{font:800 clamp(26px,2.6vw,36px)/1.1 'Geologica',system-ui,sans-serif;margin:0}
.nohelp{margin:18px 0 0!important;padding:0!important;list-style:none!important;display:flex;flex-direction:column;gap:10px;color:#A9B4C2;font-size:16px;line-height:1.6;max-width:820px}
.nohelp li{position:relative;padding-left:22px}.nohelp li::before{content:'';position:absolute;left:4px;top:.65em;width:7px;height:7px;border-radius:50%;background:#5AAEF2}
.doit{margin:16px 0 0!important;padding:0 0 0 22px!important;display:flex;flex-direction:column;gap:10px}.doit li{margin:0!important;padding-left:4px;line-height:1.6}.doit li::marker{color:#5AAEF2;font-weight:700}
.svx p{max-width:820px;color:#A9B4C2;font-size:17px;line-height:1.65}.svx h2+p{margin-top:20px!important}
.svx-t{width:100%;max-width:960px;margin:24px 0 0!important;border-collapse:collapse;font-size:16px;line-height:1.55}
.svx-t th{text-align:left;font-size:13px;font-weight:500;color:#8792A3;padding:0 16px 10px 0;border-bottom:1px solid rgba(255,255,255,.12)}
.svx-t td{padding:14px 16px 14px 0;border-bottom:1px solid rgba(255,255,255,.08);vertical-align:top;color:#A9B4C2}.svx-t td:first-child{color:#EEF2F7;font-weight:600;width:34%}
@media (max-width:899px){.svx{padding:44px 0 0!important}.svx-end{padding-bottom:44px!important}.svx-t thead{display:none}.svx-t tr,.svx-t td{display:block;width:auto!important}.svx-t td{border:0;padding:0 0 4px}.svx-t tr{padding:14px 0;border-bottom:1px solid rgba(255,255,255,.08)}}
.vt-x p{margin:16px 0 0!important}.vt-x p a{color:#5AAEF2;font-weight:600}
@media (max-width:899px){.vt-x{padding:0 16px 48px!important}.toc{padding:16px 18px}}
.ft-ct{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px 40px;margin-top:32px;padding-top:28px;border-top:1px solid rgba(255,255,255,.06);scroll-margin-top:100px}
.fc-col{display:flex;flex-direction:column;gap:6px;font-size:15px;color:#D5DCE5;line-height:1.5}
.fc-h{font-size:13px;color:#8792A3;margin-bottom:2px}.fc-m{font-size:14px;color:#8792A3}
.fc-col a{color:#5AAEF2;font-weight:600;font-size:15px}.fc-col a.fc-tel{color:#EEF2F7;font-size:18px}
@media (max-width:899px){.ft-ct{grid-template-columns:minmax(0,1fr);gap:22px}}
.km-m .km-hd{margin-bottom:16px}
.km-m .km-fig{padding:10px 6px 4px}.km-m .km-dots{inset:10px 6px 4px}
.km-rail{display:flex;gap:10px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-padding:0 16px;padding:14px 16px 4px;scrollbar-width:none}
.km-rail::-webkit-scrollbar{display:none}
.km-rw{position:relative}.km-rw::after{content:'';position:absolute;top:14px;right:0;bottom:4px;width:36px;background:linear-gradient(90deg,rgba(11,18,32,0),#0B1220);pointer-events:none;transition:opacity .2s}.km-rw.at-end::after{opacity:0}
.km-rd{justify-content:center;margin:12px 0 0!important}
.km-cd{flex:0 0 68%;scroll-snap-align:start;display:flex;flex-direction:column;align-items:flex-start;gap:6px;text-align:left;padding:16px;border-radius:14px;background:#131E33;border:1px solid rgba(255,255,255,.08);color:#EEF2F7;font-family:inherit;cursor:pointer;min-height:112px}
.km-cd b{font-size:16px;font-weight:600;line-height:1.25}.km-cd span{font-size:13.5px;line-height:1.45;color:#8792A3}
.km-cd[aria-expanded=true]{border-color:#0071BC;background:#0F2A4A}.km-cd[aria-expanded=true] b{color:#5AAEF2}
.km-pn{margin-top:12px;padding:16px;border-radius:14px;background:#131E33;border:1px solid rgba(0,113,188,.5);display:flex;flex-direction:column;gap:8px}
.km-pn[hidden]{display:none}
.km-pn-h{display:flex;justify-content:space-between;align-items:center;gap:12px}.km-pn-h b{font-size:17px}
.km-x{width:32px;height:32px;border:0;border-radius:50%;background:rgba(255,255,255,.08);position:relative;cursor:pointer;flex:none}
.km-x::before,.km-x::after{content:'';position:absolute;left:50%;top:50%;width:13px;height:2px;background:#A9B4C2;transform:translate(-50%,-50%) rotate(45deg)}.km-x::after{transform:translate(-50%,-50%) rotate(-45deg)}
.km-pn>a{display:flex;align-items:center;min-height:44px;margin-top:2px;border:1px solid rgba(255,255,255,.06);padding:0 14px;border-radius:10px;background:#0B1424;color:#EEF2F7!important;font-weight:600;font-size:15px}
.km-pb{display:flex;align-items:center;justify-content:space-between;gap:12px;margin-top:4px}.km-pb .km-price{font-size:20px}.km-pb .btn{width:auto!important;min-height:44px}
.km-m .km-unsure{display:block;margin-top:14px}.km-m .km-all{margin-top:16px}
.vt-brands h2{font:800 clamp(24px,2.4vw,32px)/1.15 'Geologica',system-ui,sans-serif;letter-spacing:-.01em;margin:0;max-width:760px}
.vt-brands ul{list-style:none;margin:22px 0 0!important;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.vt-brands li{padding:7px 14px;border-radius:999px;border:1px solid rgba(255,255,255,.12);font-size:15px;font-weight:500;color:#D5DCE5;white-space:nowrap}
.vt-brands li.cn{border-color:rgba(90,174,242,.45);color:#EEF2F7;background:rgba(0,113,188,.12)}
.vt-brands li.more{border-style:dashed;color:#8792A3}
.vt-brands p{margin:16px 0 0!important;font-size:14px;color:#8792A3}
@media (max-width:899px){.vt-brands h2{font-size:22px}.vt-brands ul{margin-top:16px!important;gap:6px}.vt-brands li{padding:6px 11px;font-size:13.5px}}
.prow .plink{color:#EEF2F7!important;border-bottom-color:rgba(238,242,247,.25)}
.prow-go{grid-template-columns:minmax(0,1fr) auto!important}
.pgo{display:inline-flex;align-items:center;gap:2px;font-size:15px;font-weight:600;color:#5AAEF2!important;white-space:nowrap;text-decoration:none}.pgo:hover{color:#8CC8FF!important}
@media (max-width:899px){.bb{position:fixed;left:0;right:0}footer,.ft{padding-bottom:110px!important}}
.topbar{background:#080E1A;border-bottom:1px solid rgba(255,255,255,.06);font-size:13px;color:#A9B4C2}
.tb-in{max-width:1280px;margin:0 auto;padding:7px 48px;display:flex;gap:24px}
@media (max-width:899px){.tb-in{padding:6px 16px;justify-content:space-between;gap:12px;font-size:12px}}
.vt-legend{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:max-content minmax(0,1fr);gap:12px 14px;align-items:baseline;font-size:15px;line-height:1.55;color:#A9B4C2}
.vt-legend li{display:contents}.vt-legend .ft-st,.vt-paper .ft-st{white-space:nowrap}
.vt-case .vc-in{display:grid;grid-template-columns:minmax(0,5fr) minmax(0,7fr);gap:clamp(28px,4vw,56px);align-items:center;padding:clamp(22px,3vw,40px);border-radius:20px;background:#11161E;border:1px solid rgba(255,255,255,.08)}
.vc-tx{display:flex;flex-direction:column;gap:14px}.vc-eb{font-size:13px;font-weight:600;color:#5AAEF2}
.vt-case h2{font-size:clamp(24px,2.6vw,36px);line-height:1.1;font-weight:800;margin:0;color:#FFFFFF}
.vt-case p{margin:0;font-size:16px;line-height:1.6;color:#A9B4C2}.vt-case .lnk{font-weight:600;font-size:15px}
.vc-pics{display:grid;grid-template-columns:1fr 1.6fr 1fr;gap:10px}.vt-case.sm .vc-pics{grid-template-columns:1.6fr 1fr}
.vc-pics img{width:100%;height:300px;object-fit:cover;border-radius:12px;display:block;background:#0A0D12}
@media (max-width:899px){.vt-case .vc-in{grid-template-columns:minmax(0,1fr)}.vc-pics img{height:200px}}
.vt-act{margin:0;background:#FFFFFF;color:#111827;border-radius:6px;padding:28px 28px 22px;box-shadow:0 18px 50px rgba(0,0,0,.35);font-size:14px}
.act-top{display:flex;justify-content:space-between;align-items:center;gap:16px;padding-bottom:14px;border-bottom:2px solid #111827}
.act-top img{height:34px;width:auto;display:block}.act-top>span{text-align:right;font-size:12px;line-height:1.5;color:#374151}
.vt-act h3{font:700 19px 'Geologica',system-ui,sans-serif;text-align:center;margin:16px 0 12px;color:#111827}
.act-meta{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));border:1px solid #111827;border-bottom:0}
.act-meta div{display:flex;justify-content:space-between;gap:8px;padding:6px 10px;border-bottom:1px solid #111827;font-size:13px}
.act-meta div:nth-child(odd){border-right:1px solid #111827}.act-meta span{color:#4B5563}.act-meta b{font-weight:600}
.act-band{margin-top:14px;padding:6px 10px;border:1px solid #111827;border-bottom:0;background:#EEF1F4;text-align:center;font-weight:700;font-size:13px}
.act-tw{overflow-x:auto}.vt-act table{width:100%;border-collapse:collapse;font-size:13px;min-width:420px}
.vt-act th,.vt-act td{border:1px solid #111827;padding:6px 8px;text-align:left;vertical-align:middle}
.vt-act th{font-weight:600;background:#F8F9FA}.vt-act td:first-child,.vt-act th:first-child{width:30px;text-align:center}
.vt-act td:last-child,.vt-act th:last-child{text-align:right;white-space:nowrap}
.vt-act em{font-style:normal;color:#6B7280}.vt-act .ft-st{min-width:0;padding:2px 9px;font-size:12px;white-space:nowrap}
.vt-act tfoot td{font-weight:700;text-align:right}
.act-parts{margin:10px 0 0;font-size:12.5px;color:#4B5563}
.act-sign{display:grid;grid-template-columns:1fr 1fr;gap:24px;margin-top:22px}
.act-sign div{display:flex;align-items:flex-end;gap:8px;font-size:12.5px;color:#4B5563}.act-sign i{flex:1;border-bottom:1px solid #111827;height:14px}
.vt-act figcaption{margin-top:16px;padding-top:10px;border-top:1px dashed #C9CFD6;font-size:12px;color:#6B7280}
.mv .vt-act{padding:18px 12px 16px}.mv .vt-act table{min-width:0;font-size:12.5px}.mv .vt-act th,.mv .vt-act td{padding:5px 5px}.mv .vt-act .ft-st{font-size:11px;padding:2px 6px;white-space:normal;text-align:center;display:inline-block;line-height:1.25}.mv .vt-act td:first-child,.mv .vt-act th:first-child{width:22px}.mv .act-meta{grid-template-columns:minmax(0,1fr)}.mv .act-meta div:nth-child(odd){border-right:0}
.vt-paper{padding:28px 30px}.vt-paper .ft-row{font-size:15px}.vt-paper em{font-style:normal;color:#5B6576}
.vt-stop{list-style:none;margin:0;padding:0;border-top:1px solid rgba(255,255,255,.1)}
.vt-stop li{position:relative;padding:20px 0 20px 28px;border-bottom:1px solid rgba(255,255,255,.1);font-size:17px;line-height:1.5;color:#D5DCE5}
.vt-stop li::before{content:'';position:absolute;left:3px;top:28px;width:9px;height:9px;border-radius:50%;background:#F26B6B}
.prdk .prow{color:#EEF2F7!important;border-bottom-color:rgba(255,255,255,.1)!important}
.mv .vt-p{margin-top:10px;font-size:15px;line-height:1.6;color:#A9B4C2}
.mv .vt-legend{margin:16px 0 18px;font-size:14px}
.mv .vt-paper{padding:16px}.mv .vt-paper .ft-row{font-size:14px;align-items:flex-start}
.mv .vt-stop{margin-top:14px}.mv .vt-stop li{font-size:15px;padding:14px 0 14px 24px}.mv .vt-stop li::before{top:21px}
"""
CSS += VT_CSS


def insert_map(soup, name, lang, url_for, wa):
    """Home: replaces the «Что беспокоит?» picker (one tool, not two). Services: right after the hero."""
    if any(x[0] == name for x in ALL_ARTS):
        article_extras(soup, name, lang, url_for, wa)
    elif name.startswith(('svc-', 'l-')) or name == 'Mobile-service.dc.html':
        service_extras(soup, 'svc-vibrostand.dc.html' if name == 'Mobile-service.dc.html' else name, lang, url_for)
    # the address block sits right above the booking form: its own «Записаться» button only repeats the form
    if soup.find('form', attrs={'data-book': True}):
        for route in soup.find_all('a', href=re.compile(r'2gis\.kz/almaty/firm/')):
            for b in route.parent.find_all('a', class_='btn', recursive=False):
                b.decompose()
    if name not in ('Main.dc.html', 'Mobile.dc.html'):
        if name in ('svc-vibrostand.dc.html', 'Mobile-service.dc.html'):
            vibro_page(soup, lang, name == 'Mobile-service.dc.html')
        if name == 'Blog.dc.html':
            blog_cards(soup, lang, url_for)
        if name in CASE_PAGES:
            faq = _sec_by_h2(soup, {'Частые вопросы', 'Жиі қойылатын сұрақтар', 'Вопросы и ответы', _KK.get('Вопросы и ответы', '')})
            blk = BeautifulSoup(case_block(lang, url_for, small=True), 'html.parser')
            if faq:
                faq.insert_before(blk)
            else:
                secs = soup.find_all('section')
                (secs[-1].insert_before if len(secs) > 1 else secs[0].insert_after)(blk)
        if name == 'Services.dc.html':
            services_list(soup, lang)
        one_tone(soup, lang)
    anchor = None
    if name in ('Main.dc.html', 'Mobile.dc.html'):
        chip = soup.find('button', class_='chip')
        anchor = chip.find_parent('section') if chip else None
    if anchor is None:
        return
    home = name in ('Main.dc.html', 'Mobile.dc.html')
    phone = name == 'Mobile.dc.html'
    to_dots(soup)
    if home:
        brand_chips(soup, lang, phone)
        merge_contacts(soup, phone)
    new = BeautifulSoup(knock_map(lang, url_for, wa, name == 'Mobile.dc.html', 'symptom' if name == 'Main.dc.html' else '', prices=not home), 'html.parser')
    if home:
        anchor.extract()
        i = 0 if lang == 'ru' else 1
        # one block tells the stand story: the facts strip under the hero and «Как проходит диагностика» repeat it
        facts = soup.find('div', class_='facts')
        if facts and facts.find_parent('div', class_='w'):
            facts.find_parent('div', class_='w').decompose()
        diag = soup.find('section', id='diag')
        if diag:
            diag.decompose()
        for h in soup.find_all('h2'):
            if h.get_text(' ', strip=True) in DIAG_H2:
                h.find_parent('section').decompose()
                break
        hero = soup.find('section')
        hero.insert_after(BeautifulSoup(stand_feature(lang, url_for, wa, phone), 'html.parser'))
        # the other services come after the stand story: desktop after the paper sample, phone right after the stand
        after = None
        for h in soup.find_all('h2'):
            if h.get_text(' ', strip=True) in STORY_END:
                after = h.find_parent('section')
                break
        (after or soup.find('section', class_='ft-sec')).insert_after(new)
        # «С чем приезжают» lists the same services: the map covers it now
        for h in soup.find_all('h2'):
            if h.get_text(' ', strip=True) in SERVICES_H2:
                h.find_parent('section').decompose()
                break
        # plainer headings, one name for the booking button
        for ru, pair in RETITLE.items():
            for t in soup.find_all(string=lambda x: x and x.strip() in (ru, _KK.get(ru, ru))):
                t.replace_with(t.replace(t.strip(), pair[i]))
        if phone:
            # the price question, answered with a link: prices live on the services page
            faq = next((d for d in soup.find_all('details') if 'km-it' not in (d.get('class') or [])), None)
            if faq:
                q, a, link = PRICE_FAQ[i]
                faq.parent.append(BeautifulSoup(
                    f'<details><summary>{q}<svg class="pm" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" aria-hidden="true"><path d="M12 5v14M5 12h14"></path></svg></summary>'
                    f'<p style="padding: 0 0 18px; font-size: 15px; line-height: 1.6; color: #A9B4C2">{a} <a href="{url_for(lang, "Services.dc.html")}">«{link}»</a>.</p></details>', 'html.parser'))
            # small text up to 13px, and standalone links get a finger-sized hit area
            for el in soup.find_all(style=re.compile(r'font-size:\s*12px')):
                el['style'] = re.sub(r'font-size:\s*12px', 'font-size: 13px', el['style'])
            for a in soup.find_all('a'):
                cls = a.get('class') or []
                if set(cls) - {'lnk', 'num'} or a.find_parent(class_=['km-links', 'bb', 'mh']):
                    continue
                if a.get('href', '').startswith('tel:') or not a.parent.find(string=lambda x: x.strip() and x.parent is a.parent, recursive=False):
                    a['class'] = cls + ['tap']
        theme_home(soup, phone)
    else:
        anchor.insert_after(new)
        if name == 'Services.dc.html':
            i = 0 if lang == 'ru' else 1
            for x in soup.select('.km-price'):
                x.decompose()
            for t in soup.find_all(string=T2['sub'][i]):
                t.replace_with(T2['sub_home'][i])


# ---------- home: light paper between the dark moments (hero, the car map, the booking form) ----------

DARK2LIGHT = [
    (r'#(?:EEF2F7|FFFFFF|D5DCE5|E3E8EE)\b', '#0F1722'), (r'#(?:A9B4C2|B4BECB)\b', '#4A5566'), (r'#(?:8A96A6|6F7B8B)\b', '#5B6676'),
    (r'#3A4556\b', '#C3CBD5'), (r'#(?:11161E|151B24)\b', 'var(--well)'), (r'#(?:0E131A|0A0D12)\b', 'var(--paper)'),
    (r'#5AAEF2\b', '#0071BC'), (r'#FF9EA1\b', '#B4232A'), (r'rgba\(255,\s*255,\s*255,\s*\.(\d+)\)', r'rgba(15,23,34,.\1)'),
]


# the dark surfaces in navy, like the neighbour's site, instead of near-black
NAVY = [(r'#0A0D12\b', '#0B1220'), (r'#0E131A\b', '#0F1829'), (r'#11161E\b', '#131E33'), (r'#151B24\b', '#17233A'),
        (r'#141B25\b', '#17233A'), (r'#0E1520\b', '#101B30'), (r'#0B1018\b', '#0B1424'), (r'rgba\(10,\s*13,\s*18,', 'rgba(11,18,32,'), (r'#6F7B8B\b', '#7F8A9B')]


def lighten(sec, paper):
    """Recolour a dark-board section for light paper: inline colours swap to their light pair, classes get .lt rules."""
    sec['class'] = (sec.get('class') or []) + ['lt', 'lt-' + paper]
    for el in [sec] + sec.find_all(style=True):
        st = el.get('style')
        if not st:
            continue
        for a, b in DARK2LIGHT:
            st = re.sub(a, b, st, flags=re.I)
        el['style'] = st
    for el in sec.find_all(['path', 'svg', 'circle', 'rect', 'line', 'polyline']):
        for k in ('stroke', 'fill'):
            v = el.get(k)
            if v and v.lower() in ('#6f7b8b', '#8a96a6', '#3a4556'):
                el[k] = '#8C97A6'


def theme_home(soup, phone):
    """One tone for the whole page: every section sits on the same navy, no panels of a second shade.
    (The light-paper variant, lighten() and LIGHT_CSS, stays available but is not used.)"""
    for sec in [x for x in soup.find_all('section') if x.find_parent('section') is None][1:]:
        st = sec.get('style', '')
        st = re.sub(r';?\s*(background|border-top|border-bottom)\s*:[^;]*', '', st)
        sec['style'] = st.strip('; ')
    # template punctuation and mono costume
    for t in soup.find_all(string=re.compile(r'\s·\s')):
        if t.parent.name not in ('script', 'style'):
            t.replace_with(re.sub(r'\s·\s', ', ', t))
    for t in soup.find_all(string=lambda x: x and x.strip() == '·'):
        el = t.parent if t.parent.name == 'span' and t.parent.get_text(strip=True) == '·' else t
        prev = el.previous_sibling
        if isinstance(prev, str):
            prev.replace_with(prev.rstrip())
        el.replace_with(',')
    for el in soup.find_all(class_='num'):
        el['class'] = [c for c in el['class'] if c != 'num'] + ['fig']


LIGHT_CSS = """
.lt{--paper:#FFFFFF;--well:#F1F4F7;background:var(--paper)!important;color:#0F1722;border:0!important}
.lt-grey{--paper:#F2F4F7;--well:#FFFFFF}
.lt a:not(.btn){color:inherit}.lt p a,.lt a.tap,.lt .km-unsure a{color:#0067AC}.lt a.tap{text-decoration:underline;text-underline-offset:4px;text-decoration-thickness:1px}
.lt .lnk{color:#0F1722!important;border-bottom-color:rgba(15,23,34,.3)!important}
.lt .card,.lt details{border-color:rgba(15,23,34,.1)!important}
.lt summary{color:#0F1722}
.lt .ft-main>p,.lt .ft-steps span{color:#4A5566}.lt .ft-steps b{color:#0F1722}.lt .ft-steps,.lt .ft-steps li{border-color:rgba(15,23,34,.12)}
.lt .ft-steps li::before{color:#0071BC}
.lt .ft-get{background:#F1F4F7}.lt .ft-row{border-color:#DDE3EA}
.lt .brands{color:#0F1722;font-weight:500}.lt .brands-h{color:#5B6676}
.lt .btn-d{background:#0F1722;color:#FFFFFF}
.lt .btn-p,.lt .btn-p:hover,.lt .btn-d,.lt .btn-d:hover{color:#FFFFFF!important}
.lt .stack>*{background:var(--well)!important;border:0!important}
.fig{font-family:'Geologica',system-ui,sans-serif;font-variant-numeric:tabular-nums;letter-spacing:-.01em}
::selection{background:#0071BC;color:#FFFFFF}
.num{font-family:'Geologica',system-ui,sans-serif!important;letter-spacing:0!important}
a[href^="tel:"]{white-space:nowrap}
@media (max-width:899px){.km-side{align-items:flex-start}.mv .brands{margin-top:16px!important}.mv .brands-h{margin:20px 0 -8px!important}.mv section.lt{padding-bottom:48px!important}}
.lang{color:#6F7B8B}
"""
CSS += LIGHT_CSS


def light_css(css):
    """The boards colour some text through class rules (FAQ, row lists, labels): give each such rule a light twin under .lt."""
    out = []
    for sel, body in re.findall(r'([^{}@]+)\{([^{}]*)\}', css):
        decls = []
        for d in body.split(';'):
            if ':' not in d:
                continue
            k, v = d.split(':', 1)
            if k.strip() not in ('color', 'background', 'background-color', 'border-color', 'border', 'border-top', 'border-bottom'):
                continue
            nv = v
            for a, b in DARK2LIGHT:
                nv = re.sub(a, b, nv, flags=re.I)
            if nv != v:
                decls.append(f'{k.strip()}:{nv.strip()}!important')
        if decls:
            sels = []
            for one in sel.split(','):
                one = one.strip()
                if not one or re.fullmatch(r'(\.(?:dv|mv)\s+)?a(:hover)?', one) or re.search(r'btn|chip|bwhen|mapf|pbook|hbtn|mbtn', one) or one.startswith(('.lt', ':root', 'html', 'body', '.bb', '.mh', '.dh', '.menu', '.ft ', '.ft{', '.ft-')):
                    continue
                m = re.match(r'(\.(?:dv|mv))\s+(.*)', one)
                sels.append(f'{m.group(1)} .lt {m.group(2)}' if m else f'.lt {one}')
            if sels:
                out.append(','.join(sels) + '{' + ';'.join(decls) + '}')
    return '\n'.join(out)


def footer_contacts(kk):
    """Footer: address, phone and hours in three columns, the way viton.kz ends its pages."""
    i = 1 if kk else 0
    t = lambda ru, k: (ru, k)[i]
    col = lambda h, body: f'<div class="fc-col"><span class="fc-h">{h}</span>{body}</div>'
    return ('<div class="ft-ct" id="contacts">'
            + col(t('Адрес', 'Мекенжай'), f'<span>{t("Алматы, ул. Аносова, 91, 1 этаж", "Алматы, Аносов к-сі, 91, 1 қабат")}</span>'
                  f'<span class="fc-m">{t("мкр Тастак-3, остановка «Розыбакиева»", "Тастақ-3 ш/а, «Розыбакиев» аялдамасы")}</span>'
                  f'<a href="https://2gis.kz/almaty/firm/70000001104923303">{t("Маршрут в 2ГИС", "2ГИС-те бағыт")}</a>')
            + col(t('Запись', 'Жазылу'), '<a class="num fc-tel" href="tel:+77474956165">+7 747 495 61 65</a>'
                  f'<a href="https://wa.me/77474956165">{t("Написать в WhatsApp", "WhatsApp-қа жазу")}</a>')
            + col(t('Часы', 'Жұмыс уақыты'), f'<span>{t("Ежедневно 09:30–19:00", "Күн сайын 09:30–19:00")}</span>'
                  f'<span class="fc-m">{t("Оплата картой и наличными", "Карта және қолма-қол төлем")}</span>')
            + '</div>')


def footer_mobile(doc, kk, lg, arts):
    """Phone footer in the viton.kz shape: contacts, then folded link groups, then the legal line."""
    t = lambda ru, k: k if kk else ru
    nav = re.search(r'<nav aria-label="Footer">(.*?)</nav>', doc, re.S)
    svc = ''.join(a for a in re.findall(r'<a [^>]*>.*?</a>', nav.group(1) if nav else '') if '/blog/' not in a)
    menu = re.search(r'<nav class="dnav"[^>]*>(.*?)</nav>', doc, re.S)
    grp = lambda h, links: f'<details class="fm-g"><summary>{h}<i aria-hidden="true"></i></summary><div>{links}</div></details>'
    return ('<div class="ftm">'
            f'<p class="fm-tag">{t("Диагностика подвески на вибростенде в Алматы", "Алматыдағы вибростендте аспа диагностикасы")}</p>'
            f'<div class="fm-ct"><span class="fc-h">{t("Автосервис", "Автосервис")}</span>'
            f'<span>{t("Алматы, Аносова 91", "Алматы, Аносов к-сі 91")}</span>'
            '<a class="num fm-tel" href="tel:+77474956165">+7 747 495 61 65</a>'
            f'<span class="fc-m">{t("Ежедневно 09:30–19:00", "Күн сайын 09:30–19:00")}</span></div>'
            + grp(t('Услуги', 'Қызметтер'), svc) + grp(t('Полезное', 'Пайдалы'), arts)
            + grp(t('Разделы', 'Бөлімдер'), menu.group(1) if menu else '')
            + f'<div class="fm-bot"><span>© 2026 VibroTest.kz</span><span>{t("Алматы, Аносова 91", "Алматы, Аносов к-сі 91")}</span>'
            f'<a href="/{lg}/privacy/">{t("Политика конфиденциальности", "Құпиялылық саясаты")}</a></div></div>')


SVC_NAMES = [('Услуги и цены на ремонт ходовой в Алматы', 'Услуги по ремонту ходовой в Алматы'),
             ('Услуги и цены на ремонт ходовой', 'Услуги по ремонту ходовой'),
             ('Цена работы «от», запчасти отдельно. Точную сумму мастер называет после диагностики, до начала ремонта. Цены на октябрь 2026. Алматы, Аносова 91.',
              'Диагностика на вибростенде, рулевые рейки, подвеска, ступицы и ШРУС, тормоза, радиаторы и двигатель. Цены и подробности на странице каждой услуги. Алматы, Аносова 91.'),
             ('Алматыда жүріс бөлігін жөндеу қызметтері мен бағалары', 'Алматыда жүріс бөлігін жөндеу қызметтері'),
             ('Жүріс бөлігін жөндеу қызметтері мен бағалары', 'Жүріс бөлігін жөндеу қызметтері'),
             ('Жұмыс бағасы «бастап», қосалқы бөлшектер бөлек. Нақты соманы шебер диагностикадан кейін, жөндеу басталғанға дейін айтады. Алматы, Аносов 91.',
              'Вибростендте диагностика, рульдік рейкалар, аспа, күпшек және ШРУС, тежегіштер, радиаторлар және қозғалтқыш. Бағалар мен толық сипаттама әр қызмет бетінде. Алматы, Аносов 91.'),
             ('>Услуги и цены<', '>Услуги<'), ('>Қызметтер мен бағалар<', '>Қызметтер<'),
             ('>Все услуги и цены<', '>Все услуги<'), ('>Барлық қызметтер мен бағалар<', '>Барлық қызметтер<'),
             # «where are the prices»: the stand page has them now, the services list only links
             ('на странице <a href="/ru/services/">«Услуги и цены»</a>', 'на странице <a href="/ru/services/diagnostika-na-vibrostende/">«Диагностика на вибростенде»</a>'),
             ('на странице «Услуги и цены»', 'на странице «Диагностика на вибростенде»'),
             ('Все цены собраны на странице', 'Все цены на странице'),
             ('мына бетте жиналған: <a href="/kk/services/">«Қызметтер мен бағалар»</a>', 'мына бетте: <a href="/kk/services/diagnostika-na-vibrostende/">«Вибростендте диагностика»</a>'),
             ('мына бетте: <a href="/kk/services/">«Қызметтер мен бағалар»</a>', 'мына бетте: <a href="/kk/services/diagnostika-na-vibrostende/">«Вибростендте диагностика»</a>'),
             ('мына бетте жиналған: «Қызметтер мен бағалар»', 'мына бетте: «Вибростендте диагностика»'),
             # the stand is two mobile units under a lifted car, not platforms in the floor
             ('Машина заезжает колёсами на платформы.', 'Машину поднимают на подъёмнике и ставят колёсами на платформы стенда.'),
             ('Көлік дөңгелектерімен платформаларға кіреді.', 'Көлікті көтергішпен көтеріп, дөңгелектерімен стенд платформаларына қояды.')]


def prefix(doc):
    """Serve the whole v2 build under /v2/: rewrite root-relative links and assets."""
    doc = re.sub(r'<div class="ft-bot">.*?</div>', lambda m: re.sub(r'\s·\s', ', ', m.group(0)), doc, flags=re.S)
    for a, b in NAVY:
        doc = re.sub(a, b, doc, flags=re.I)
    kk = '<html lang="kk"' in doc[:400]
    for a, b in SVC_NAMES:
        doc = doc.replace(a, b)
    bar = (f'<div class="topbar"><div class="tb-in"><span>{"Алматы, Аносов к-сі 91" if kk else "Алматы, Аносова 91"}</span>'
           f'<span>{"Күн сайын 09:30–19:00" if kk else "Ежедневно 09:30–19:00"}</span></div></div>')
    doc = doc.replace('<header class="dh d-only">', bar + '<header class="dh d-only">', 1)
    lg = 'kk' if kk else 'ru'
    doc = re.sub(r'(<div class="ft-bot">.*?)(</div>)', lambda m: m.group(1) + f'<a href="/{lg}/privacy/">{"Құпиялылық саясаты" if kk else "Политика конфиденциальности"}</a>' + m.group(2), doc, count=1, flags=re.S)
    arts = ''.join(f'<a href="/{lg}/blog/{x[1]}/">{html.escape(x[2][1 if kk else 0])}</a>' for x in ALL_ARTS)
    doc = doc.replace('<div class="ft-bot">', f'<div class="ft-arts"><span class="fc-h">{"Пайдалы" if kk else "Полезное"}</span><div>{arts}</div></div>'
                      + footer_contacts(kk) + '<div class="ft-bot">', 1)
    doc = doc.replace('<div class="ft-bot">', footer_mobile(doc, kk, lg, arts) + '<div class="ft-bot">', 1)
    # hreflang with the region, as the search engines read it best
    doc = re.sub(r'(<link rel="alternate" hreflang=")(ru|kk)(")', r'\1\2-KZ\3', doc)
    return re.sub(r'(?<=["\'(\s,=])/(ru|kk|img|media|fonts|map|favicon\.png|apple-touch-icon\.png)(?=[/"\'\s)?#,])', PREFIX + r'/\1', doc)
