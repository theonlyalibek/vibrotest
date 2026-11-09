"""VibroTest and Viton share one address (Аносова 91), one phone and one founder.
VibroTest owns the running gear, steering, brakes and radiator replacement; Viton owns the engine,
injectors, computer diagnostics, heater flushing and air conditioning. These blocks send people
(and AI answers) to the right one. Rule: flush the heater = Viton, replace the radiator = VibroTest.
Prices are only the ones each site states. Every string is (ru, kk); links to viton.kz/ru/ become /kk/ on KK pages."""
import html

from bs4 import BeautifulSoup

V = 'https://viton.kz/ru/'
PHONE = '+7 747 495 61 65'

# board -> (text, link text, Viton path): one line in the text, right where the topic turns to Viton's side
CALLOUT = {
    'svc-cooling.dc.html': (
        ('Если радиатор печки не течёт, а просто забит и печка дует холодным, его обычно сначала промывают без снятия. Это делают соседи в Viton на том же адресе, от 15 000 ₸.',
         'Пеш радиаторы ақпай, тек бітеліп, пеш суық үрлесе, оны әдетте алдымен шешпей жуады. Мұны сол мекенжайдағы көршілес Viton жасайды, 15 000 ₸-ден.'),
        ('Промывка печки в Viton', 'Viton-да пешті жуу'), 'services/heater-cleaning/'),
    'art-antifriz.dc.html': (
        ('Если течи нет, а печка дует холодным, причина бывает в забитом радиаторе печки, термостате или воздушной пробке. Это подробно разбирают соседи в Viton.',
         'Ағу жоқ, бірақ пеш суық үрлесе, себебі бітелген пеш радиаторында, термостатта немесе ауа тығынында болуы мүмкін. Мұны көршілес Viton толық талдайды.'),
        ('Печка дует холодным: причины', 'Пеш суық үрлейді: себептері'), 'blog/pechka-duet-holodnym/'),
    'art-zima.dc.html': (
        ('Перед зимой стоит проверить и печку: если она греет слабо, радиатор обычно промывают без снятия. Это делают соседи в Viton на том же адресе.',
         'Қыс алдында пешті де тексерген жөн: нашар жылытса, радиаторды әдетте шешпей жуады. Мұны сол мекенжайдағы көршілес Viton жасайды.'),
        ('Промывка печки в Viton', 'Viton-да пешті жуу'), 'services/heater-cleaning/'),
    'l-pered-pokupkoy.dc.html': (
        ('Что именно смотрят в двигателе перед покупкой, подробно рассказывают соседи в Viton на том же адресе.',
         'Сатып алар алдында қозғалтқышта нақты нені қарайтынын сол мекенжайдағы көршілес Viton толық айтады.'),
        ('Проверка двигателя перед покупкой', 'Сатып алар алдында қозғалтқышты тексеру'), 'blog/proverka-dvigatelya-pered-pokupkoj/'),
    'art-kitaycy.dc.html': (
        ('У многих китайских машин двигатели с непосредственным впрыском, и их форсунки чистят иначе, чем обычные. Об этом рассказывают соседи в Viton.',
         'Көптеген қытай көліктерінде тікелей бүркуі бар қозғалтқыштар, олардың форсункаларын әдеттегіден басқаша тазалайды. Бұл туралы көршілес Viton айтады.'),
        ('Чистка форсунок GDI и TSI', 'GDI және TSI форсункаларын тазалау'), 'blog/chistka-forsunok-gdi-tsi/'),
    'art-gul.dc.html': (
        ('Если гудит не на скорости, а двигатель трясёт на холостых, дело не в ходовой. Причины разбирают соседи в Viton.',
         'Жылдамдықта емес, бос жүрісте қозғалтқыш дірілдесе, мәселе жүріс бөлігінде емес. Себептерін көршілес Viton талдайды.'),
        ('Троит двигатель: причины', 'Қозғалтқыш троит: себептері'), 'blog/troit-dvigatel/'),
    'art-podveska-ceny.dc.html': (
        ('Цены на работы по двигателю, чистку форсунок и промывку печки смотрите у соседей в Viton на том же адресе.',
         'Қозғалтқыш жұмыстарының, форсунка тазалаудың және пешті жуудың бағаларын сол мекенжайдағы көршілес Viton-нан қараңыз.'),
        ('Услуги и цены Viton', 'Viton қызметтері мен бағалары'), 'services/'),
    'art-check-engine.dc.html': (
        ('Частые коды ошибок и что они обычно значат, подробно разбирают соседи в Viton.',
         'Жиі кездесетін қате кодтарын және олардың әдетте нені білдіретінін көршілес Viton толық талдайды.'),
        ('Горит Check Engine: разбор в Viton', 'Check Engine жанып тұр: Viton талдауы'), 'blog/gorit-check-engine/'),
    'art-pechka-radiator.dc.html': (
        ('Если радиатор не течёт, начните с промывки: её делают соседи в Viton на том же адресе, от 15 000 ₸. Как они решают, промыть или менять, рассказано у них в статье.',
         'Радиатор ақпаса, жуудан бастаңыз: оны сол мекенжайдағы көршілес Viton жасайды, 15 000 ₸-ден. Жуу керек пе, ауыстыру керек пе, оны қалай шешетінін олар мақаласында айтады.'),
        ('Печка не греет: промыть или менять радиатор', 'Пеш жылытпайды: жуу ма, радиаторды ауыстыру ма'), 'blog/pechka-ne-greet-promyt-ili-menyat-radiator/'),
}

