# خطة الجاهزية الإنتاجية — Orion / Azadexa

> **تاريخ كتابة الخطة:** 2026-11-19
> **مصدر الخطة:** فحص مباشر للكود (لا مستندات). كل رقم أدناه مُستخرج من ملف فعلي،
> مصحوب بمسار الملف عند الحاجة. أي تعارض مع `README.md` أو `ORION-Project-Plan-Report.md`
> يُحسم لمصلحة الكود.
> **الجمهور:** المطوّر / Tech Lead. **الهدف:** تحويل المشروع من "يعمل محلياً"
> إلى "جاهز للإنتاج بثقة عالية".

---

## تحديث التنفيذ — P0 مكتمل (2026-11-19)

| المرحلة | الحالة | ما نُفّذ فعلياً |
|---|---|---|
| 0 — الحقيقة والبيئة | ✅ | تصحيح README (الأرقام/بيانات الأدمن)، توحيد `psycopg2=2.9.12` و`pyyaml=6.0.3`، إنشاء `.env` بمفاتيح مولّدة، `ADR/0001`، إقلاع `create_app` ناجح (250 route) |
| 1 — الأمان | ✅ | `JWT_COOKIE_SECURE`/`SESSION_COOKIE_SECURE`/HSTS/PREFERRED_URL_SCHEME في production، فشل الإقلاع بالمفاتيح الافتراضية، إصلاح legacy accept في توقيع PayPal + منع replay، secret scanning وBandit في CI (الـ login limits كانت موجودة أصلاً) |
| 2 — العزل | ✅ | 4 اختبارات سلبية (قراءة/تعديل/حذف عبر API + service)، هجرة `rls_coverage_0025` ترفع التغطية من 32 إلى **90/90** جدول، `app.is_platform_admin` في middleware وسياق Celery، `scripts/audit_rls.py --check` في CI |
| 3 — الدفع | ✅ | طبقة `_http` مشتركة، 4 adapters حقيقية (Stripe REST، PayPal Orders v2، PalPay، BNPL)، idempotency key ثابت لكل طلب، فشل صريح في production عند غياب الاعتماد، منع مكالمات الشبكة خارج production عبر `PAYMENT_LIVE_CALLS_ENABLED` |

**تحقق:** black/isort/flake8/file-length/RLS audit كلها خضراء. أثناء الاختبار الكامل
ظهرت 4 فشل: اثنان ناتجان عن تعديل الخطة (توقيع PayPal مع epoch، وتسريب
`guard_beta_program` من `register_middleware`) وتم إصلاحهما، واثنان كانا موجودين
أصلاً في `HEAD` (اختبار reconciliation يستخدم `financial_event_id=1` غير موجود،
واختبار audit يستخدم صلاحيات مستأجر بدل platform admin) وتم إصلاحهما أيضاً.
ثم ظهرت 4 فشل إضافية في `tests/services/test_v2_services.py` (نفس نمط المعرّفات
الثابتة: `product_id=42`، `order_id=1`، `financial_event_id=1`، `user_id=1`) — كلها
سابقة على تعديلاتنا، وتم استبدالها بكيانات حقيقية، والملف الآن 26/26 ناجح.
**النتيجة النهائية بعد جولات التدقيق: `532 passed, 0 failed`**
مع استبعاد E2E وexternal (E2E 4/4 منفردة). بوابات الجودة كلها خضراء.
تحذير Sentry عند إنهاء العملية (pending events) غير مؤثر — `pytest` يخرج برقم 0.

---

## تحديث المرحلة 4 — بند 1 (إعادة الهجرات من الصفر)

بعد تأكيد عدم وجود نشر، استُبدلت سلسلة الـ 25 هجرة بـ **3 هجرات baseline نظيفة**
(جداول / فهارس / RLS) مولّدة من نماذج SQLAlchemy عبر `scripts/generate_baseline_migration.py`.
تم التحقق قبل الحذف: مقارنة مخطط قاعدة قديمة بمخطط الـ baseline أظهرت **0 فهارس مفقودة**
و19 فهرساً إضافياً من النماذج، و91/91 جدولاً بـ RLS بعد إضافة `impersonation_sessions`
التي كانت في النماذج بلا هجرة. النسخة الاحتياطية للهجرات القديمة محفوظة خارج المستودع
في `%TEMP%\orion_old_migrations_backup`. اختبارات الهجرات 22/22 ناجحة.

