<!-- ABOUTME: How to preview, test, and deploy the Catilda marketing landing. -->
<!-- ABOUTME: Static site from the Famulatus marketing design, rebranded to Catilda. -->

# Catilda landing

Marketing site for Catilda (digital employees for small business). Single-file HTML/CSS/JS plus `assets/`.

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

Based on [UliKorotysh/famulatus-website](https://github.com/UliKorotysh/famulatus-website), rebranded Famulatus → Catilda.