ENGINE_H1 = ('Проверка двигателя сканером', 'Қозғалтқышты сканермен тексеру')
ENGINE_META = (('Проверка двигателя сканером, от 5 000 ₸ — VibroTest',
                'Читаем ошибки двигателя сканером, в том числе вместе с проверкой ходовой перед покупкой. От 5 000 ₸. Полная диагностика двигателя и чистка форсунок — в Viton на том же адресе, Аносова 91.'),
               ('Қозғалтқышты сканермен тексеру, 5 000 ₸ бастап — VibroTest',
                'Қозғалтқыш қателерін сканермен оқимыз, сатып алар алдында жүріс бөлігін тексерумен бірге де. 5 000 ₸ бастап. Толық диагностика және форсунка тазалау — сол мекенжайдағы Viton-да, Аносов 91.'))
ENGINE = {
    'h': ('Двигатель целиком — в Viton по соседству', 'Қозғалтқыш толығымен — көршілес Viton-да'),
    'p': (('VibroTest занимается ходовой, рулевым и тормозами. Сканером мы читаем ошибки и смотрим параметры двигателя, в том числе при проверке машины перед покупкой.',
           'VibroTest жүріс бөлігімен, рульмен және тежегішпен айналысады. Сканермен қателерді оқып, қозғалтқыш параметрлерін қараймыз, оның ішінде сатып алар алдында көлікті тексергенде.'),
          ('Если причину нужно искать глубже, двигатель смотрят соседи в Viton на том же адресе, Аносова 91: компьютерная диагностика от 5 000 ₸, чистка форсунок, замер компрессии, эндоскопия. Телефон общий: ' + PHONE + '.',
           'Себебін тереңірек іздеу керек болса, қозғалтқышты сол мекенжайдағы көршілес Viton қарайды, Аносов 91: компьютерлік диагностика 5 000 ₸-ден, форсунка тазалау, компрессияны өлшеу, эндоскопия. Телефон ортақ: ' + PHONE + '.')),
    'links': ((('Компьютерная диагностика в Viton', 'Viton-да компьютерлік диагностика'), 'services/computer-diagnostics/'),
              (('Чистка форсунок', 'Форсунка тазалау'), 'services/injector-cleaning/'),
              (('Замер компрессии', 'Компрессияны өлшеу'), 'services/compression-test/'),
              (('Горит Check Engine: что делать', 'Check Engine жанып тұр: не істеу керек'), 'blog/gorit-check-engine/')),
}

