# Orion / Azadexa — دليل التشغيل (RUNBOOK)

> النسخة 1.0 — 2026-11-20. يُحدَّث هذا الملف عند كل تغيير في الإجراءات.
> **القاعدة الذهبية:** لا تنفّذ إجراءً في production ولم تجرّبه في staging أولاً.

---

## 0. قبل أي تدخل — فحص سريع

```powershell
.\scripts\dev.ps1 launch-verify                 # /health + /ready
curl http://127.0.0.1:5000/health
curl http://127.0.0.1:5000/ready                # database + redis
curl http://127.0.0.1:5000/metrics              # Prometheus (غير مُفعّل في TESTING)
```

- `/ready` يُعيد 503 إذا تعذّر الوصول لـ PostgreSQL.
- `/health` يُظهر حالة Redis (`ping_redis`).

### 0.1 TLS / reverse proxy (production)
 compose الإنتاج لا يكشف المنفذ 5000 مباشرة؛ خدمة `nginx` تنهي TLS على
 المنفذين 80/443 وتُعيد التوجيه إلى `orion-api:5000` على الشبكة الداخلية.
 قبل التشغيل ضع الشهادة في `01-FOUNDATION/infrastructure/certs/`
 (`fullchain.pem` + `privkey.pem`، راجع `certs/README.md`)، ثم:

```powershell
docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml up -d --build
curl -I https://<tenant>.azadexa.com/health        # يجب 200 + HSTS
curl -I http://<tenant>.azadexa.com/               # 301 إلى HTTPS
```

 التطبيق يثق بـ `X-Forwarded-*` عبر ProxyFix في بيئة production فقط، لذا
 كوكيز `Secure` وإعادة التوجيه تعمل بشكل صحيح خلف البروكسي.

---

## 1. النسخ الاحتياطي (Backup)

### Staging / Production (Docker)
```powershell
.\scripts\backup_db.ps1 -ComposeFile 01-FOUNDATION/infrastructure/docker-compose.staging.yml -EnvFile .env.staging
```
الملف يُكتب في `backups/orion-pg-<timestamp>.sql`.

### تحقق دوري من آلية النسخ/الاستعادة (drill)
```powershell
$env:PYTHONPATH="02-CORE;03-MODELS;04-SERVICES;05-API;06-STOREFRONT;07-ADMIN"
$env:FLASK_APP="orion.wsgi:app"; $env:FLASK_ENV="development"
python scripts/verify_backup_restore.py --pg-bin "C:\Program Files\PostgreSQL\18\bin"
```
**النتيجة المتوقعة:** `BACKUP_RESTORE_OK` وتطابق `(عدد الجداول, السياسات, الصفوف, إصدار Alembic)`.
يُنشئ السكربت قاعدتين مؤقتتين (`orion_drill_src` / `orion_drill_restored`) ويحذفهما تلقائياً.

---

## 2. الاستعادة (Restore)

1. أوقف كتابة الطلبات (مثال: أوقف الـ webhook أو ضع المنصة في وضع الصيانة).
2. أنشئ نسخة احتياطية **جديدة** قبل الاستعادة (حتى لو كانت الحالية معطوبة).
3. استعد داخل حاوية Postgres:
```powershell
docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml `
  exec -T postgres pg_restore --clean --if-exists -U azadexa -d azadexa_prod < backup.dump
```
4. تحقق: `python scripts/audit_rls.py --check` و `python scripts/audit_schema.py --check`
   (مع `DATABASE_URL` يشير لقاعدة الإنتاج) ثم `.\scripts\dev.ps1 launch-verify`.

> لا تُعدّل بيانات الإنتاج مباشرةً؛ attempted fixes تتم عبر migrations أو أدوات مُراجَعة.

---

## 3. فشل الدفع

1. راجع `/metrics`: هل ارتفع معدل 5xx؟ (لوحة Grafana `Orion API Overview`).
2. تحقق من أن `PAYMENT_LIVE_CALLS_ENABLED=true` و`PAYMENT_STUB_ALLOWED=false` في production.
3. تأكد من فك تشفير بيانات الاعتماد (`credentials_encrypted`) وعدم انتهاء صلاحية مفاتيح المزوّد.
4. راجع webhooks: التوقيع + `WEBHOOK_MAX_AGE_SECONDS` + منع replay عبر Redis.
5. إذا تعذّر التأكيد: اعتبر الدفع **فاشلاً** وأبلغ المزوّد — لا تُعلّم الطلب كمدفوع يدوياً.
6. شغّل التسوية: `GET /api/v1/reconciliation` ثم راجع `financial_events` و`commission_ledger`.

---

## 4. Celery / المهام الخلفية

```powershell
docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml restart celery-worker
```
- Broker و result backend كلاهما `REDIS_URL` افتراضياً.
- المهام التي تلمس بيانات مستأجر يجب أن تستدعي `core.middleware.bind_task_rls_context(tenant_id)`،
  وإلا سترى RLS صفوفاً صفرية (هذا سلوك مقصود).
- تحقق من طابور Redis: `redis-cli -u $env:REDIS_URL llen celery`.

---

## 5. تدقيق الأمان والصحة

```powershell
python scripts/audit_rls.py --check     # كل جداول tenant_id لها RLS (ساكن)
python scripts/audit_schema.py --check  # FK سليمة + فهارس tenant_id
python -m pre_commit run --all-files    # lint + yaml + حدود الملفات
```

### فحص إلزامي فور النشر (بعد كل نشر staging/production)
```powershell
# استخدم DATABASE_URL الخاص بالتطبيق (orion_app)، ليس أدمن الهجرة
python scripts/verify_deployment_rls.py --check
```
**النتيجة المتوقعة:** `RLS deployment issues: 0`. أي نتيجة أخرى تعني أن التطبيق
يتصل بـ superuser أو بمالك الجداول → RLS مُعطَّل فعلياً → **NO-GO**.

إذا أظهر `audit_rls` نقصاً: لا تُعطّل الفحص — أضف السياسة في هجرة جديدة وأعد التحقق.

---

## 6. التراجع عن نشر (Rollback)

1. `docker compose --env-file .env.production -f ...docker-compose.prod.yml down`
2. استعد آخر نسخة احتياطية صالحة (القسم 2).
3. أعد النشر بالإصدار السابق من الصورة/الـ commit.
4. شغّل `launch-verify` + التدقيقات + اختبار دفع sandbox واحد.

---

## 7. تدوير الأسرار (Secrets)

الأسرار: `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, `SENTRY_DSN`, `SMTP_PASSWORD`.

> تحذير: تغيير `ENCRYPTION_KEY` يجعل بيانات `credentials_encrypted` الحالية غير قابلة للفك.
> يجب إعادة تشفيرها أولاً عبر خدمة التشفير ثم التدوير.

---

## 8. المراقبة

- Grafana: لوحة `Orion API Overview` (معدل الطلبات، نسبة 5xx، p95).
- Prometheus: قواعد `alerts/alert_rules.yml` → `OrionApiDown`, `OrionHigh5xxRate`, `OrionSlowP95`.
- Sentry: `SENTRY_DSN` + `SENTRY_ENVIRONMENT=production` + `LOG_JSON=true`.
