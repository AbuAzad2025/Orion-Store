# Orion / Azadexa — دليل التشغيل (RUNBOOK)

> النسخة 1.1 — 2026-11-28 (تحديث الجولتين 9–10: SFTP/systemd، POSTGRES_DB، بوابات التفعيل). يُحدَّث هذا الملف عند كل تغيير في الإجراءات.
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
> المسار أدناه هو نشر Docker (staging/بديل)؛ الإنتاج الحالي SFTP + systemd (§5.1 و§6).
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
**النتيجة المتوقعة:** `BACKUP_RESTORE_OK` وتطابق `(عدد الجداول, السياسات, المستأجرون, إصدار Alembic)`.
يُنشئ السكربت قاعدتين مؤقتتين (`orion_drill_src` / `orion_drill_restored`) ويحذفهما تلقائياً.

---

## 2. الاستعادة (Restore)

1. أوقف كتابة الطلبات (مثال: أوقف الـ webhook أو ضع المنصة في وضع الصيانة).
2. أنشئ نسخة احتياطية **جديدة** قبل الاستعادة (حتى لو كانت الحالية معطوبة).
3. استعد داخل حاوية Postgres:
```powershell
docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml `
  exec -T postgres pg_restore --clean --if-exists -U orion_admin -d orionstore_db < backup.dump
```
> Use the `POSTGRES_DB` value from `.env.production` (default `orionstore_db`);
> `-U orion_admin` is the migration/admin role defined in the production compose file.

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

## 5.1 النشر الأول (Deployment runbook)

1. انسخ `.env.production.example` إلى `.env.production` واملأ الأسرار الحقيقية.
2. ضع شهادة wildcard في `01-FOUNDATION/infrastructure/certs/`
   (`fullchain.pem` + `privkey.pem`) — راجع §0.1.
3. شغّل الفحص المحلي: `powershell -File scripts/preflight_deploy.ps1`.
   يجب أن ينتهي بـ `GO`؛ أي `NO-GO` يعني إيقاف النشر.
4. انشر: `docker compose --env-file .env.production -f 01-FOUNDATION/infrastructure/docker-compose.prod.yml up -d --build`.
5. تحقق بعد النشر:
   - `curl -I https://<tenant>.azadexa.com/health` → 200 + HSTS
   - `curl -I http://<tenant>.azadexa.com/` → 301 إلى HTTPS
   - `python scripts/verify_deployment_rls.py --check` → 0 مشاكل
   - طلب sandbox واحد كامل (طلب → دفع → فاتورة)
6. سجّل رقم الإصدار/الـ commit ووقت النشر في سجل العمليات.

### النشر الحالي (SFTP + systemd على نطاق واحد)
- المسار المعتمد محلياً: `.local/deploy_filtered.py --release <ts> --files <list>`.
- على السيرفر يستدعي `/srv/scripts/activate_orionstore.sh <release>` الذي:
  1. يحمّل `shared/.env` ويشغّل `flask db upgrade` **بكود الإصدار الجديد**،
  2. يتحقق من نسخة Alembic و`FORCE ROW LEVEL SECURITY`،
  3. يستدعي `activate.sh` العام ثم يتحقق من `/health`،
  4. يفشل النشر إذا فشلت أي خطوة (لا يُفعّل إصدار غير مكتمل).
- `activate.sh` العام **لا يُعدّل** لأن تطبيقات أخرى تستخدمه.
- الإقلاع نفسه يرفض العمل في production إذا لم يكن RLS مُفعّلاً بالقوة؛
  أثناء الـ migration فقط يُستخدم `ORION_SKIP_RLS_CHECK=1`.
- بوابات التفعيل وسلوك التراجع التلقائي موثّقة في §6.1.

---

## 6. التراجع عن نشر (Rollback) — SFTP + systemd

> النشر على السيرفر ليس `docker compose`؛ الإصدار يُفعَّل من `releases/<timestamp>`
> عبر `/srv/scripts/activate_orionstore.sh <release>`. التراجع يعيد تفعيل إصدار
> موجود أصلاً على السيرفر — **لا** `git pull/clone/fetch` ولا نشر من GitHub.

1. حدّد الإصدار الحالي والسابق (الإصدارات مُرتَّبة بالاسم تنازلياً، آخر 3 محفوظة):
   ```bash
   CURRENT=$(basename "$(readlink -f /srv/apps/orionstore/current)")
   ls -1 /srv/apps/orionstore/releases | sort -r
   PREV=<اسم-الإصدار-السابق-من-القائمة>
   ```
2. **تراجع سريع (كود فقط)** — يبدّل الـ symlink ويُعيد تشغيل `orionstore.service`
   دون لمس قاعدة البيانات (نفس آلية التراجع التلقائي في `activate_orionstore.sh`):
   ```bash
   /srv/scripts/activate.sh orionstore orionstore.service "$PREV"
   systemctl is-active orionstore.service
   curl -fsS "https://orion.azadexa.com/ready?check=$(date +%s%N)"
   ```
   النتيجة المتوقعة: `"status":"ready"` + `"database":true` + `"redis":true`.
   استخدم هذا فقط إذا كانت هجرات الإصدار الجديد متوافقة مع الكود السابق.