# home and contacts: what else is done at the same address
HOME = {
    'h': ('Что ещё делаем на Аносова 91', 'Аносов 91-де тағы не жасаймыз'),
    'p': (('На том же адресе работает Viton — сервис по двигателю того же основателя, Виктора Новикова. Там чистят форсунки, делают компьютерную диагностику двигателя, замер компрессии, промывку печки и заправку кондиционера.',
           'Сол мекенжайда Viton жұмыс істейді — сол негізін қалаушының, Виктор Новиковтың қозғалтқыш сервисі. Онда форсункаларды тазалайды, қозғалтқышты компьютерлік диагностикалайды, компрессияны өлшейді, пешті жуады және кондиционерге фреон толтырады.'),
          ('Правило простое: стучит, тянет в сторону, скрипят тормоза, течёт радиатор — к нам в VibroTest. Троит двигатель, горит Check Engine, печка дует холодным, не холодит кондиционер — в Viton. Телефон общий: ' + PHONE + '.',
           'Ереже қарапайым: тықылдайды, бір жаққа тартады, тежегіш сықырлайды, радиатор ағады — бізге, VibroTest-ке. Қозғалтқыш троит, Check Engine жанады, пеш суық үрлейді, кондиционер салқындатпайды — Viton-ға. Телефон ортақ: ' + PHONE + '.')),
    'links': ((('Чистка форсунок', 'Форсунка тазалау'), 'services/injector-cleaning/'),
              (('Диагностика двигателя', 'Қозғалтқыш диагностикасы'), 'services/computer-diagnostics/'),
              (('Промывка печки', 'Пешті жуу'), 'services/heater-cleaning/'),
              (('Заправка кондиционера', 'Кондиционерге фреон толтыру'), 'services/ac-refill/'),
              (('Все услуги Viton', 'Viton-ның барлық қызметтері'), 'services/')),
}

# one more question on the pages people reach with an engine problem
FAQ = (('А двигатель и форсунки у вас смотрят?', 'Қозғалтқыш пен форсункаларды сіздер қарайсыздар ма?'),
       ('Мы занимаемся ходовой, рулевым, тормозами и заменой радиаторов. Двигатель, чистку форсунок, промывку печки и заправку кондиционера делают соседи в Viton на том же адресе, Аносова 91. Телефон общий: ' + PHONE + '.',
        'Біз жүріс бөлігімен, рульмен, тежегішпен және радиаторларды ауыстырумен айналысамыз. Қозғалтқышты, форсунка тазалауды, пешті жуу мен кондиционерге фреон толтыруды сол мекенжайдағы көршілес Viton жасайды, Аносов 91. Телефон ортақ: ' + PHONE + '.'))
FAQ_ON = ('svc-engine.dc.html', 'svc-cooling.dc.html', 'svc-suspension.dc.html')

CSS = ('.vt-nb{margin:28px 0;padding:18px 22px;border-left:3px solid #0290FE;border-radius:0 12px 12px 0;background:rgba(2,144,254,.07)}'
       '.vt-nb a{font-weight:600}.vt-vl{display:flex;flex-wrap:wrap;gap:10px 22px;margin:18px 0 0;padding:0;list-style:none}.vt-vl a{font-weight:600}'
       '.vt-vit p{max-width:860px}.vt-vit h2{margin-bottom:14px}.vt-vit p+p{margin-top:12px}.vt-vit ul.vt-vl{margin-top:18px!important}.mv .vt-vit{padding:40px 16px 48px!important}')


def add_faq(svc):
    for b in FAQ_ON:
        if b in svc and not any(q[0] == FAQ[0][0] for q in svc[b]['f']):
            svc[b]['f'] = svc[b]['f'] + [(FAQ[0][0], FAQ[0][1], FAQ[1][0], FAQ[1][1])]


def _a(i, text, path):
    return f'<a href="{V}{path}">{html.escape(text[i])}</a>'


def _block(c, i, pad):
    return (f'<section class="vt-x vt-vit" style="padding: {pad}"><div class="w"><h2>{html.escape(c["h"][i])}</h2>'
            + ''.join(f'<p>{html.escape(p[i])}</p>'.replace(PHONE, f'<span style="white-space:nowrap">{PHONE}</span>') for p in c['p'])
            + '<ul class="vt-vl">' + ''.join(f'<li>{_a(i, t, p)}</li>' for t, p in c['links']) + '</ul></div></section>')