**بند 4 — تدقيق الفهارس والـ FK:** أُضيف `scripts/audit_schema.py` (+ فحص في CI بعد
تطبيق الهجرات + اختبار تكامل). كشف 5 جداول بلا فهرس `tenant_id` في المخطط القديم؛
أُصلحت كلها عبر النماذج والـ baseline. النتيجة على المخطط المنهجي: **0 مشاكل**،
وعلى المخطط القديم: >0 (فحص حقيقي لا شكلي). black/isort/flake8/RLS/طول الملفات خضراء.

**بند 3 — backup/restore:** أُضيف `scripts/verify_backup_restore.py` (يستخدم pg_dump/pg_restore
ويقارن عدد الجداول/السياسات/الصفوف/الإصدار). تجربة فعلية: `BACKUP_RESTORE_OK` مع
`(113, 91, 1, baseline_0003)` متطابق في المصدر والمستعاد.

> ملاحظة: تشغيل الاختبار الكامل الذي بدأ أثناء العمل على هذه البنود تعارض مع قاعدة
> الاختبار نفسها وأظهر أخطاءً غير حقيقية؛ سيُعاد تشغيله على قاعدة نظيفة بعد انتهاء
> التعديلات.

---

## تحديث المرحلة 5 — الجودة وCI

- نُقلت سكربتات التشخيص من الجذر إلى `scripts/diagnostics/` مع README يوضّح أنها
  يدوية فقط وغير مُجمّعة في CI.
- `pre-commit run --all-files` **أخضر بالكامل**. أُضيف hook محلي لتدقيق RLS.
- استُبعدت `.md/.html/.js` و`migrations/rls_v2_tables.sql` من hooks المسافات/نهاية
  الملف لأن المسافات في نهاية سطر Markdown فاصل إجباري — حُميَ من التعديل العارض.
- أُصلح مفتاحان مكرران في `scripts/coverage_manifest.yaml` (`storefront.py`، `i18n.py`)
  كانا يفشلان `check-yaml`.
- تحقق صحة `ci.yml`: 4 وظائف، كل مسارات السكربتات موجودة، boابات gitleaks/Bandit/
  RLS/schema audit مفعّلة. **ملاحظة:** التوافق مع Python 3.11 (CI) لم يُختبر محلياً
  (المثبّت 3.14 فقط).

---

## تحديث المرحلة 6 — المراقبة والتشغيل

- `ProductionConfig`: `LOG_JSON=True` و`SENTRY_ENVIRONMENT=production`، مع إضافة المتغيرات
  إلى `.env.production.example` و`.env.staging.example`.
- لوحة Grafana `Orion API Overview` وقواعد `OrionApiDown`/`OrionHigh5xxRate`/`OrionSlowP95`
  موجودة أصلاً ومُوصّلة عبر `docker-compose.staging.yml` — تم التحقق وليس الإنشاء.
- أُضيف `docs/RUNBOOK.md` (فحص، نسخ/استعادة، فشل دفع، Celery، تدقيق، تراجع، أسرار).
- أُضيف `PAYMENT_STUB_ALLOWED=false` و`PAYMENT_LIVE_CALLS_ENABLED=true` صراحةً في
  `docker-compose.prod.yml`.
- **فجوة معروفة:** لا يوجد تنبيه لطول طابور Celery لأن الخدمة لا تُصدّر مقياساً له بعد؛
  موثّقة بدل اختراع تنبيه وهمي.

---

## تحديث المرحلة 7 — إنتاجية الواجهات

- بُني Tailwind محلياً (`package.json` + `tailwind.config.js` + `npm run build:css`)
  إلى ملفي CSS بحجم 15KB لكلٍّ من المتجر والإدارة، واستُبدل CDN في 4 قوالب.
