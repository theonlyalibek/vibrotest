# VibroTest.kz

Static site for VibroTest (Almaty, Anosova 91): suspension and steering diagnostics on a vibration stand. Russian and Kazakh.

## Build

```
pip install -r requirements.txt
python3 build.py --out dist            # production (indexable, canonical https://vibrotest.kz)
python3 build.py --out dist --noindex  # preview: robots Disallow, noindex meta and headers
```

- `src/*.dc.html` are the approved design boards (desktop, phone, services, blog, articles).
- `build.py` turns them into pages under `/ru/` and `/kk/`, adds header/footer, live open status, symptom picker,
  2GIS map (`/map/anosova/`), schema.org, hreflang, sitemap, robots, llms.txt, 404, `.htaccess` (ps.kz/Apache) and `vercel.json`.
- `i18n/kk.json` maps each Russian string to Kazakh. Untranslated strings are written to `i18n/kk.missing.json`.
- `i18n/symptoms.*.json` feed the "Что беспокоит?" picker.
- `img/` source photos (converted to WebP at build), `fonts/` self-hosted Inter, Geologica, JetBrains Mono.