def apply(soup, name, lang):
    i = 0 if lang == 'ru' else 1
    if name in CALLOUT:
        text, link, path = CALLOUT[name]
        nb = BeautifulSoup(f'<p class="vt-nb">{html.escape(text[i])} {_a(i, link, path)}</p>', 'html.parser')
        art = soup.find('article', class_='art')
        if art is not None:
            faq_h = next((h for h in art.find_all('h2', recursive=False) if h.find_next_sibling('div') and h.find_next_sibling('div').find('details')), None)
            (faq_h.insert_before if faq_h else art.append)(nb)
        else:
            faq = next((d.find_parent('section') for d in soup.find_all('details') if 'km-it' not in (d.get('class') or [])), None)
            box = BeautifulSoup(f'<section class="vt-x" style="padding: 0 0 72px"><div class="w">{nb}</div></section>', 'html.parser')
            if faq is not None:
                faq.insert_before(box)
    if name == 'svc-engine.dc.html':
        h1 = soup.find('h1')
        if h1 is not None:
            h1.string = ENGINE_H1[i]
        hero = soup.find('section')
        if hero is not None:
            hero.insert_after(BeautifulSoup(_block(ENGINE, i, 'clamp(36px, 4.5vw, 64px) 0 0'), 'html.parser'))
    if name in ('Main.dc.html', 'Mobile.dc.html', 'contacts.dc.html'):
        blk = BeautifulSoup(_block(HOME, i, '40px 16px 48px' if name == 'Mobile.dc.html' else '0 0 96px'), 'html.parser')
        book = soup.find(id='book')
        if book is not None and book.name == 'section':
            book.insert_before(blk)
        else:
            secs = soup.find_all('section')
            if secs:
                secs[-1].insert_after(blk)
    if lang == 'kk':
        for a in soup.find_all('a', href=True):
            if a['href'].startswith(V):
                a['href'] = 'https://viton.kz/kk/' + a['href'][len(V):]


# llms.txt: which of the two neighbours to send a person to, by symptom
ROUTE = (('Стук в подвеске, люфт или стук в руле', 'VibroTest', 'https://vibrotest.kz/ru/services/diagnostika-na-vibrostende/'),
         ('Машину уводит, скрип или стук в подвеске', 'VibroTest', 'https://vibrotest.kz/ru/services/remont-podveski/'),
         ('Скрипят или бьют тормоза', 'VibroTest', 'https://vibrotest.kz/ru/services/tormoza/'),
         ('Течёт антифриз, нужно заменить радиатор двигателя или печки, патрубки', 'VibroTest', 'https://vibrotest.kz/ru/services/radiatory-patrubki/'),
         ('Печка дует холодным, радиатор не течёт (промывка без снятия, от 15 000 ₸)', 'Viton', V + 'services/heater-cleaning/'),
         ('Горит Check Engine, полная компьютерная диагностика двигателя (от 5 000 ₸)', 'Viton', V + 'services/computer-diagnostics/'),
         ('Троит двигатель, плавают обороты, вырос расход, чистка форсунок', 'Viton', V + 'services/injector-cleaning/'),
         ('Не холодит кондиционер, заправка фреоном (от 15 000 ₸)', 'Viton', V + 'services/ac-refill/'),
         ('Проверка машины перед покупкой: ходовая на вибростенде и двигатель сканером', 'VibroTest', 'https://vibrotest.kz/ru/services/proverka-pered-pokupkoy/'))


def llms_section():
    out = ['', '## Соседний сервис на том же адресе: Viton',
           f'Viton.kz ({V}) работает на том же адресе, Алматы, ул. Аносова, 91, у него тот же основатель, Виктор Новиков, и общий телефон {PHONE}. '
           'VibroTest — ходовая, рулевое, тормоза, замена радиаторов. Viton — двигатель, форсунки, компьютерная диагностика, промывка печки, кондиционер. '
           'Правило: промыть печку — Viton, заменить радиатор — VibroTest.', '',
           '| Симптом | Куда | Страница |', '|---|---|---|']
    out += [f'| {s} | {w} | {u} |' for s, w, u in ROUTE]
    return out