- أُزيل `cdn.tailwindcss.com` من CSP، مع 3 اختبارات تمنع عودته.
- `innerHTML` المتبقي كان في تعليقين فقط (لا استخدام فعلي) — تحقق ولا تعديل.
- أُضيف 3 اختبارات E2E بـ Playwright/Chromium (تصفّح المتجر، دخول أدمن المتجر،
  دخول أدمن المنصة) تحت marker `e2e` مُستبعد من CI الافتراضي — **3/3 ناجحة**.
- **إعادة التصميم الفاخرة نُفّذت:** `orion-theme.css` (كحلي/ذهبي، متغيّرات، بطاقات/أزرار/
  جداول/مدخلات، `focus-visible`، خصائص RTL منطقية) يُبنى ويُنسخ تلقائياً للمتجر والإدارة،
  وُوصّل بـ 4 قوالب أساسية، وطُبّق على الشريط الجانبي (35 رابطاً) وأزرار الدفع/الدخول.
- **RTL/WCAG:** أُضيف `scripts/audit_a11y.py` (فحص ثابت + CI + pre-commit)؛ أصلح 21 مدخلاً
  بلا تسمية قابلة للوصول → **0 مشاكل**. `focus-visible` و`prefers-reduced-motion` مُفعّلان.
- **تحقق بصري:** لقطات Playwright تُحفظ تلقائياً في `test-results/screenshots/` لكل مسار،
  مع فشل عند أي خطأ JavaScript في المتصفح — 3/3 ناجحة ورُوجعت اللقطات بصرياً.

---

## تحديث المرحلة 8 — الإطلاق والتسليم

- أُضيف `docs/LAUNCH-CHECKLIST.md` بمعايير Go/No-Go لكل بند (أمان، دفع، قاعدة، جودة،
  مراقبة، واجهات، نشر) مع توقيعات Tech Lead وOps.
- النشر الفعلي (staging → canary → production) **لا يمكن تنفيذه محلياً**؛ التوثيق جاهز
  ويُنفَّذ من قبل Ops في البيئة المستهدفة فقط.
- الاختبار الكامل النهائي: **532 passed / 0 failed** + E2E 4/4 + pre-commit أخضر
  + RLS 91/91 + schema 0 مشاكل + a11y 0 مشاكل + backup/restore OK.

---

## مراجعة الوكلاء العشرة (2026-11-20)
 عشرة وكلاء راجعوا الكود قراءةً فقط بنطاقات منفصلة، ثم عشرة وكلاء إضافيون وضعوا خططاً
عملية للباقي. أُصلح فوراً: ترتيب ربط RLS قبل
مصادقة المستخدم، اشتقاق مفتاح JWT، ابتلاع أخطاء المصادقة، الجلسة على API، مسح كوكيات
JWT عند الخروج، السر العام للـ webhooks، غياب معرّف الحدث، سياسة RLS التي سمحت بصفوف
NULL، IDOR في التطبيقات/الهدايا/المستودعات/الفئات، مصادقة المرتجعات، 8 مسارات API
بشرطة زائدة، وإيجابيات التدقيق الكاذبة.

الدفعة الثانية: خصم مخزون ذري + قيد فريد لمفتاح الطلب، منع الدفع المكرر (409)،
تحويل الاسترداد إلى حدث سالب بلا عمولة جديدة، قيود فريدة (بريد المستخدم، بوابة المستأجر،
singleton، تجاوزات الميزات)، توصيل بانر الانتحال، وإصلاح مسارات لوحة الإدارة.
الدفعة الثالثة (تحقق شامل 10 وكلاء): إصلاح بوابة التغطية (path_defaults)، تنسيق
backup بـ `-Fc`، مهمة انتهاء التجربة (فحص التاريخ + beat)، زر RMA، بوابة Beta،
وCSRF/refresh الخاصة بـ impersonation، حقول id/is_active في to_dict، أسرار PayPal/BNPL
بصيغة JSON قابلة للفك، منع إعادة دفع pending، تدقيق بمعرّف المستخدم الحقيقي،
وحذف قوالب SQL قديمة متعارضة مع سياسة الـ baseline.