3. **تراجع كامل (كود + قاعدة البيانات)** — إذا طبّق الإصدار الفاشل هجرةً لا يعرفها
   الإصدار السابق، أو احتاجت البيانات نفسها للرجوع:
   ```bash
   /srv/apps/orionstore/venv/bin/python /srv/scripts/orion_backup.py list
   /srv/apps/orionstore/venv/bin/python /srv/scripts/orion_backup.py restore-platform \
     --dump /srv/apps/orionstore/shared/backups/full/orionstore_full_<stamp>.dump \
     --assets /srv/apps/orionstore/shared/backups/full/shared_<stamp>.tar.gz \
     --confirm RESTORE
   /srv/scripts/activate_orionstore.sh "$PREV"   # يُعيد تطبيق هجرات الإصدار السابق + البوابات
   ```
   `restore-platform` يأخذ نسخة أمان تلقائية، يوقف `orionstore` فقط، ينفّذ `pg_restore --clean`
   ويستخرج الأصول — **لا يمسّ `gop`**.
4. تحقق نهائي: `/health` + `/ready` + `python scripts/verify_deployment_rls.py --check` (صفر مشاكل)
   + عملية sandbox واحدة، ثم سجّل الإصدار والوقت في سجل العمليات.

### 6.1 بوابات التفعيل والتراجع التلقائي
- `activate_orionstore.sh <release>` يطبّق `flask db upgrade` بكود الإصدار الجديد
  (مع `ORION_SKIP_RLS_CHECK=1` أثناء الهجرة فقط)، ثم قبل تحريك الـ symlink يتحقق من:
  1. `alembic_version` غير فارغ،
  2. `FORCE ROW LEVEL SECURITY` مُفعّل على `users`،
  3. `/ready` → `status=ready` + `database=true` + `redis=true` (حتى 5 محاولات).
- فشل أي بوابة قبل التفعيل = إيقاف النشر؛ فشل فحص الصحة بعد التفعيل = عودة تلقائية
  للـ symlink إلى `PREV_REL` عبر `activate.sh` **دون** تراجع قاعدة البيانات؛
  حينها يلزم التراجع الكامل (الخطوة 3 أعلاه).
- إقلاع production يرفض العمل إن لم يكن RLS مُفعّلاً بالقوة؛ التجاوز مسموح به داخل الهجرة فقط.
- `activate.sh` العام **لا يُعدَّل** (تستخدمه تطبيقات أخرى)؛ `gop` و`default_server` لا يُلمسان.

### 6.2 تجربة النسخ/الاستعادة قبل النشر (drill)
- محلي/Staging (قاعدتان مؤقتتان `orion_drill_src` / `orion_drill_restored`، لا production):
  ```powershell
  $env:PYTHONPATH="02-CORE;03-MODELS;04-SERVICES;05-API;06-STOREFRONT;07-ADMIN"
  $env:FLASK_APP="orion.wsgi:app"; $env:FLASK_ENV="development"
  # POSTGRES_ADMIN_URL = local admin only (never a production URL)
  python scripts/verify_backup_restore.py --pg-bin "C:\Program Files\PostgreSQL\18\bin"
  ```
  `BACKUP_RESTORE_OK` وتطابق `(عدد الجداول, السياسات, المستأجرون, إصدار Alembic)` = تحقق ناجح.
- على السيرفر (نسخة حقيقية + استعادة تجريبية في بيئة اختبار، لا في المتجر الحي):
  ```bash
  /srv/apps/orionstore/venv/bin/python /srv/scripts/orion_backup.py backup-platform
  /srv/apps/orionstore/venv/bin/python /srv/scripts/orion_backup.py backup-store --slug palestinian-heritage
  # على نسخة اختبار/Staging فقط:
  /srv/apps/orionstore/venv/bin/python /srv/scripts/orion_backup.py restore-store \
    --slug <test-slug> --backup <path-to-store-archive.tar.gz> --confirm RESTORE
  ```
  قارن عدد الصفوف/الصور مع `manifest.json`، شغّل `python scripts/audit_rls.py --check` و
  `python scripts/audit_schema.py --check`، ثم احذف نسخة الاختبار. التفاصيل في
  `.local/scripts/README_BACKUP.md` — النسخ محلية على السيرفر فقط؛ انسخها لوسيط خارجي دورياً.

---

## 7. تدوير الأسرار (Secrets)

الأسرار: `SECRET_KEY`, `JWT_SECRET_KEY`, `ENCRYPTION_KEY`, `POSTGRES_PASSWORD`, `SENTRY_DSN`, `SMTP_PASSWORD`.

> تحذير: تغيير `ENCRYPTION_KEY` يجعل بيانات `credentials_encrypted` الحالية غير قابلة للفك.
> يجب إعادة تشفيرها أولاً عبر خدمة التشفير ثم التدوير.

---

## 8. المراقبة

- Grafana: لوحة `Orion API Overview` (معدل الطلبات، نسبة 5xx، p95).
- Prometheus: قواعد `alerts/alert_rules.yml` → `OrionApiDown`, `OrionHigh5xxRate`, `OrionSlowP95`, `OrionCeleryWorkerDown`, `OrionCeleryQueueDepthHigh`, `OrionBackupStale`.
- Alertmanager: ابدأ من `alerts/alertmanager.yml.example` بلا أسرار؛ الأسرار من ملفات mounted وقت النشر.
- Sentry: `SENTRY_DSN` + `SENTRY_ENVIRONMENT=production` + `LOG_JSON=true`.
