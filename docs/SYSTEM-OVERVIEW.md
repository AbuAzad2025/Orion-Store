# Orion / Azadexa — نظرة نظامية مبنية على الكود الفعلي

> هذا الوصف مُستخرج من قراءة الكود والتحقق منه (app factory، الـ blueprints، النماذج،
> الخدمات، القوالب، سكربتات التدقيق). الأرقام مُقاسة من الملفات، لا من خطة المشروع.

---

## 1. ما هو النظام؟

**Azadexa** منصة تجارة إلكترونية SaaS متعددة المستأجرين (Multi-tenant). محركها الداخلي
يُسمّى **Orion** (كود فقط، لا يظهر للمستخدم). منصة واحدة تشغّل متاجر كثيرة، لكل متجر
بياناته وواجهته ومديروه، مع لوحة تحكم مركزية للمنصة.

- **الخلفية:** Python 3.11+ / Flask 3.1 / SQLAlchemy / PostgreSQL / Redis / Celery.
- **الواجهات:** متجر (Storefront) + لوحة إدارة للمستأجر + لوحة إدارة للمنصة.
- **النمط:** Monolith modular — طبقات واضحة لكن بنشر واحد.

---

## 2. تدفّق الطلب (Request Flow)

```
HTTP Request
  → create_app()        : orion/app.py — تهيئة db/migrate/jwt/csrf/limiter/celery
  → register_middleware : حلّ المستأجر (header/subdomain/domain/query)
                          ربط g.user + g.role + g.is_platform_admin
                          set_config('app.tenant_id', ...) + ('app.is_platform_admin', ...)
  → guard_beta_program  : بوابة Beta اختيارية
  → guard_admin_html    : حماية صفحات /admin/*
  → Blueprint handler   : 05-API/v1/* أو 06-STOREFRONT أو 07-ADMIN
  → Service             : 04-SERVICES/* (منطق الأعمال)
  → Model               : 03-MODELS/* → PostgreSQL مع RLS
  → JSON / HTML         : استجابة + هيدرات أمان + مقاييس Prometheus
```

نقاط الدخول: `/health`، `/ready`، `/metrics` (Prometheus)، `/api/v1/*`،
`/webhooks/*`، `/admin/*`، وواجهات المتجر `/`.

---

## 3. الطبقات (من الكود)

| المجلد | الدور | حجم مُقاس |
|---|---|---|
| `02-CORE/core` | أمان، JWT، CSRF، RLS middleware، rate limit، مراقبة، تسجيل، crypto | 21 ملفًا |
| `02-CORE/orion` | app factory، config، extensions، celery، wsgi | 6 ملفات |
| `03-MODELS` | 112 صنف `db.Model` | 99 ملفًا |
| `04-SERVICES` | منطق الأعمال (96 ملفًا) | auth/tenant/catalog/order/payment/… |
| `05-API` | ~100 نقطة API عبر blueprint | 50 ملفًا |
| `06-STOREFRONT` | 13 قالبًا + JS + ثيم | متجر العميل |
| `07-ADMIN` | 45 قالبًا + 27 JS | لوحتا المستأجر والمنصة |
| `migrations/versions` | 3 هجرات baseline | جداول/فهارس/RLS |

قاعدة البيانات: **113 جدولاً** بعد التهجير (منها `alembic_version`)، و**101 جدولاً**
لديها سياسة RLS.

---

## 4. تعدد المستأجرين والعزل (أهم ما في النظام)

- **حلّ المستأجر** في `core/middleware.py` يقرأ (بالترتيب):
  1. هيدر `X-Tenant-ID` (public_id uuid أو slug).
  2. النطاق الفرعي `slug.local.azadexa` أو `domain`.
  3. `custom_domain`.
  4. في وضع التطوير فقط: `?tenant_slug=...` أو الافتراضي `beta-ramallah`.
- **سياق قاعدة البيانات**: `set_config('app.tenant_id', tid, true)` و
  `set_config('app.is_platform_admin', flag, true)` داخل نفس الـ transaction.
