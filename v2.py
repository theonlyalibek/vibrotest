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
    'sub': ('Выберите узел: покажем частые симптомы и цену работы. Точно скажет только диагностика.',
            'Түйінді таңдаңыз: жиі белгілер мен жұмыс бағасын көрсетеміз. Нақтысын тек диагностика айтады.'),
    'book': ('Записаться', 'Жазылу'),
    'swipe': ('Листайте вправо', 'Оңға қарай сырғытыңыз'),
    'sub_home': ('Выберите узел: покажем частые симптомы и чем мы поможем. Точно скажет только диагностика.',
                 'Түйінді таңдаңыз: жиі белгілер мен қалай көмектесетінімізді көрсетеміз. Нақтысын тек диагностика айтады.'),
    'all': ('Все услуги и цены', 'Барлық қызметтер мен бағалар'),
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
.km-list{flex-wrap:nowrap;overflow-x:auto;margin:14px -16px 0;padding:0 16px 4px;scrollbar-width:none;-webkit-mask-image:linear-gradient(90deg,#000 calc(100% - 36px),transparent);mask-image:linear-gradient(90deg,#000 calc(100% - 36px),transparent)}
.km-list::-webkit-scrollbar{display:none}
.km-chip{flex:none;min-height:48px;padding:0 18px;font-size:15px}.km-chip b{font-size:13px}
.km-swipe{display:flex;align-items:center;gap:6px;margin-top:8px;font-size:13px;color:#6F7B8B}
.km-side{margin:14px -16px 0;padding:0 16px 4px;display:flex;gap:12px;overflow-x:auto;scroll-snap-type:x mandatory;scroll-padding:0 16px;scrollbar-width:none}
.km-side::-webkit-scrollbar{display:none}
.km-side .km-panel,.km-side .km-panel[hidden]{display:flex;flex:0 0 calc(100% - 28px);scroll-snap-align:start;min-height:0}
.km-panel{padding:22px 20px;gap:12px}.km-panel h3{font-size:22px}.km-price{font-size:24px}.km-panel .btn{width:100%}
.km-unsure{margin-top:14px;font-size:14px}.km-hd{margin-bottom:18px}.km-hd p{font-size:15px}}

.ft-card{display:grid;grid-template-columns:minmax(0,1.05fr) minmax(0,1fr);gap:64px;align-items:start}
.ft-main{display:flex;flex-direction:column;gap:22px}
.ft-main h2{font:800 clamp(30px,3.6vw,50px)/1.04 'Geologica',system-ui,sans-serif;letter-spacing:-.02em;margin:0}
.ft-main>p{color:#A9B4C2;font-size:17px;line-height:1.65;margin:0}
.ft-steps{list-style:none;margin:4px 0 0;padding:0;counter-reset:st;border-top:1px solid rgba(255,255,255,.1)}
.ft-steps li{counter-increment:st;display:grid;grid-template-columns:28px 1fr;column-gap:12px;row-gap:4px;padding:14px 0;border-bottom:1px solid rgba(255,255,255,.1)}
.ft-steps li::before{content:counter(st);grid-row:span 2;color:#5AAEF2;font-weight:600;font-size:16px;line-height:1.4}
.ft-steps b{font-size:16px;color:#EEF2F7}.ft-steps span{font-size:15px;line-height:1.55;color:#A9B4C2}
.ft-cta{display:flex;align-items:center;gap:26px;flex-wrap:wrap;margin-top:auto}
.ft-cta .lnk{color:#EEF2F7;font-weight:600;font-size:15px;border-bottom:1px solid rgba(255,255,255,.28);padding-bottom:3px}
.ft-side{display:flex;flex-direction:column;gap:16px}
.ft-pic{position:relative;border-radius:14px;overflow:hidden;background:#11161E;aspect-ratio:4/5}
.ft-pic img{width:100%;height:100%;object-fit:cover;display:block}
.ft-get{padding:20px 22px;border-radius:16px;background:#F3F5F8;color:#0B1220}
.ft-get h3{font:700 18px 'Geologica',system-ui,sans-serif;margin:0 0 10px}
.ft-get ul{list-style:none;margin:0;padding:0}
.ft-row{display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid #DDE3EA;font-size:14px}
.ft-st{flex:none;min-width:104px;padding:4px 10px;border-radius:999px;font-size:13px;font-weight:600;text-align:center}
.ft-st.urgent{background:#FDE8E8;color:#B42318}.ft-st.later{background:#FEF3D7;color:#8A5A00}.ft-st.ok{background:#DDF4E6;color:#17663A}
.ft-get p{margin:10px 0 0;font-size:13px;color:#5B6576}
.dots{display:flex;gap:6px;margin-top:14px}.dots span{width:6px;height:6px;border-radius:3px;background:#3A4556;transition:width .2s,background .2s}.dots span.on{width:18px;background:#5AAEF2}
.chips{list-style:none;margin:14px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:8px}
.chips li{padding:8px 12px;border-radius:10px;background:#11161E;border:1px solid rgba(255,255,255,.08);font-size:14px;color:#D5DCE5}
.chips.cn li{border-color:rgba(90,174,242,.35);color:#EEF2F7}
.chips-h{margin:18px 0 0;font-size:13px;color:#8A96A6}
@media (max-width:899px){.ft-card{grid-template-columns:minmax(0,1fr);gap:20px}
.ft-main{gap:16px}.ft-main>p{font-size:15px}.ft-pic{aspect-ratio:16/10}
.ft-cta{gap:14px}.ft-cta .btn{width:100%}.ft-get{padding:16px}.ft-st{min-width:112px}
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
// car map: a dot or a chip picks the node and its card shows. On phones the cards are a swipeable row:
// swiping a card moves the chip row and the lit part on the drawing along with it.
[].forEach.call(document.querySelectorAll('[data-km]'),function(km){
 var btns=km.querySelectorAll('[data-node]'),panels=[].slice.call(km.querySelectorAll('.km-panel')),
  side=km.querySelector('.km-side'),list=km.querySelector('.km-list'),mq=matchMedia('(max-width:899px)'),cur='';
 function mark(id,follow){if(id===cur)return;cur=id;
  [].forEach.call(btns,function(b){var on=b.getAttribute('data-node')===id;b.setAttribute('aria-pressed',on?'true':'false');
   if(on&&!follow&&mq.matches&&b.classList.contains('km-chip'))list.scrollTo({left:b.offsetLeft-16,behavior:'smooth'})});
  panels.forEach(function(p){p.hidden=p.getAttribute('data-panel')!==id})}
 [].forEach.call(btns,function(b){b.addEventListener('click',function(){var id=b.getAttribute('data-node');mark(id);
  if(mq.matches){var p=km.querySelector('[data-panel="'+id+'"]');jump=panels.indexOf(p);side.scrollTo({left:p.offsetLeft-side.offsetLeft-16,behavior:'smooth'})}})});
 // the chip row moves with the finger, frame by frame, not after the swipe settles
 var chips=panels.map(function(p){return list.querySelector('[data-node="'+p.getAttribute('data-panel')+'"]')}),raf=0,jump=-1;
 function follow(){raf=0;if(!mq.matches||panels.length<2)return;
  var max=side.scrollWidth-side.clientWidth,f=max>0?Math.max(0,Math.min(1,side.scrollLeft/max))*(panels.length-1):0,
   i=Math.min(panels.length-2,Math.floor(f)),fr=f-i,a=chips[i],b=chips[i+1];
  if(jump>=0){if(Math.abs(f-jump)>.02)return;jump=-1}  // a tap on a chip: let the cards catch up first
  if(a&&b)list.scrollLeft=a.offsetLeft-16+(b.offsetLeft-a.offsetLeft)*fr;
  mark(panels[Math.round(f)].getAttribute('data-panel'),true)}
 side.addEventListener('scroll',function(){if(!raf)raf=requestAnimationFrame(follow)},{passive:true});
 cur=(km.querySelector('[aria-pressed=true]')||btns[0]).getAttribute('data-node');
});
// carousels with dots: the active dot follows the swipe
[].forEach.call(document.querySelectorAll('[data-dots]'),function(r){var d=r.parentNode.querySelector('.dots');if(!d)return;var dots=d.children;
 r.addEventListener('scroll',function(){var w=r.children[0].getBoundingClientRect().width+12,k=Math.min(dots.length-1,Math.round(r.scrollLeft/w));
  [].forEach.call(dots,function(s,j){s.classList.toggle('on',j===k)})},{passive:true})});
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
    return (f'<section{f' id="{sid}"' if sid else ''} class="km-sec" data-km style="padding: {"56px 16px 48px" if phone else "120px 0 0"}"><div class="{"" if phone else "w"}">'
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
    'steps': tuple((t, _KK.get(t, t), x, _KK.get(x, x)) for t, x in (
        ('Заезд на стенд', 'Ставим колёса на платформы. Седан, кроссовер, джип или пикап. Грузовые и спецтехнику не берём.'),
        ('Нагрузка и датчики', 'Платформы трясут подвеску, датчики шума стоят на узлах, рычаги давления нагружают их вручную.'),
        ('Мастер показывает', 'Находим конкретный узел и показываем люфт вживую. Не «вроде бы рычаг», а та деталь, что стучит.'),
        ('Заключение на руки', 'Срочно, можно позже, в норме. Ремонтировать у нас не обязательно.'))),
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
    return (f'<section class="ft-sec" style="padding: {"40px 16px 48px" if phone else "110px 0 0"}"><div class="{"" if phone else "w"}">'
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


def brand_chips(soup, phone):
    """Phone home: the brand list as a line of names, the way the desktop page shows it."""
    if not phone:
        return
    for p in soup.find_all('p'):
        t = p.get_text(' ', strip=True)
        if 'Toyota' in t and 'Lexus' in t:
            names = [x.strip() for x in t.split(',')]
            p.replace_with(BeautifulSoup('<p class="brands">' + ', '.join(html.escape(x.replace('-', '\u2011')) for x in names) + '</p>', 'html.parser'))
        elif 'Li Auto' in t and 'Geely' in t:
            head, _, rest = t.partition(':')
            names = [x.strip() for x in rest.split(',')]
            p.replace_with(BeautifulSoup(f'<p class="brands-h">{html.escape(head)}</p><p class="brands">' + ', '.join(html.escape(x.replace('-', '\u2011')) for x in names) + '</p>', 'html.parser'))

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
    phone = name == 'Mobile.dc.html'
    to_dots(soup)
    brand_chips(soup, phone)
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
            # reviews read as a short list, not one more carousel
            rail = soup.find(attrs={'data-dots': True})
            if rail:
                del rail['data-dots']
                rail['class'] = ['stack']
                for extra in rail.find_all(recursive=False)[3:]:
                    extra.decompose()
                d = rail.parent.find(class_='dots')
                if d:
                    d.decompose()
            # the price question, answered with a link: prices live on the services page
            faq = soup.find('details')
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
    """Long stretches, not a zebra: navy for the hero; light for the stand and the sample conclusion;
    navy again for the car map and the rack; light for brands, masters, reviews, articles and FAQ;
    navy from the booking form to the footer. Reviews and the sample sit on a cool grey well."""
    secs = [x for x in soup.find_all('section') if x.find_parent('section') is None]
    gap = 'clamp(64px, 8vw, 112px)'
    for k, sec in enumerate(secs[1:], 1):
        # sections that now change paper at an edge may not start or end flush against the next one
        m = re.match(r'\s*padding:\s*(\S+(?:\([^)]*\))?)\s+0(?:\s+(\S+(?:\([^)]*\))?))?', sec.get('style', ''))
        if m and not phone:
            top, bot = m.group(1), m.group(2) or m.group(1)
            top = gap if top == '0' else top
            bot = gap if bot == '0' else bot
            sec['style'] = sec['style'][:m.start()] + f'padding: {top} 0 {bot}' + sec['style'][m.end():]
    km = next((k for k, x in enumerate(secs) if 'km-sec' in (x.get('class') or [])), -1)
    book = next((k for k, x in enumerate(secs) if x.get('id') == 'book'), len(secs))
    for k, sec in enumerate(secs):
        if k == km + 1 and km > 0 and not phone:
            # the rack follows the map on the same navy: no second full gap between them
            sec['style'] = re.sub(r'padding:\s*(?:clamp\([^)]*\)|\S+)', 'padding: clamp(24px, 3vw, 40px)', sec.get('style', ''), count=1)
        if k == 0 or k in (km, km + 1) or k >= book:
            continue
        h = sec.find('h2')
        grey = sec.get('id') == 'reviews' or sec.find(class_='stack') or (h and h.get_text(' ', strip=True) in STORY_END)
        lighten(sec, 'grey' if grey else 'white')
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
@media (max-width:899px){.km-side{align-items:flex-start}.mv .brands{margin-top:16px!important}.mv .brands-h{margin:20px 0 -8px!important}.mv section.lt,.mv section.sec{padding-bottom:48px!important}}
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


def prefix(doc):
    """Serve the whole v2 build under /v2/: rewrite root-relative links and assets."""
    doc = re.sub(r'<div class="ft-bot">.*?</div>', lambda m: re.sub(r'\s·\s', ', ', m.group(0)), doc, flags=re.S)
    for a, b in NAVY:
        doc = re.sub(a, b, doc, flags=re.I)
    return re.sub(r'(?<=["\'(\s,=])/(ru|kk|img|fonts|map|favicon\.png|apple-touch-icon\.png)(?=[/"\'\s)?#,])', PREFIX + r'/\1', doc)
