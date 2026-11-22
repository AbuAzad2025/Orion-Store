# Translation & RTL/LTR audit

Goal: **no English UI text in Arabic mode, no Arabic UI text in English mode**,
with every page checked in both directions.

## How it was checked

`scripts/audit_translation.py` renders 100 page variants (storefront in `ar`
and `en`, admin and platform pages in `ar`) through the Flask test client with
real authenticated sessions, strips script/style/tags, and flags:

- Arabic script characters on English pages
- Latin word tokens on Arabic pages

Four parallel read-only audits covered storefront templates, admin templates
(A–G and H–W), and backend user-facing strings.

## Fixed

### Storefront
- `ui_text.py`: added ~55 bilingual keys; both dictionaries stay in sync.
- `account.html`, `checkout.html`, `consent.html`, `consent_banner.html`,
  `page.html`: replaced all hardcoded Arabic/English text with `t()`.
- `header.html`: language switcher labels and aria-labels are localised.
- `routes.py`: page titles and the 404 message are translated.
- `index.html`: hero spotlight uses the translated product record.
- `whatsapp.py`: order message is locale-aware.

### Backend
- `core/i18n_messages.py`: central message catalogue plus `localize()` and
  `request_locale()`. `orion/app.py` translates the `error` field of JSON
  responses using the request locale (skipped in testing so API contracts stay
  stable). This covers hundreds of service/API messages at one point.
- Order confirmation email, workflow email fallback, default invoice heading,
  and checkout payment labels now have real English variants.
- `scripts/seed_translations.py`: seeds English product/category translations
  (90 rows) so catalogue data is not Arabic on English pages.
- Demo dataset enables the `multi_language` flag and creates a platform admin.

### Admin
- 47 exact replacements of English labels/aria-labels/headings with Arabic in
  login, sidebar, platform settings/users/tenants, compliance, OMS, metafields,
  gateways, UI kit and related templates.
- Physical `left-0 right-0` / `text-right` replaced with logical utilities.

## Legitimate exceptions (not translation bugs)

Brand names (`Azadexa`, `PayPal`, `Stripe`, `Tabby`, `Tamara`), currency codes
(`AED`, `USD`, `EUR`, `ILS`, `GBP`, `JOD`, `SAR`), ISO/example values (`PS`,
`SAVE10`, phone numbers, emails), technical identifiers (`SSO`, `OAuth`,
`SAML`, `OpenID Connect`, `JSON-LD`, schema.org type names, `slug`, `SKU`), and
language endonyms in a locale selector.

## Live role-by-role walkthrough (single browser tab)

Acted as platform admin, store admin, customer and developer across every
template: 7 platform pages, 34 store-admin pages and all storefront pages.

Real browser findings that source audits could not catch, all fixed:

- BOPIS location printed `[object Object]` instead of the address text
  (`tenant_ops.js` now normalises object/string addresses).
- Schema-markup page title was still English (`routes.py`).
- Currency admin showed a permanent loading state and an English API error
  (`admin_currency.js` now shows a clear Arabic message and handles convert errors).
- Feature-flag page showed `Rollout:` in English (`tenant_admin.js`).
- App-platform page showed `sandbox` in English (`admin_app_platform.js`).
- Cart rendered raw AED numbers under an EUR label — no conversion. `cart.js`
  now uses the footer's customer FX rate (incl. 3%) and body currency metadata;
  verified live: `1899.00 AED → 485.33 EUR`.
- Cart/WhatsApp/customer JS strings were Arabic-only; now localised via
  `document.documentElement.lang` and template data attributes.
- API clients now send `X-Locale` from the page language, so server-side
  messages (payment labels, errors) match the page instead of the browser's
  `Accept-Language`. Verified: checkout payment label changed from
  "Cash on delivery" to "الدفع عند الاستلام" on the Arabic page.

## Result

- `scripts/audit_translation.py`: **100 page renders, 0 foreign-language UI strings**.
- Live browser check (single tab): `ar` → `lang=ar`, `dir=rtl`, body direction
  `rtl`; `en` → `lang=en`, `dir=ltr`, body direction `ltr`; English pages contain
  no Arabic script, including checkout and product pages.
- `pre-commit` green; UI + i18n + notification tests green.