الدفعة الرابعة (10 وكلاء تنفيذ): استرداد فعلي عبر المزوّد + جزئي، عكس عمولة + تسوية ليلية،
توقيع PayPal RSA، RBAC من جداول الصلاحيات، i18n ديناميكي في HTML، PDF عربي، أثر مالي للـ webhooks،
وتدفقات v2 موصولة (B2B/رصيد/هدايا/إشعارات). أُعيد توليد الـ baseline مرة واحدة.

الدفعة الخامسة (8 وكلاء): SSO/GDPR بتدفق حقيقي، محرك workflows بأحداث order.paid،
تقييم fraud آلياً عند order.created، صفحات CMS كاملة بعرض/تحرير/ترجمة، OAuth بتدفق
client_secret/token حقيقي، object storage للفواتير + عملات متعددة، وضرائب حسب العنوان.
أُعيد توليد الـ baseline مرة واحدة.

النظام الآن **كامل من ناحية الميزات المخططة**: لا توجد ميزة "مخزّنة بلا تدفق مستخدم" بعد.
ما يبقى خارج نطاق الكود: النشر الفعلي، حساب تاجر Stripe/PayPal، واختبار الحِمل.

---

## 0. المبادئ الحاكمة (غير قابلة للتفاوض)

1. **اقرأ قبل أن تكتب** (سياسة المشروع §0.1): قبل أي تعديل، اقرأ الملف + المستدعي + المستدعى + الاختبار + الـ migration المرتبطة.
2. **لا قفز بين المراحل:** كل مرحلة لها معيار قبول (DoD) MUST تتحقق قبل الانتقال للتي بعدها.
3. **مصدر الحقيقة = الكود + الاختبارات + CI**، وليس الـ README ولا خطة المشروع.
4. **PR واحد = هدف واحد** (bug / feature / refactor) + اختبار يغطيه + مرور الـ CI.
5. **لا أسرار في الكود أو الـ logs** — كل secret يأتي من `.env` / secrets manager.
6. **التراجع siempre posible:** كل migration يجب أن يكون له `downgrade` مُختبر.

---

## 1. خط الأساس (Baseline) — أرقام حقيقية من الكود

| العنصر | العدد الفعلي | الدليل |
|---|---|---|
| ملفات Python | 387 | `Get-ChildItem -Recurse -Filter *.py` |
| نماذج `db.Model` | 112 | `03-MODELS/**/*.py` |
| `create_table(` في الهجرات | 113 | `migrations/versions/*.py` |
| عبارات RLS (POLICY / ENABLE) | 43 | `migrations/versions/*.py` |
| نقاط API (decorators) | 100 | `05-API/v1/*.py` |
| Blueprints مسجّلة | 42 | `05-API/v1/routes.py:106-154` |
| ملفات اختبار | 68 | `tests/**/test_*.py` |
| قوالب أدمن / JS أدمن | 45 / 26 | `07-ADMIN/templates`, `07-ADMIN/static/js` |
| قوالب متجر / JS متجر | 10 / 6 | `06-STOREFRONT/themes/default` |
| استخدامات `SafeDOM` / `innerHTML` | 256 / 2 | `06-STOREFRONT`, `07-ADMIN` |
| بوابات دفع حقيقية | **0** (كلها stubs) | `04-SERVICES/integrations/payments/*.py` |