- **RLS**: كل جدول يحمل `tenant_id` لديه سياسة `tenant_isolation` تسمح بصفوف
  المستأجر الحالي أو صفوف NULL (مدير المنصة يمرّ عبر `app.is_platform_admin=true`).
- **مهام Celery**: لا يوجد request middleware؛ لذلك `bind_task_rls_context()` يُضبط
  صراحةً في `ContextTask`، والمهام الخاصة بمستأجر تستدعيها صراحةً.
- **اختبارات العزل**: محاولات قراءة/تعديل/حذف بيانات مستأجر آخر عبر API تُرفض (403/404).

---

## 5. المصادقة والصلاحيات

- **JWT** عبر `flask-jwt-extended`، موقعان: cookies + headers، مع `HttpOnly` وCSRF.
- **Three roles**: `platform_admin` (superuser بلا tenant_id)، `tenant_admin`، `customer`.
- **دوال حماية**: `require_platform_admin()`، `require_tenant_admin()`،
  `require_tenant_context()`، و`guard_admin_html` للصفحات.
- **تسجيل أدمن المنصة**: عبر `scripts/bootstrap_cli.py` تفاعلياً فقط (لا كلمة مرور
  ثابتة في الكود). المتاجر التجريبية العشرة تُنشأ من `scripts/seed_beta.py`.
- **انتحال هوية (Impersonation)**: مدير المنصة يمكنه انتحال مدير متجر لمدة محددة
  (`platform_models/impersonation_session.py`) مع تسجيل ذلك.
- **حماية إضافية**: rate limiting (10/دقيقة للّوجن، 5/دقيقة لـ admin login، 300/ساعة
  افتراضياً)، هيدرات أمان، CSRF، بوابة Beta، ومنع replay للـ webhooks.

---

## 6. الوحدات الوظيفية (من النماذج والـ APIs)

| المجال | ما هو مُنفّذ فعلياً |
|---|---|
| **الكتالوج** | منتجات، تصنيفات، ماركات، metafields، حزم (bundles)، ضرائب، عملات، رصيد متجر |
| **الطلبات** | سلة، طلبات، عناصر، أحداث، مسودات، مرتجعات/استبدال (RMA)، BOPIS، OMS/مستودعات/نقل مخزون |
| **العملاء** | مستخدمون، أدوار/صلاحيات، مجموعات B2B وقوائم أسعار، عضوية/اشتراكات، إشعارات مخزون |
| **خدمة ذاتية للزبون** | `/account`: الطلبات، GDPR export/delete، الاشتراكات، رصيد المتجر، طلبات عروض B2B، قوائم الهدايا |
| **الدفع** | Stripe Connect، PayPal، PalPay، BNPL (Tabby/Tamara)،COD، تسوية وعمولات وفواتير وأحداث مالية |
| **الخصومات** | كوبونات/vouchers، خصم شحن مجاني، رصيد متجر |
| **المحتوى** | i18n (لغات/ترجمات/صفحات CMS)، CMS، قوالب مستندات/PDF، schema markup |
| **المنصة** | إعدادات المنصة، مستأجرون، مديرون، تدقيق (audit logs)، تسوية مالية، تقارير |
| **التطبيقات والقنوات** | منصة تطبيقات، OAuth apps، webhooks، دروبشيب، مسوقون (affiliates)، هدايا، دردشة حية |
| **الامتثال والجودة** | فرaud rules/reviews، consent records،طلبات بيانات، SSO، إمكانية وصول، البحث/merchandising، سير عمل |
| **المراقبة** | /health و/ready و/metrics، Sentry، Grafana، تنبيهات، LOG_JSON |

> **أسعار الصرف**: مبدّل العملة في المتجر يستخدم أسعاراً حقيقية من
> `exchangerate-api` (`CURRENCY_RATE_PROVIDER_URL`)، تُخزَّن في `currency_rates`
> لمدة `CURRENCY_RATE_TTL_SECONDS` كـ fallback دون اتصال. عند تغيير عملة العرض
> يُضاف `CURRENCY_FX_MARKUP_PERCENT` (افتراضي 3%) فوق سعر الصرف؛ الفوتر يعرض
> السعر الأساسي والسعر بعد الفرق ومصدره وعلامة "مباشر". في الاختبارات
> `CURRENCY_LIVE_RATES=false` و`CURRENCY_FX_MARKUP_PERCENT=0` لضمان determinism.

