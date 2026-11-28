# قائمة الإطلاق — Go / No-Go

> لا يُنتقل إلى production إلا إذا كانت **كل** البنود أدناه خضراء.
> أي بند أحمر = NO-GO. الوثيقة مرتبطة بـ `PRODUCTION-READINESS-PLAN.md` و`RUNBOOK.md`.

## 1. الأمان (P0)
- [ ] `ProductionConfig` يرفض `SECRET_KEY` الافتراضي والمفاتيح الفارغة — `pytest tests/security/test_production_config.py`
- [ ] كوكيز `Secure` + `HttpOnly` + `SameSite` وHSTS مُفعّل — نفس الاختبار
- [ ] شهادة TLSwildcard في `infrastructure/certs/` وخدمة `nginx` تنهي TLS على 443 — `docs/RUNBOOK.md §0.1`
- [ ] RLS على **كل** الجداول التي تحمل `tenant_id` — `python scripts/audit_rls.py --check`
- [ ] دور التطبيق **ليس superuser** بعد النشر — `python scripts/verify_deployment_rls.py --check` (0 مشاكل)
- [ ] FK سليمة وفهارس `tenant_id` موجودة — `python scripts/audit_schema.py --check`
- [ ] اختبارات العزل السلبية ناجحة — `pytest tests/security -m "not e2e"`
- [ ] توقيع PayPal يرفض الغائب/المزوّر وstripe لديه حماية replay

## 2. الدفع
- [ ] `PAYMENT_STUB_ALLOWED=false` و`PAYMENT_LIVE_CALLS_ENABLED=true` في production
- [ ] بيانات اعتماد المزوّد مُشفّرة (`credentials_encrypted`) وليست في الكود
- [ ] عملية sandbox حقيقية تنشئ طلباً + حدثاً مالياً + فاتورة
- [ ] idempotency key يُرسل لكل عملية شحن — `pytest tests/services/test_payment_live_boundary.py`
- [ ] webhook موقّع يُقبل ومزوّر يُرفض — `pytest tests/unit/test_webhook*`

## 3. قاعدة البيانات
- [ ] بناء المخطط من الصفر: `flask db upgrade` على قاعدة فارغة → `schema_drift_parity_0009` (أحدث هجرة / head)
- [ ] كل هجرة قابلة للتراجع خطوة بخطوة — `pytest tests/integration/test_migration_downgrades.py`
- [ ] النسخ والاستعادة مُختبرة — `python scripts/verify_backup_restore.py`
- [ ] لا يوجد `.env` أو secret مُلتزم في git

## 4. الجودة
- [ ] `python -m pre_commit run --all-files` أخضر
- [ ] `pytest -m "not external and not e2e"` بالكامل أخضر + تغطية ≥99%
- [ ] `pip-audit --strict` وBandit وgitleaks في CI

## 5. المراقبة
- [ ] `/health` و`/ready` و`/metrics` تستجيب
- [ ] Sentry مُهيّأ بـ `SENTRY_DSN` و`SENTRY_ENVIRONMENT=production`
- [ ] `LOG_JSON=true`
- [ ] لوحة Grafana وقواعد التنبيه مُحمّلة في staging
- [ ] `RUNBOOK.md` مُراجَع من قبل الشخص المناوب

## 6. الواجهات
- [ ] لا CDN خارجي (CSS محلي مبني) — `pytest tests/ui`
- [ ] صفر `innerHTML`، 4 مسارات E2E خضراء — `pytest tests/e2e -m e2e`
- [ ] RTL وصفحة الوصولية تعملان

## 7. النشر والتسليم
- [ ] staging ناجح → canary بنسبة صغيرة → production
- [ ] خطة تراجع مُختبرة (إيقاف + استعادة + إعادة نشر)
- [ ] DNS/Subdomains و`BETA_MODE` مُراجَعة
- [ ] `README.md` و`ADR/` و`RUNBOOK.md` محدّثة

---

### التوقيع
| الدور | الاسم | التاريخ | قرار |
|---|---|---|---|
| Tech Lead | | | GO / NO-GO |
| Ops | | | GO / NO-GO |
