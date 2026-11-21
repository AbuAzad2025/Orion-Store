# Diagnostics (manual use only)

هذه سكربتات تشخيص قديمة كانت في جذر المشروع. نُقلت هنا لتنظيف الجذر، وهي:

- **غير جزء من CI** — `pyproject.toml` يحدد `testpaths = ["tests", "02-CORE/tests"]`.
- **غير مخصصة للإنتاج** — تحتوي عناوين/kredentials محلية للتحقق اليدوي فقط.
- `probe_rls.py` استُبدل عملياً بـ `scripts/audit_rls.py` و`tests/integration/test_rls_coverage.py`.

لا تضف هذه الملفات إلى مسارات الاختبار أو التشغيل التلقائي.