### ثغرات/فجوات مؤكدة من الكود (تُعالج في الخطة)
- `JWT_COOKIE_SECURE = False` في `orion/config.py:35` ولا يُرفع في `ProductionConfig` → كوكيز JWT تُرسل على HTTP في الإنتاج.
- `ENFORCE_HSTS` يُقرأ في `core/security_headers.py:24` لكنه **غير مُعرَّف** في أي config → HSTS لا يُفعّل إطلاقاً.
- `SECRET_KEY` افتراضي `"dev-only-change-me"` في `orion/config.py:30` ولا يُجبر الإنتاج على قيمة حقيقية.
- اختبارات العزل (`tests/security/test_tenant_isolation.py`, `test_catalog_isolation.py`) تمرّر `tenant_id` صراحةً ولا تختبر **رفض** الوصول المتبادل.
- `for bp in API_BLUEPRINTS: csrf.exempt(bp)` في `orion/app.py:82-83` → يجب مراجعة نموذج CSRF مقابل `JWT_COOKIE_CSRF_PROTECT`.
- `scripts/bootstrap_cli.py:8` ينصّ على أنه "المسار الوحيد" لإنشاء أدمن المنصة، لكن `05-API/v1/users.py:49-50` يسمح لمدير المنصة بإنشاء superuser عبر API → تناقض في نموذج الصلاحيات.
- README يعطي `admin@azadexa.com / Admin2026!` وغير موجود في أي كود → بيانات خاطئة.
- `psycopg2-binary`: `2.9.12` في `requirements.txt` مقابل `2.9.9` في `pyproject.toml`.
- لا يوجد `.env` فعلي؛ الاعتماد على القيم الافتراضية في `config.py`.
- Tailwind يُحمّل من CDN (`base.html`) → اعتماد على الإنترنت + CSP يسمح بالـ CDN صراحةً.

---

## 2. خريطة المراحل (المدة: 8 مراحل)

> التقديرات بالأيام لمطوّر واحد؛ قابلة للتعديل بعد المرحلة 0.

### المرحلة 0 — توحيد الحقيقة والبيئة (1–2 يوم) — `P0`
**الهدف:** أن يصبح الكود هو المرجع، والبيئة قابلة لإعادة الإنتاج من الصفر.
**المهام:**
- تصحيح `README.md`: الأرقام (112 نموذج/113 جدول/43 RLS)، حذف بيانات الأدمن الخاطئة واستبدالها بإرشادات `bootstrap_cli.py`.
- توحيد `psycopg2-binary` على إصدار واحد في `requirements.txt` و`pyproject.toml`.
- إنشاء `.env` محلي من `.env.example` + توليد `ENCRYPTION_KEY` و`SECRET_KEY`.
- تثبيت المتطلبات فعلياً (`pip install -r requirements.txt`) والتأكد من إقلاع `create_app()` بدون قاعدة بيانات (اختبار import/health).
- كتابة `ADR/0001-source-of-truth.md` يوضّح أن المستندات تتبع الكود.

**DoD:** `README` يطابق الكود؛ `python -c "from orion.app import create_app; ..."` ينجح؛ لا تناقض إصدارات.

---

### المرحلة 1 — سد فجوات الإنتاج الأمنية (2–3 أيام) — `P0` 🔴
**الهدف:** إغلاق الثغرات التي تمنع النشر على HTTPS.
**المهام:**
- `ProductionConfig` (و`Config` بشكل آمن بالdefault):
  - `JWT_COOKIE_SECURE = True`، `SESSION_COOKIE_SECURE = True`، `PREFERRED_URL_SCHEME = "https"`.
  - `ENFORCE_HSTS = True` في الإنتاج (أو إزالة الشرط وجعل HSTS مُفعّلاً دائماً في الإنتاج).
  - فشل صريح عند الإقلاع إذا `SECRET_KEY == "dev-only-change-me"` أو `JWT_SECRET_KEY`/`ENCRYPTION_KEY` فارغة في production (مثل فحص `DEBUG` الموجود أصلاً في `app.py:29-33`).
- مراجعة CSRF: توثيق أن API محمي بـ `JWT_COOKIE_CSRF_PROTECT=True` رغم `csrf.exempt`، أو تفعيل حماية صريحة للـ endpoints الحسّاسة (تغيير كلمة المرور، الدفع).
- توحيد مسار إنشاء superuser: إمّا السماح به عبر API بصلاحية صريحة موثّقة، أو منعه والاكتفاء بـ CLI.
- تحديد rate limit مخصّص على `/api/v1/auth/login` و`/admin/login` (منع brute-force) خارج الـ 300/ساعة العامة.
- إضافة secret scanning في CI (`gitleaks` أو `trufflehog`).

