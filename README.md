<!-- ABOUTME: How to preview, test, and deploy the Catilda marketing landing. -->
<!-- ABOUTME: Static site from UliKorotysh/catilda-site; App Platform deploys from main. -->

# Catilda landing

Marketing site for Catilda (your digital employee). Self-contained `index.html` plus `brand.html`.

## Local

```bash
python3 -m http.server 8080 --bind ::
# open http://localhost:8080
```

## Tests

```bash
python3 -m unittest discover -s tests -v
```

## Deploy

DigitalOcean App Platform uses `.do/app.yaml` (`catilda.com` / `www.catilda.com`).
Push to `main` with `deploy_on_push: true`.

GitHub Pages alternative: **Settings → Pages → Deploy from branch → main / (root)**.

## Source

Imported from [UliKorotysh/catilda-site](https://github.com/UliKorotysh/catilda-site)
(preview: https://ulikorotysh.github.io/catilda-site/).
