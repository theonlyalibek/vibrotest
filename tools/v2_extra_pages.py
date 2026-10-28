"""v2 only: the contacts and privacy pages, as boards in the article template, with their Kazakh text."""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
WA = 'https://wa.me/77474956165'
GIS = 'https://2gis.kz/almaty/firm/70000001104923303'
ROW = 'display: grid; grid-template-columns: 180px minmax(0, 1fr); gap: 20px; padding: 18px 0; border-bottom: 1px solid rgba(255,255,255,.1)'

CONTACTS = {
    'title': ('Контакты VibroTest: Алматы, Аносова 91', 'VibroTest байланыстары: Алматы, Аносов 91'),
    'h1': ('Контакты VibroTest в Алматы', 'VibroTest байланыстары, Алматы'),
    'crumb': ('Контакты', 'Байланыс'),
    'lead': ('Диагностика ходовой на вибростенде и ремонт подвески на Аносова, 91. Запись по телефону и в WhatsApp, без очереди на стенд.',
             'Аносов, 91 мекенжайында вибростендте жүріс бөлігінің диагностикасы және аспа жөндеу. Телефон және WhatsApp арқылы жазылу, стендке кезексіз.'),
    'rows': ((('Адрес', 'Мекенжай'), ('Алматы, ул. Аносова, 91, 1 этаж', 'Алматы, Аносов к-сі, 91, 1 қабат'),
              ('мкр Тастак-3, остановка «Розыбакиева» в 270 м', 'Тастақ-3 ш/а, «Розыбакиев» аялдамасы 270 м жерде')),
             (('Телефон и WhatsApp', 'Телефон және WhatsApp'), None, None),
             (('Часы', 'Жұмыс уақыты'), ('Ежедневно, 09:30–19:00', 'Күн сайын, 09:30–19:00'), None),
             (('Оплата', 'Төлем'), ('Карта, наличные', 'Карта, қолма-қол'), None),
             (('Въезд', 'Кіру'), ('Заезд во двор узкий: на высоком внедорожнике заезжайте медленно', 'Аулаға кіру тар: биік джиппен баяу кіріңіз'), None)),
    'book': ('Записаться в WhatsApp', 'WhatsApp арқылы жазылу'),
    'route': ('Маршрут в 2ГИС', '2ГИС-те бағыт'),
    'map': ('Здесь будет живая карта 2ГИС', None),
    'near_h': ('Рядом на той же площадке', 'Сол алаңда қатар'),
    'near': ((('Чистка форсунок и двигатель', 'Форсунка тазалау және қозғалтқыш'), 'Viton', 'https://viton.kz/ru/'),
             (('Детали для Li Auto L6–L9', 'Li Auto L6–L9 бөлшектері'), 'Lixiangshop', None)),
}

PRIVACY = {
    'title': ('Политика конфиденциальности VibroTest', 'VibroTest құпиялылық саясаты'),
    'h1': ('Политика конфиденциальности', 'Құпиялылық саясаты'),
    'crumb': ('Политика конфиденциальности', 'Құпиялылық саясаты'),
    'lead': ('Коротко: сайт не хранит ваши данные. Всё, что вы нам пишете, остаётся в WhatsApp или в телефонном разговоре.',
             'Қысқаша: сайт сіздің деректеріңізді сақтамайды. Бізге жазғаныңыздың бәрі WhatsApp-та немесе телефон әңгімесінде қалады.'),
    'body': ((('Форма записи', 'Жазылу формасы'),
              ('Форма на сайте не отправляет данные на наш сервер. Она только собирает текст сообщения и открывает WhatsApp, где вы сами решаете, отправлять его или нет.',
               'Сайттағы форма деректерді біздің серверге жібермейді. Ол тек хабарлама мәтінін жинап, WhatsApp-ты ашады, жіберу-жібермеуді өзіңіз шешесіз.')),
             (('Что мы получаем и зачем', 'Не аламыз және не үшін'),
              ('Имя и номер из WhatsApp или звонка, марку машины и описание проблемы. Используем их только чтобы записать вас и связаться по вашему ремонту.',
               'WhatsApp немесе қоңыраудан аты мен нөмір, көлік маркасы және ақау сипаттамасы. Оларды тек сізді жазу және жөндеу бойынша байланысу үшін қолданамыз.')),
             (('Кому передаём', 'Кімге береміз'),
              ('Никому. Мы не передаём ваши данные третьим лицам и не делаем рекламных рассылок.',
               'Ешкімге. Деректеріңізді үшінші тұлғаларға бермейміз және жарнамалық хабарламалар жібермейміз.')),
             (('Карта 2ГИС', '2ГИС картасы'),
              ('Карта загружается только после нажатия «Показать карту». После этого 2ГИС может получить технические данные браузера по своим правилам.',
               'Карта «Картаны көрсету» батырмасын басқаннан кейін ғана жүктеледі. Содан кейін 2ГИС өз ережелері бойынша браузердің техникалық деректерін алуы мүмкін.')),
             (('Как связаться', 'Қалай байланысуға болады'),
              ('Чтобы удалить переписку или задать вопрос о данных, напишите в WhatsApp или позвоните: +7 747 495 61 65.',
               'Хат алмасуды өшіру немесе деректер туралы сұрақ қою үшін WhatsApp-қа жазыңыз немесе қоңырау шалыңыз: +7 747 495 61 65.'))),
}