**الملفات:** `orion/config.py`، `orion/app.py`، `core/security_headers.py`، `core/rate_limit.py`، `05-API/v1/auth.py`، `.github/workflows/*`.

**DoD:** اختبار يفحص أن production يرفض الإقلاع بمفاتيح افتراضية؛ اختبار يتحقق من وجود `Secure` و`HSTS` في الهيدرات؛ CI يمرّ.

---

### المرحلة 2 — اختبارات العزل الحقيقية (2–3 أيام) — `P0` 🔴
**الهدف:** إثبات أن المستأجر لا يرى بيانات غيره **فعلياً**، لا فقط عبر تمرير `tenant_id`.
**المهام:**
- تحويل `tests/security/test_tenant_isolation.py` و`test_catalog_isolation.py` إلى اختبارات **سلبية**:
  - إنشاء مستأجرين A/B + مستخدم/منتج لكل منهما.
  - محاولة قراءة/تعديل/حذف بيانات B بصلاحية A (عبر API وعبر الـ service مباشرة) → توقّع `403/404` أو قائمة فارغة.
  - اختبار أن `set_config('app.tenant_id', ...)` يمنع التسريب حتى لو مرّر الكود `tenant_id` خاطئاً.
- تدقيق الـ 43 سياسة RLS: التأكد أن **كل جدول يحمل `tenant_id`** له سياسة (`CREATE POLICY`) و`ENABLE ROW LEVEL SECURITY`.
- التأكد من بقاء سياق RLS في مهام Celery (الـ `before_request` لا يعمل هناك) → إضافة helper يضبط `app.tenant_id` داخل كل مهمة.
- إضافة اختبار IDOR حقيقي على endpoints (مثلاً `/api/v1/products/<id>` لمستأجر آخر).

**DoD:** اختبارات سلبية تعمل على PostgreSQL حقيقي؛ تقرير يطابق "عدد الجداول التي تحمل tenant_id" مع "عدد جداول RLS"؛ لا `set_config` مفقود في مهام الخلفية.

---

### المرحلة 3 — الدفع الحقيقي (4–5 أيام) — `P0` 🔴 (حاسم للإنتاج)
**الهدف:** استبدال الـ stubs بتكامل حقيقي آمن.
**المهام:**
- تنفيذ `charge_stripe` / `charge_paypal` / `charge_palpay` / `charge_bnpl` داخل نفس الـ boundary الحالي بـ SDK رسمي أو HTTP موقّع.
- **مفاتيح idempotency** لكل عملية شحن (منع الخصم المزدوج عند إعادة المحاولة).
- التحقق من webhooks: Stripe/PayPal موجود (HMAC) → إضافة **منع replay** عبر timestamp (موجود جزئياً في `verification_service.py`) + تخزين معرّف الحدث.
- فصل `is_sandbox` عن slug المستأجر؛ بيانات الاعتماد تبقى مشفّرة (`credentials_encrypted` موجود في النموذج).
- Reconciliation: ربط `financial_event` / `commission_ledger` / `invoice` بمعرّف الدفع الحقيقي.
- اختبارات VCR (البنية موجودة في `tests/support/vcr_config.py`) + حسابات sandbox في CI secrets.

**DoD:** عملية دفع sandbox حقيقية تنشئ طلباً + حدثاً مالياً + فاتورة؛ إعادة نفس الطلب لا تخصم مرتين؛ webhook موقّع يُقبل ومزوّر يُرفض.

---

### المرحلة 4 — قاعدة البيانات والهجرات (2–3 أيام) — `P1`
**الهدف:** بناء قاعدة نظيفة من الصفر وترقية آمنة.
**المهام:**
- اختبار `flask db upgrade` من قاعدة فارغة حتى أحدث هجرة (24 ملف/113 create_table).
- مراجعة idempotency لكل الـ migrations (بعضها أُصلح في commits أخيرة مثل `1ac4481`).
- اختبار `downgrade` لكل هجرة (أو توثيق أي هجرة لا تدعمها).
- **تهيئة النظام (لا تُعدّ مرحلة مستقلة):** `PlatformSettingsService.ensure_seeded()` و
  `bootstrap_cli.py` و`seed_beta.py` هي كود تهيئة يُعامل كأي كود آخر — تُتحقق إعادة
  تشغيله الآمنة ضمن اختبارات الوحدة/التكامل، لا كـ "بذور بيانات". المتاجر العشرة
  تجريبية محلية/Staging فقط ولا تُحمّل في production.
