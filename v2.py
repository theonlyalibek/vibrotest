"""v2 additions to the build: the service landing pages and the «Где стучит?» car map.

build.py imports this only with --v2; the current site at the root stays as it is.
"""
import html, json, re
from pathlib import Path
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parent
LANDINGS = json.loads((ROOT / 'i18n' / 'v2-pages.json').read_text(encoding='utf-8'))
KK_EXTRA = json.loads((ROOT / 'i18n' / 'kk-v2.json').read_text(encoding='utf-8'))
PREFIX = '/v2'

# price-row name -> landing board, so rows on the services and category pages link to the landing
ROW_LINK = {}
for p in LANDINGS:
    for r in p['rows']:
        ROW_LINK.setdefault(r, p['board'])
ROW_LINK['Стенд и двигатель перед покупкой'] = 'l-pered-pokupkoy.dc.html'
ROW_LINK['Диагностика ходовой на вибростенде'] = 'svc-vibrostand.dc.html'
ROW_LINK['Компьютерная диагностика двигателя'] = 'svc-engine.dc.html'

# symptom picker on the home page: send people to the narrow page when there is one
SYM_HREF = {'Стук или люфт в руле': 'l-tyagi.dc.html', 'Хруст при повороте': 'l-shrus.dc.html',
            'Гул растёт со скоростью': 'l-stupica.dc.html', 'Машину раскачивает': 'l-amortizatory.dc.html',
            'Перед покупкой авто': 'l-pered-pokupkoy.dc.html'}


def pages():
    return {p['board']: (f'services/{p["slug"]}/', 'service') for p in LANDINGS}


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


# ---------- «Где стучит?» ----------