---

## 6.0 المستودع لكل مستأجر (مصدر واحد للحساب والمراقبة)
- **الكتالوج/المخزون القابل للبيع** هو جدول `products` بعمود `tenant_id`، محمي بـ RLS:
  مدير المتجر يضيف/يعدّل منتجاته من لوحته، والمتجر يقرأ **نفس الجدول** عبر
  `ProductService.list_published(tenant.id)` — لا نسخ ولا مزامنة يدوية للواجهة.
- يوجد أيضاً نظام OMS (`warehouses`, `inventory_levels`) لكل مستأجر. كان غير متصل بالكتالوج؛
  تم توحيده: عند إنشاء منتج أو تغيير كميته أو بعد كل checkout تُزامَن الكمية تلقائياً
  مع «المستودع الرئيسي» (`code=main`) الذي يُنشأ تلقائياً مرة واحدة لكل مستأجر.
- لذلك: `products.quantity` = `inventory_levels.quantity` دائماً (مُختبر آلياً)،
  ويمكن الحساب والمراقبة والتدقيق من أيٍّ منهما بثقة. فشل المزامنة يُسجَّل تحذيراً
  ولا يمنع تعديل الكتالوج.
- **الأسعار التاريخية**: عند كل طلب تُحفظ نسخة من السعر واسم المنتج داخل `order_items`
  (`unit_price` / `total_price`)، والفاتورة تستخدم `order.total`. لذلك تعديل سعر المنتج
  لاحقاً **لا يغيّر** الطلبات المباعة سابقاً — مُثبت باختبار `test_price_history.py`.

## 6.0.1 إدارة المنتجات من لوحة المتجر
- صفحة `/admin/store/products` (تظهر في القائمة الجانبية) تدير المنتجات بالكامل:
  إضافة، تعديل، حذف، تحديث، تحديد تصنيف، كمية/سعر/SKU، نشر/إخفاء، تمييز.
- حقل `image_url` للمنتج (مُضاف إلى النموذج والـ baseline والـ API) مع عرض الصورة
  في بطاقة المنتج وصفحته، ورسالة بديلة عند غيابها. الروابط المقبولة http(s) أو مسار محلي فقط
  (يُرفض `javascript:`).
- كل العمليات تمر عبر `/api/v1/products/*` بصلاحية `require_tenant_admin` وعزل RLS.

## 6.0.2 ميزات مُكتملة بدفعة الوكلاء العشرة (2026-11-21)
- **استرداد فعلي عبر المزوّد** (Stripe/PayPal/PalPay/BNPL) مع مبلغ جزئي و`provider_refund_id`
  ومنع استرداد مكرر؛ الوضع المحلي يبقى stubاً مجانياً.
- **عكس العمولة محاسبياً**: قيد `debit` مرتبط بـ `reverses_ledger_id`، idempotent،
  مع مهمة تسوية ليلية لكل مستأجر على حدة (`CELERY beat`).
- **توقيع PayPal حقيقي**: RSA-SHA256 عبر شهادة `paypal-cert-url` مع allowlist في production،
  وHMAC محلياً؛ فحص `crc32(body)`.
- **RBAC فعلي**: `user_has_permission` يستعلي من `user_roles → role_permissions → permissions`
  مع عزل المستأجر، superuser bypass، ونقطة إسناد دور.
- **i18n في HTML**: `lang/dir` ديناميكيان per-request (ar/he⇒rtl، en/fr⇒ltr)،
  وفحص a11y يتبع اللغة بدل فرض العربية.
