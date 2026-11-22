# Storefront design benchmark

The storefront was audited against the patterns used by the world's leading
stores (Nike, Apple, Gymshark, Aesop, Glossier, and the Baymard top-1% cohort).
Sources: Toimi "Best E-Commerce Website Designs 2026", Baymard UX benchmark,
Charle Agency "12 Best Ecommerce Web Designs".

## Patterns identified

| Pattern | Where it is used | Applied here |
|---------|------------------|--------------|
| Trust / cost signals stated before the cart | Nike, Gymshark, Baymard top-1% | `orion-trustbar` (secure payment, fast delivery, WhatsApp support) |
| Product is the hero, not generic stock | Apple, Nike, Aesop | Editorial two-column hero with a real product spotlight |
| Sticky buy control on the PDP | Apple, Gymshark | `orion-sticky-buy` fixed bottom bar with image, name, price, add-to-cart |
| Social proof next to the price | Nike, Gymshark, Represent | `orion-pdp-trust` badges on the product detail page |
| Product photography as infrastructure | every benchmark site | 12 keyword-matched free-stock photos per tenant, consistent 4:3 crop |
| Hover feedback on product media | Nike, Gymshark | card lift + image zoom on hover |
| Typography as a brand asset | Bottega, Aesop, Geist-based sites | one self-hosted family — **Tajawal** — across body, headings, navbar, footer and bars |
| Single, consistent brand conviction | all benchmark sites | charcoal / panel / gold palette across header, hero, cards, footer |

## Arabic typography

The previous build used a generic system stack (`Segoe UI` / `Tahoma`), which
is not comparable to benchmark stores and falls back to Tahoma for Arabic on
Windows. It is now replaced with two modern Arabic web fonts:

- **Tajawal** (400/500/700/800/900) — the single family used for every piece
  of text: body, headings, prices, navbar, footer, buttons and trust bars.

Using one family keeps the page visually coherent. Only weights that exist in
the font files are used, so bold text is real rather than browser-synthesised.

`scripts/fetch_fonts.py` downloads the licensed woff2 files from Google Fonts
at build time and commits them under both `static/fonts/` folders, generating
a `fonts.css` per app with the correct URL prefix. This keeps the strict CSP
(`default-src 'self'`) intact — no third-party requests and no CSP relaxation.

Verified in the browser: 10 `@font-face` rules, no external font requests,
Tajawal 400/700/800/900 loaded, and every text element resolves to Tajawal.

## Implementation notes

- All new strings are bilingual (Arabic + English) in `06-STOREFRONT/engine/ui_text.py`.
- `01-FOUNDATION/assets/orion-theme.css` is the single source; the two shipped
  copies are regenerated with `npm run build:css`.
- Asset URLs carry a content hash (`asset_version`), so CSS/JS changes are
  visible immediately instead of being served from browser cache.

## Verification

Live DOM checks on the seeded `gulf` tenant (single browser tab):

- trust bar: 3 items rendered with correct Arabic labels
- hero: two-column grid (`454.8px 336.2px`), spotlight image loaded at 800px
- 12/12 product images loaded
- PDP: sticky buy bar `position: fixed`, 3 trust badges, 2 add-to-cart controls

`pre-commit`, `audit_a11y.py --check` and `audit_contrast.py --check` all pass
with zero violations.