- تدريب استعادة: `scripts/backup_db.ps1` → استعادة في قاعدة اختبار → مقارنة عدد الصفوف.
- فهرسة: التأكد من فهارس البحث والـ FK (بعضها أُضيف في `15d68a0`).

**DoD:** قاعدة جديدة تُنشأ بالكامل بـ أمر واحد؛ backup/restore يعمل؛ لا هجرة تفشل عند إعادة التطبيق.

---

### المرحلة 5 — الجودة والـ CI (2 أيام) — `P1`
**الهدف:** بوابات تمنع الكود المكسور من الدمج.
**المهام:**
- التشغيل الفعلي: `.\scripts\dev.ps1 test` على PostgreSQL حقيقي؛ التأكد أن تغطية ≥85% تمرّ فعلاً (الإعداد موجود في `pyproject.toml:62` لكنه لم يُشغّل بعد).
- إضافة `bandit` (SAST) و`pip-audit` (موجود) و`check_migrations.py` و`check_file_length.py` إلى نفس الـ workflow.
- إزالة ملفات debug المؤقتة بالجذر (`debug_health.py`, `debug_imp.py`, `probe_rls.py`) أو نقلها إلى `scripts/diagnostics/` مع توثيق.
- تثبيت pre-commit محلياً وتشغيله على كل الملفات مرة واحدة.

**DoD:** CI أخضر من صفر؛ التغطية ≥85%؛ لا ملفات debug في الجذر.

---

### المرحلة 6 — المراقبة والتشغيل (2–3 أيام) — `P1`
**الهدف:** معرفة أي عطل قبل المستخدم.
**المهام:**
- تفعيل Sentry بـ DSN حقيقي في staging/production (المتغير موجود لكن فارغ).
- Prometheus + Grafana (موجودة في `docker-compose.staging.yml`) — اللوحة وقواعد التنبيه فُعّلت فعلاً في `01-FOUNDATION/staging/`؛ المتبقي توفير خدمة Prometheus/Grafana وAlertmanager في production.
- تحويل `LOG_JSON=true` في production + ضمان عدم تسجيل الأسرار (راجع `core/logging_config.py`).
- كتابة runbooks: النسخ الاحتياطي، استعادة، إعادة تشغيل Celery، التعامل مع فشل الدفع.
- تمكين HSTS فعلياً (مرتبط بالمرحلة 1).

**DoD:** تنبيه مُختبر يصل عند إيقاف Redis أو Postgres؛ لوحة تعرض `/health` و`/ready`؛ runbook مكتوب ومُجرّب.

---

### المرحلة 7 — إنتاجية الواجهات (3–4 أيام) — `P2`
**الهدف:** واجهة مستقرة وسريعة بدون اعتماد خارجي.
**المهام:**
- استبدال `https://cdn.tailwindcss.com` في `06-STOREFRONT/themes/default/templates/base.html` بـ CSS مبني محلياً (أو self-hosted) → إزالة الاستثناء من CSP في `core/security_headers.py:19-21`.
- معالجة الـ 2 استخدامات المتبقية لـ `innerHTML` عبر `SafeDOM`.
- إضافة اختبارات E2E (Playwright) لأهم 3 مسارات: تصفّح/سلة/دفع، تسجيل دخول أدمن المتجر، لوحة المنصة.
- تحسين RTL في `static/css/rtl.css` واختبار Accessibility (الخطة تذكر WCAG).

**DoD:** الموقع يعمل بدون إنترنت خارجي؛ صفر `innerHTML`؛ 3 مسارات E2E خضراء.

---