- **PDF عربي**: خط Unicode + HarfBuzz، لا ASCII stripping، مع `ToUnicode`.
- **Webhooks بأثر مالي**: تحقق → منع replay → تحويل الطلب/الدفع + أحداث مالية + عمولة + استرداد.
- **تدفقات v2 موصولة**: تسعير B2B في السلة، خصم رصيد المتجر عند checkout، عناصر قوائم الهدايا،
  وإشعار إعادة توفر المخزون.

## 6.1 البيع عبر واتساب (بدون حساب بطاقات)
- لكل متجر رقم تواصل يُضبط من `/admin/store/contact` عبر `GET/PUT /api/v1/tenant/contact`
  (مدير المتجر فقط، مع تحقق من صيغة الرقم).
- المتجر يعرض زر "واتساب" للتواصل وزر "اطلب عبر واتساب" في بطاقة المنتج وصفحته،
  عبر رابط مجاني `https://wa.me/<رقم>?text=...` — **لا يحتاج WhatsApp Business API ولا دفع**.
- صفحة السلة تعرض **خيارين جنب بعض**: «إتمام الشراء» (الدفع الإلكتروني، يبقى دائماً متاحاً)
  و«إرسال الطلب عبر واتساب». الخيار الثاني يبني الرسالة **خادمياً** من محتوى السلة الحقيقي
  (`POST /api/v1/store/cart/<token>/whatsapp-message`) مع اسم المنتج والكمية والأسعار
  والإجمالي والاسم/الملاحظات الاختيارية — لا يمكن التلاعب بالأسعار من المتصفح.
- الأزرار تظهر فقط إذا ضُبط رقم المتجر؛ ولا يُنشأ طلب في قاعدة البيانات بهذا المسار
  (المتجر يتابع الطلب يدوياً عبر واتساب).

## 6.2 تحسينات أمنية لاحقة
- طلبات الزبون مرتبطة بمعرّف الحساب `user_id` (وليس بالإيميل فقط)، مع توافق رجعي
  للطلبات القديمة عبر `customer_email` عندما يكون `user_id` فارغاً. الزبون المسجّل
  يرى طلباته فقط، والضيوف لا يرون طلبات بعضهم.
- `scripts/verify_deployment_rls.py` يُشغَّل بعد كل نشر للتأكد أن دور التطبيق ليس
  superuser ولا مالك الجداول (وإلا RLS مُعطَّل) — أُضيف إلى RUNBOOK وقائمة الإطلاق.
- مهام Celery تُثبّت سياق RLS تلقائياً (`bind_task_rls_context`) مع اختبار آلي.

## 7. الدفع (تفاصيل مهمة)

- طبقة `integrations/payments/_http.py` توحّد: فك تشفير الاعتماد (Fernet)،
  `Idempotency-Key` ثابت لكل طلب، timeout， وتحويل أخطاء الشبكة إلى `success=False`.
- **في التطوير/الاختبار**: `PAYMENT_STUB_ALLOWED=true` و`PAYMENT_LIVE_CALLS_ENABLED=false`
  → معرّفات وهمية محلية، بلا إنترنت، بلا تكلفة.
- **في الإنتاج**: `PAYMENT_LIVE_CALLS_ENABLED=true` → استدعاء فعلي:
  - Stripe: `/v1/payment_intents` مع Bearer key.
  - PayPal: OAuth ثم `/v2/checkout/orders` ثم capture.
  - PalPay/BNPL: endpoints قابلة للضبط عبر `config.api_base_url` أو env.
  - غياب الاعتماد في production = فشل صريح، لا دفع وهمي.
- **Webhooks**: توقيع HMAC (Stripe/PayPal/BNPL) + فحص عمر الرسالة + منع replay
  عبر Redis `SET NX`، مع bootstrap لسياق المستأجر قبل المعالجة.

---

## 8. الفرونت إند

- **بناء محلي**: Tailwind 3.4.19 يُبنى عبر `npm run build:css` إلى `tailwind.css`
  (15KB) + نسخ `orion-theme.css` (متغيّرات التصميم) إلى مجلدَي static. **لا CDN**، CSP يمنع المصدر الخارجي.
