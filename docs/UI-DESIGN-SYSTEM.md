# نظام تصميم Orion — المرجع التنفيذي

> مصدر الحقيقة: `01-FOUNDATION/assets/orion-theme.css`
> البناء: `npm run build:css` → يولّد `tailwind.css` + ينسخ `orion-theme.css` إلى
> مجلدَي static في المتجر والإدارة. **لا CDN في وقت التشغيل.**

---

## 1. المبادئ
1. RTL-first: خصائص منطقية (`inset-inline-*`, `margin-inline-*`, `border-inline-start`) — لا `left/right`.
2. تباين كافٍ (WCAG AA ≥ 4.5 للنص العادي) على الخلفية الداكنة.
3. لا ألوان عشوائية في القوالب — استخدم المتغيّرات أو المكوّنات الجاهزة.
4. كل عنصر تفاعلي له `:focus-visible` واسم قابل للوصول (`aria-label` أو نص).
5. احترام `prefers-reduced-motion`.

## 2. المتغيّرات (Design Tokens)

| المتغيّر | القيمة | الاستخدام |
|---|---|---|
| `--orion-bg` | `#0b1220` | خلفية الصفحة |
| `--orion-panel` | `#111c2e` | البطاقات/الحقول |
| `--orion-panel-2` | `#16243a` | الحالات/Topbar |
| `--orion-text` | `#e8eef7` | النص الأساسي |
| `--orion-muted` | `#a9b8cc` | النص الثانوي |
| `--orion-gold` | `#e6c479` | العناوين/التمييز/الحدود النشطة |
| `--orion-gold-strong` | `#f2d99b` | hover للأزرار الذهبية |
| `--orion-accent` | `#7cb0f8` | focus outline |
| `--orion-danger` | `#ff9b9b` | أخطاء/خروج |
| `--orion-success` | `#8fe0b0` | نجاح |
| `--orion-border` | `#2a3b55` | الحدود |
| `--orion-radius` | `14px` | انحناء البطاقات |
| `--orion-shadow` | `0 12px 32px rgba(0,0,0,.35)` | ظل البطاقات |

## 3. المكوّنات

### `.orion-surface`
يُوضع على `<body>`؛ يضبط الخلفية/النص ويُعيد تعريف أدوات Tailwind الشائعة
(`bg-white`, `text-gray-*`, `border-gray-*`) داخل النطاق فقط.

### `.orion-card`
حاوية زجاجية داكنة بحدّ وظل. للتجميعات/Illustrations داخل البطاقة.

### `.orion-stat` + `.orion-stat-value` + `.orion-stat-label`
بطاقة رقم إحصائي. مثال:
```html
<div class="orion-card orion-stat">
  <span class="orion-stat-label">إجمالي الطلبات</span>
  <span class="orion-stat-value">1,234</span>
</div>
```

### `.orion-btn` / `.orion-btn-gold`
زر قياسي (ارتفاع 2.75rem، حواف دائرية). الذهبي للإجراء الأساسي فقط (حفظ/دفع/تأكيد).

### `.orion-input` / `.orion-select`
حقول نموذج متسقة مع الخلفية الداكنة.

### `.orion-table`
جدول بحدود/radius موحّدة؛ الرؤوس ذهبية.

### `.orion-nav-link` (+ `.is-active`)
روابط الشريط الجانبي؛ الحد النشط على `border-inline-start` (ينعكس تلقائياً في RTL).

### `.orion-badge`
شارة صغيرة للحالة/الدور.

### `.orion-topbar` + `.orion-breadcrumb` + `.orion-user-pill`
شريط علوي لاصق مع مسار تنقّل ومعلومات المستخدم/المستأجر.

### `.orion-toast` / `.orion-toast-host`
رسائل زائدة من `OrionUI.toast(message, kind)` — تظهر تلقائياً عند `orion-api-error`.

### `.orion-skeleton` + `.orion-loading`
حالة تحميل (shimmer) وحالة تعطيل مؤقتة مع `aria-busy`.

### `.orion-skip-link`
رابط "تخطَّ إلى المحتوى" يظهر عند التركيز فقط (WCAG 2.4.1).

## 4. صفحة المعاينة
توجد صفحة حيّة تعرض كل مكوّن بحالاته على:
`/admin/store/ui-kit` (قالب `07-ADMIN/templates/ui_kit.html`).

## 5. قواعد الاستخدام في القوالب
- لا تضف `style="..."` جديداً؛ أضف صنفاً إلى `orion-theme.css`.
- الأرقام تُعرض عبر `Number(v).toLocaleString("ar")`.
- أي طلب API يمرّ عبر `OrionAPI` (لا `fetch` مباشر) ليحصل على التحميل/الخطأ تلقائياً.
- أي عنصر تفاعلي جديد يجب أن يمرّ `scripts/audit_a11y.py --check`.

## 6. البناء
```powershell
npm install
npm run build:css
python -m pre_commit run --all-files
python -m pytest tests/ui tests/e2e -q -m "e2e or not external"
```