### المرحلة 8 — الإطلاق والتسليم (2 يوم) — `P1`
**الهدف:** نشر آمن قابل للتراجع.
**المهام:**
- قائمة تحقق الإطلاق (Go/No-Go): مفاتيح، نسخة احتياطية، RLS، دفع sandbox، مراقبة، DNS/Subdomain، `BETA_MODE`.
- نشر staging → canary (نسبة صغيرة عبر `rollout_percent` migrations الموجودة) → production.
- خطة تراجع مكتوبة ومُختبرة (`docker-prod-down` + استعادة DB).
- تحديث `README.md` النهائي + `docs/RUNBOOK.md` + `ADR/`.

**DoD:** نشر تجريبي ناجح + تراجع مُختبر + توثيق محدّث.

---

## 3. جدول الأولويات

| الأولوية | المراحل | لماذا |
|---|---|---|
| `P0` 🔴 | 0، 1، 2، 3 | تمنع نشر غير آمن (كوكيز غير محمية، تسريب بيانات، دفع وهمي) |
| `P1` 🟠 | 4، 5، 6، 8 | تضمن الاستقرار والقدرة على الصيانة والاستعادة |
| `P2` 🟡 | 7 | تحسين تجربة المستخدم وتقليل الاعتماد الخارجي |

---

## 4. أبدأ من أين؟ (أول 3 أيام فعلياً)

1. **اليوم 1 صباحاً:** أنشئ `.env` من `.env.example`، ثبّت الإصدار الموحّد لـ `psycopg2`، شغّل `python -m pytest --collect-only` للتأكد أن كل الاختبارات تُجمع بدون أخطاء.
2. **اليوم 1 ظهراً:** صحّح `README.md` (الأرقام + بيانات الأدمن) — سريع ويمنع تضليل أي مطور جديد.
3. **اليوم 2:** المرحلة 1 — أضف فحص المفاتيح الافتراضية في `ProductionConfig` و`JWT_COOKIE_SECURE=True` + اختبار لهما.
4. **اليوم 3:** حوّل اختبارَي العزل إلى اختبارات سلبية حقيقية (المرحلة 2).

> لا تبدأ بوابات الدفع (المرحلة 3) قبل إغلاق 1 و2 — الدفع بدون عزل بيانات ومصادقة آمنة = خطر مضاعف.

---

## 5. تعريف "جاهز للإنتاج" (Production-Ready Checklist)

- [ ] الإقلاع يفشل بأي secret افتراضي أو فارغ في production.
- [ ] كل كوكيز حسّاسة `Secure` + `HttpOnly` + `SameSite` وHSTS مُفعّل.
- [ ] كل جدول بـ `tenant_id` محمي بـ RLS + اختبار رفض سلبي + سياق في Celery.
- [ ] عملية دفع حقيقية (sandbox) بـ idempotency + webhook موقّع بمكافحة replay.
- [ ] قاعدة تُبنى من الصفر بأمر واحد + backup/restore مُختبر.
- [ ] CI أخضر: lint + pytest(≥85%) + migration check + pip-audit + SAST + secret scan.
- [ ] `/health` و`/ready` + تنبيه مُختبر + runbook.
- [ ] لا CDN خارجي، صفر `innerHTML`، 3 مسارات E2E خضراء.
- [ ] README وADR وRUNBOOK مطابقة للكود.

---

## 6. قياس التقدّم (KPIs أسبوعية)

| المؤشر | الهدف |
|---|---|
| اختبارات عزل سلبية | من 0 → ≥5 |
| جداول بـ RLS / جداول بـ tenant_id | 100% |
| تكاملات دفع حقيقية | من 0 → 4 |
| التغطية | ≥85% فعلياً (مُشغّلة) |
| thresholds أمنية مفتوحة (P0) | 0 |
| زمن استعادة backup | مُقاس وموثّق |

---

### ملاحظة ختامية
هذه الخطة **تتبع الكود**، لذا قد تتغير تفاصيلها بعد المرحلة 0 إذا ظهرت فجوات جديدة أثناء
تشغيل الاختبارات فعلياً على PostgreSQL. أي تغيير في الترتيب يجب تسجيله في `ADR/`.
