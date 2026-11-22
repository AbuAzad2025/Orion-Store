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
| Single, consistent brand conviction | all benchmark sites | charcoal / panel / gold palette across header, hero, cards, footer |

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