- **نظام التصميم**: كحلي/ذهبي، RTL-first بخصائص منطقية، `focus-visible`،
  `prefers-reduced-motion`، تباين WCAG AA مُدقق آلياً (0 مخالفة).
- **مكوّنات**: `orion-card`، `orion-stat`، `orion-btn(-gold)`، `orion-table`،
  `orion-nav-link`، `orion-toast`، `orion-skeleton`، `orion-topbar`، `orion-skip-link`.
- **الصفحات**: متجر (رئيسية/منتج/تصنيف/سلة/دفع/حساب) + لوحة مستأجر (35+ شاشة) +
  لوحة منصة + صفحة معاينة مكوّنات `/admin/store/ui-kit`.
- **JS**: `SafeDOM` (لا `innerHTML`)، `OrionAPI` (timeout/dedupe/أخطاء)،
  `OrionUI` (toast/loading/confirm)، و22 ملف JS تستخدم العميل الموحّد.
- **اختبارات بصرية**: Playwright/Chromium، 4 مسارات + لقطات شاشة،
  فشل عند أي خطأ JS في المتصفح.

---

## 9. الخلفية والتشغيل

- **Celery** مع Redis broker و`task_always_eager` في الاختبار؛ مهام إشعارات البريد
  وفحص انتهاء التجربة.
- **المراقبة**: Counter/Histogram لـ `/metrics`، لوحة Grafana، قواعد تنبيه
  (API down، نسبة 5xx، p95 latency)، Sentry عند توفر DSN، `LOG_JSON` في production.
- **النسخ الاحتياطي**: `scripts/backup_db.ps1` (Docker) + `scripts/verify_backup_restore.py`
  لتجربة pg_dump/pg_restore ومقارنة اللقطات.
- **الوثائق التشغيلية**: `docs/RUNBOOK.md`، `docs/LAUNCH-CHECKLIST.md`،
  `docs/UI-DESIGN-SYSTEM.md`، `docs/UI-BACKEND-INTEGRATION-PLAN.md`.

---

## 10. الجودة والاختبارات

- **575 اختباراً** على PostgreSQL حقيقي (وظيفة E2E تستخدم SQLite معزولاً) + 4 اختبارات E2E، تغطية ≥99% مفروضة.
- **pre-commit/CI**: black، isort، flake8، YAML، طول الملفات، pip-audit، Bandit،
  gitleaks، تدقيق RLS، تدقيق schema/FK، تدقيق a11y/RTL، تدقيق مراجع API/الواجهة،
  تدقيق تباين الألوان.
- **الهجرات**: 3 ملفات baseline (جداول/فهارس/RLS)، قابلة للتراجع خطوة بخطوة،
  وتدقيق آلي أن كل جدول بـ `tenant_id` له سياسة RLS وفهرس.

---

## 11. حدود معروفة (بصراحة)

- بوابات الدفع مُنفّذة فعلياً لكن **لم تُختبر بحسابات تاجر حقيقية** (sandbox فقط).
- لم يُنشر على staging/production؛ TLS وDNS وsubdomains لم تُختبر.
- CI يستخدم Python 3.11 بينما التحقق المحلي كان على 3.14.
- سُدّت فجوة تنبيه Celery: `orion_celery_worker_up` و`orion_celery_queue_depth` مع قواعد `OrionCeleryWorkerDown` / `OrionCeleryQueueDepthHigh`؛ وأُضيف `OrionBackupStale` لعمر نبض النسخ.
- التدقيق البصري آلي/لقات، لا تدقيق human WCAG كامل.

---

## 12. التشغيل المحلي السريع

```powershell
npm install
npm run build:css
.\scripts\dev.ps1 setup-local     # PostgreSQL + Redis + .env + migrate + seed
.\scripts\dev.ps1 run             # http://127.0.0.1:5000
.\scripts\dev.ps1 test            # pytest + coverage ≥99%
```

المرجع الأعلى لهذا الوصف هو الكود نفسه؛ أي تعارض مع `ORION-Project-Plan-Report.md`
يُحسم لمصلحة الملفات المذكورة أعلاه (انظر `ADR/0001-source-of-truth.md`).