def e(s):
    return html.escape(s, quote=False)


def crumbs(c):
    return (f'<nav aria-label="Хлебные крошки" style="display: flex; gap: 10px; font-size: 14px; color: #6F7B8B"><a href="Main.dc.html" style="color: #8A96A6">Главная</a>'
            f'<span>/</span><span style="color: #C9D1DB">{e(c[0])}</span></nav>')


def page(head, foot, d, inner):
    head = re.sub(r'<title>.*?</title>', f'<title>{e(d["title"][0])}</title>', head, flags=re.S)
    return f'''{head}<section style="padding: 40px 0 120px">
<div class="w" style="display: flex; flex-direction: column; gap: 28px; max-width: 1100px">
{crumbs(d["crumb"])}
<h1 class="hd" style="font-size: 56px; line-height: 1.05; font-weight: 800">{e(d["h1"][0])}</h1>
<p style="font-size: 18px; line-height: 1.6; color: #A9B4C2; max-width: 760px">{e(d["lead"][0])}</p>
{inner}
</div>
</section>

{foot}'''


def contacts(head, foot):
    d = CONTACTS
    rows = ''
    for label, main, sub in d['rows']:
        if main is None:
            val = f'<a href="tel:+77474956165" class="num" style="font-size: 18px; color: #EEF2F7; font-weight: 600">+7 747 495 61 65</a>'
        else:
            val = e(main[0]) + (f'<br><span style="color: #8A96A6">{e(sub[0])}</span>' if sub else '')
        rows += f'<div style="{ROW}"><span style="font-size: 14px; color: #8A96A6">{e(label[0])}</span><span style="font-size: 16px; line-height: 1.55">{val}</span></div>\n'
    near = ''
    for (what, name, url) in d['near']:
        tag = 'a' if url else 'div'
        href = f' href="{url}"' if url else ''
        near += (f'<{tag}{href} style="display: flex; flex-direction: column; gap: 6px; padding: 20px; border-radius: 14px; border: 1px solid rgba(255,255,255,.1); color: #EEF2F7">'
                 f'<span class="hd" style="font-size: 19px; font-weight: 700">{name}</span><span style="font-size: 15px; color: #A9B4C2">{e(what[0])}</span></{tag}>')
    inner = f'''<div class="g2" style="gap: 56px; align-items: start">
<div style="display: flex; flex-direction: column; gap: 28px">
<div style="border-top: 1px solid rgba(255,255,255,.1)">
{rows}</div>
<div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap"><a class="btn btn-p" href="{WA}">{e(d["book"][0])}</a><a class="lnk" href="{GIS}">{e(d["route"][0])}</a></div>
</div>
<div style="position: relative; height: 420px; border-radius: 18px; overflow: hidden; background: #151B24; border: 1px solid rgba(255,255,255,.08)"><div style="position: absolute; left: 20px; bottom: 18px; font-size: 12px; color: #6F7B8B">{e(d["map"][0])}</div></div>
</div>
<h2 class="hd" style="font-size: 28px; font-weight: 800; margin-top: 24px">{e(d["near_h"][0])}</h2>
<div class="g2" style="gap: 14px">{near}</div>'''
    return page(head, foot, d, inner)


def privacy(head, foot):
    d = PRIVACY
    inner = '<div style="display: flex; flex-direction: column; gap: 28px; max-width: 760px">' + ''.join(
        f'<div><h2 class="hd" style="font-size: 24px; font-weight: 700">{e(h[0])}</h2><p style="margin-top: 10px; font-size: 16px; line-height: 1.65; color: #A9B4C2">{e(p[0])}</p></div>'
        for h, p in d['body']) + '</div>'
    return page(head, foot, d, inner)


def pairs(x, out):
    if isinstance(x, tuple) and len(x) == 2 and all(isinstance(v, (str, type(None))) for v in x) and isinstance(x[0], str):
        if x[1]:
            out[x[0]] = x[1]
    elif isinstance(x, (tuple, list)):
        for y in x:
            pairs(y, out)
    elif isinstance(x, dict):
        for y in x.values():
            pairs(y, out)


def main():
    t = (ROOT / 'src' / 'art-steering-knock.dc.html').read_text(encoding='utf-8')
    head = t[:t.index('<section style="padding: 40px 0 0">')]
    foot = t[t.index('<footer'):]
    (ROOT / 'src' / 'contacts.dc.html').write_text(contacts(head, foot), encoding='utf-8')
    (ROOT / 'src' / 'privacy.dc.html').write_text(privacy(head, foot), encoding='utf-8')
    kk = {}
    pairs(CONTACTS, kk)
    pairs(PRIVACY, kk)
    (ROOT / 'i18n' / 'kk-v2-extra.json').write_text(json.dumps(kk, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    print(len(kk), 'KK strings')


if __name__ == '__main__':
    main()