T2 = {
    'h': ('Что не так с машиной?', 'Көлікте не ақау?'),
    'sub': ('Нажмите на узел или выберите из списка: покажем частые симптомы и цену работы. Точно скажет только диагностика.',
            'Түйінді басыңыз немесе тізімнен таңдаңыз: жиі белгілер мен жұмыс бағасын көрсетеміз. Нақтысын тек диагностика айтады.'),
    'book': ('Записаться', 'Жазылу'),
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
.km-fig{position:relative;border-radius:18px;background:radial-gradient(120% 90% at 30% 70%,#122033 0,#0E131A 60%);border:1px solid rgba(255,255,255,.08);padding:28px 20px 18px}
.km-car{display:block;width:100%;height:auto}
.km-body{fill:#141B25;stroke:#3A4757;stroke-width:2.5}
.km-glass{fill:#0E1520;stroke:#2B3644;stroke-width:2}
.km-xray *{fill:none;stroke:#2F6EA3;stroke-width:2;opacity:.55}
.km-wheel circle{fill:#0B1018;stroke:#56647A;stroke-width:3}
.km-wheel circle:nth-child(2n){fill:none;stroke:#2B3644}
.km-trim{fill:none;stroke:#252F3C;stroke-width:2}.km-light{fill:#5AAEF2;opacity:.5}
.km-fig::after{content:'';position:absolute;top:0;bottom:0;left:0;width:22%;background:linear-gradient(90deg,transparent,rgba(90,174,242,.07),transparent);animation:kmScan 6s linear infinite;pointer-events:none}
@keyframes kmScan{0%{transform:translateX(-100%)}100%{transform:translateX(560%)}}
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
.plink{color:inherit;border-bottom:1px solid currentColor;border-bottom-color:rgba(127,140,160,.45)}
.plink:hover{color:#0071BC}
.prow .plink:hover{color:#5AAEF2}
@media (max-width:899px){.km{grid-template-columns:minmax(0,1fr);gap:16px}.km-fig{padding:16px 8px 10px}.km-dots{inset:16px 8px 10px}
.km-dot{width:30px;height:30px;margin:-15px 0 0 -15px;font-size:10px}.km-dot::before,.km-dot::after{inset:7px}
.km-list{flex-wrap:nowrap;overflow-x:auto;margin:14px -16px 0;padding:0 16px 4px;scrollbar-width:none}.km-list::-webkit-scrollbar{display:none}
.km-chip{flex:none}.km-panel{padding:22px 20px}.km-panel h3{font-size:22px}.km-price{font-size:24px}.km-hd{margin-bottom:20px}.km-hd p{font-size:15px}}
@media (prefers-reduced-motion:reduce){.km-dot::after,.km-fig::after{animation:none}.km-fig::after{display:none}}
'''

JS = r'''
// «Где стучит?»: a dot or a chip picks the node, the matching panel shows
[].forEach.call(document.querySelectorAll('[data-km]'),function(km){
 var btns=km.querySelectorAll('[data-node]'),panels=km.querySelectorAll('.km-panel');
 function pick(id){[].forEach.call(btns,function(b){b.setAttribute('aria-pressed',b.getAttribute('data-node')===id?'true':'false')});
  [].forEach.call(panels,function(p){p.hidden=p.getAttribute('data-panel')!==id})}
 [].forEach.call(btns,function(b){b.addEventListener('click',function(){pick(b.getAttribute('data-node'))})});
});
'''


def knock_map(lang, url_for, wa, phone=False, sid=''):
    i = 0 if lang == 'ru' else 1
    from urllib.parse import quote
    dots, chips, panels = [], [], []
    for n, (key, x, y, title, text, price, links) in enumerate(NODES, 1):
        on = n == 1
        t = html.escape(title[i])
        if x is not None:
            dots.append(f'<button type="button" class="km-dot" data-node="{key}" aria-pressed="{"true" if on else "false"}" '
                        f'aria-label="{t}" style="left:{x / 10:.1f}%;top:{y / 3.4:.1f}%"><span>{n}</span></button>')
        num = f'<b>{n}</b>' if x is not None else ''
        chips.append(f'<button type="button" class="km-chip" data-node="{key}" aria-pressed="{"true" if on else "false"}">{num}{t}</button>')
        p = f'{price:,}'.replace(',', ' ') + ' ₸'
        rows = ''.join(f'<a href="{url_for(lang, b)}"><span>{html.escape(l[i])}</span><span aria-hidden="true">→</span></a>' for b, *l in links)
        msg = quote(T2['wa'][i].replace('{x}', title[i].lower() if lang == 'ru' else title[i]), safe='')
        panels.append(f'<div class="km-panel" data-panel="{key}"{"" if on else " hidden"}><span class="k">{f"{n:02d}" if x is not None else "—"}</span><h3>{t}</h3>'
                      f'<p>{html.escape(text[i])}</p><div class="km-price">{T2["from"][i].format(p=p)}</div>'
                      f'<div class="km-links">{rows}</div><a class="btn btn-p" href="{wa}?text={msg}">{T2["book"][i]}</a></div>')
    unsure = T2['unsure'][i]
    head, tail = unsure.rsplit('?', 1) if '?' in unsure else ('', unsure)
    return (f'<section{f' id="{sid}"' if sid else ''} class="km-sec" data-km style="padding: {"56px 16px 0" if phone else "120px 0 0"}"><div class="{"" if phone else "w"}">'
            f'<div class="km-hd"><h2>{T2["h"][i]}</h2><p>{T2["sub"][i]}</p></div>'
            f'<div class="km"><div><div class="km-fig" role="group" aria-label="{T2["aria"][i]}">{CAR}<div class="km-dots">{"".join(dots)}</div></div>'
            f'<div class="km-list">{"".join(chips)}</div>'
            f'<span class="km-unsure">{head}? <a href="{url_for(lang, "svc-vibrostand.dc.html")}">{tail.strip()}</a></span></div>'
            f'<div>{"".join(panels)}</div></div></div></section>')


def insert_map(soup, name, lang, url_for, wa):
    """Home: replaces the «Что беспокоит?» picker (one tool, not two). Services: right after the hero."""
    anchor = None
    if name in ('Main.dc.html', 'Mobile.dc.html'):
        chip = soup.find('button', class_='chip')
        anchor = chip.find_parent('section') if chip else None
    elif name == 'Services.dc.html':
        anchor = soup.find('section')
    if anchor is None:
        return
    home = name in ('Main.dc.html', 'Mobile.dc.html')
    new = BeautifulSoup(knock_map(lang, url_for, wa, name == 'Mobile.dc.html', 'symptom' if name == 'Main.dc.html' else ''), 'html.parser')
    if home:
        anchor.replace_with(new)
    else:
        anchor.insert_after(new)


def prefix(doc):
    """Serve the whole v2 build under /v2/: rewrite root-relative links and assets."""
    return re.sub(r'(?<=["\'(\s,=])/(ru|kk|img|fonts|map|favicon\.png|apple-touch-icon\.png)(?=[/"\'\s)?#,])', PREFIX + r'/\1', doc)
