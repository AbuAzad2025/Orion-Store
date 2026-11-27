"""Locale-aware translation for user-facing API messages.

Services raise ``ValidationError`` with English literals, and some endpoints
return ``{"error": "..."}`` directly. Rather than rewriting hundreds of call
sites, the app translates the ``error`` field of JSON responses using the
locale already resolved onto ``flask.g`` by the middleware.
"""

from __future__ import annotations

from flask import g, has_request_context


def request_locale(default: str = "ar") -> str:
    """Return the locale resolved for the current request, if any."""
    if has_request_context():
        return getattr(g, "locale", None) or default
    return default


def localize(arabic: str, english: str, locale: str | None = None) -> str:
    """Pick the Arabic or English variant of a short user-facing string."""
    chosen = locale or request_locale()
    return english if chosen.split("_")[0].lower().startswith("en") else arabic


AR: dict[str, str] = {
    "An unexpected error occurred.": "حدث خطأ غير متوقع.",
    "Validation failed.": "فشل التحقق من البيانات.",
    "Resource not found.": "المورد غير موجود.",
    "Conflicting operation already in progress.": "عملية متضاربة قيد التنفيذ بالفعل.",
    "Authentication required.": "مطلوب تسجيل الدخول.",
    "Permission denied.": "تم رفض الإذن.",
    "Encryption operation failed.": "فشلت عملية التشفير.",
    "Document template validation failed.": "فشل التحقق من قالب المستند.",
    "Cart not found.": "السلة غير موجودة.",
    "Quantity must be at least 1.": "يجب أن تكون الكمية 1 على الأقل.",
    "Product not found.": "المنتج غير موجود.",
    "Insufficient stock.": "المخزون غير كافٍ.",
    "Cart is empty.": "السلة فارغة.",
    "Insufficient stock for product.": "المخزون غير كافٍ للمنتج.",
    "Voucher is not active yet.": "القسيمة غير مفعّلة بعد.",
    "Voucher has expired.": "انتهت صلاحية القسيمة.",
    "Voucher usage limit reached.": "تم بلوغ حد استخدام القسيمة.",
    "Order subtotal below voucher minimum.": "مجموع الطلب أقل من الحد الأدنى للقسيمة.",
    "Order already paid.": "الطلب مدفوع بالفعل.",
    "Payment already in progress.": "عملية الدفع قيد التنفيذ بالفعل.",
    "Payment result uncertain; reconcile before retry.": "نتيجة الدفع غير مؤكدة؛ يُرجى المطابقة قبل إعادة المحاولة.",
    "Only completed payments can be refunded.": "يمكن استرداد المدفوعات المكتملة فقط.",
    "Refund amount must be positive.": "يجب أن يكون مبلغ الاسترداد موجباً.",
    "Refund amount exceeds payment amount.": "مبلغ الاسترداد يتجاوز مبلغ الدفع.",
    "Payment already refunded.": "تم استرداد الدفع بالفعل.",
    "Payment already recorded.": "تم تسجيل الدفع بالفعل.",
    "Order is not payable.": "الطلب غير قابل للدفع.",
    "Invalid refund amount.": "مبلغ الاسترداد غير صالح.",
    "Password must be at least 8 characters.": "يجب أن تكون كلمة المرور 8 أحرف على الأقل.",
    "Super admin already exists.": "المدير العام موجود بالفعل.",
    "Email already registered for this tenant.": "البريد الإلكتروني مسجّل بالفعل لهذا المتجر.",
    "Invalid credentials.": "بيانات الدخول غير صالحة.",
    "User not found.": "المستخدم غير موجود.",
    "User does not belong to this tenant.": "المستخدم لا ينتمي إلى هذا المتجر.",
    "Role not found for this tenant.": "الدور غير موجود لهذا المتجر.",
    "Missing email or password.": "البريد الإلكتروني أو كلمة المرور مفقود.",
    "Not a customer account.": "هذا ليس حساب عميل.",
    "request_type must be export or delete.": "نوع الطلب يجب أن يكون تصديراً أو حذفاً.",
    "Request is not a deletion request.": "الطلب ليس طلب حذف.",
    "Logged out.": "تم تسجيل الخروج.",
    "Platform admin registration is not available through this endpoint.": "تسجيل مدير المنصة غير متاح عبر هذا المسار.",
    "Tenant context required.": "مطلوب سياق المتجر.",
    "Tenant context required (X-Tenant-ID).": "مطلوب سياق المتجر (X-Tenant-ID).",
    "Invalid request.": "طلب غير صالح.",
    "Invalid choice.": "اختيار غير صالح.",
    "Order not found.": "الطلب غير موجود.",
    "Only paid orders can be returned.": "يمكن إرجاع الطلبات المدفوعة فقط.",
    "Order item not found.": "عنصر الطلب غير موجود.",
    "Invalid return quantity.": "كمية الإرجاع غير صالحة.",
    "Return not found.": "طلب الإرجاع غير موجود.",
    "Return is not pending approval.": "طلب الإرجاع ليس بانتظار الموافقة.",
    "Return must be approved first.": "يجب الموافقة على الإرجاع أولاً.",
    "No pickup slot available today.": "لا توجد مواعيد استلام متاحة اليوم.",
    "Pickup slot is full.": "موعد الاستلام مكتمل.",
    "Order subtotal below shipping method minimum.": "مجموع الطلب أقل من الحد الأدنى لطريقة الشحن.",
    "Order subtotal exceeds shipping method maximum.": "مجموع الطلب يتجاوز الحد الأقصى لطريقة الشحن.",
    "Amount must be positive.": "يجب أن يكون المبلغ موجباً.",
    "Insufficient store credit.": "رصيد المتجر غير كافٍ.",
    "Category not found.": "التصنيف غير موجود.",
    "Brand not found.": "العلامة التجارية غير موجودة.",
    "Product slug already exists.": "رابط المنتج موجود بالفعل.",
    "Category slug already exists.": "رابط التصنيف موجود بالفعل.",
    "Registry not found.": "قائمة الهدايا غير موجودة.",
    "Quantity must be positive.": "يجب أن تكون الكمية موجبة.",
    "Page not found.": "الصفحة غير موجودة.",
    "Slug is required.": "الرابط مطلوب.",
    "Title is required.": "العنوان مطلوب.",
    "A page with this slug already exists.": "توجد صفحة بهذا الرابط بالفعل.",
    "Locale is required.": "اللغة مطلوبة.",
    "Invoice not found.": "الفاتورة غير موجودة.",
    "Invoice PDF not found.": "ملف الفاتورة PDF غير موجود.",
    "Missing required fields.": "الحقول المطلوبة مفقودة.",
    "Missing name.": "الاسم مفقود.",
    "Missing name or code.": "الاسم أو الرمز مفقود.",
    "Missing name or slug.": "الاسم أو الرابط مفقود.",
    "Brand slug already exists.": "رابط العلامة التجارية موجود بالفعل.",
    "Parent category not found.": "التصنيف الأب غير موجود.",
    "Missing product_id or price.": "معرّف المنتج أو السعر مفقود.",
    "Missing product_id or quantity.": "معرّف المنتج أو الكمية مفقود.",
    "Missing customer_email.": "بريد العميل مفقود.",
    "Quote not found.": "عرض السعر غير موجود.",
    "Customer group not found.": "مجموعة العملاء غير موجودة.",
    "Price list not found.": "قائمة الأسعار غير موجودة.",
    "Quote is not editable.": "لا يمكن تعديل عرض السعر.",
    "Quote already converted.": "تم تحويل عرض السعر بالفعل.",
    "Quote has no items.": "عرض السعر لا يحتوي على عناصر.",
    "Insufficient stock for quote conversion.": "المخزون غير كافٍ لتحويل عرض السعر.",
    "Missing warehouse_id, product_id, or quantity.": "معرّف المستودع أو المنتج أو الكمية مفقود.",
    "Missing order_public_id.": "معرّف الطلب العام مفقود.",
    "No warehouse configured.": "لا يوجد مستودع مُعدّ.",
    "Warehouse not found.": "المستودع غير موجود.",
    "Order must be paid before fulfillment.": "يجب دفع الطلب قبل التجهيز.",
    "Insufficient warehouse inventory.": "مخزون المستودع غير كافٍ.",
    "Fulfillment not found.": "طلب التجهيز غير موجود.",
    "Fulfillment cannot be shipped.": "لا يمكن شحن طلب التجهيز.",
    "Source and destination must differ.": "يجب أن يختلف المصدر عن الوجهة.",
    "Transfer not found.": "النقل غير موجود.",
    "Transfer is not in draft status.": "النقل ليس في حالة مسودة.",
    "Transfer has no items.": "النقل لا يحتوي على عناصر.",
    "Email and password required.": "البريد الإلكتروني وكلمة المرور مطلوبان.",
    "tenant_id required for tenant user.": "معرّف المتجر مطلوب لمستخدم المتجر.",
    "User deleted.": "تم حذف المستخدم.",
    "Invalid public_id.": "معرّف عام غير صالح.",
    "role_code required.": "رمز الدور مطلوب.",
    "Invalid tenant_id.": "معرّف متجر غير صالح.",
    "Tenant not found.": "المتجر غير موجود.",
    "Tenant deleted.": "تم حذف المتجر.",
    "Invalid tenant status.": "حالة المتجر غير صالحة.",
    "Slug already exists.": "الرابط موجود بالفعل.",
    "target_user_id (int) is required": "معرّف المستخدم المستهدف (عدد صحيح) مطلوب",
    "duration_hours must be 1-4": "مدة الجلسة يجب أن بين 1 و4 ساعات",
    "Target user not found": "المستخدم المستهدف غير موجود",
    "Cannot impersonate a platform admin": "لا يمكن انتحال صفة مدير المنصة",
    "Can only impersonate tenant admins": "يمكن انتحال صفة مدراء المتاجر فقط",
    "Target user has no tenant": "المستخدم المستهدف ليس له متجر",
    "Impersonator not found": "المُنتحِل غير موجود",
    "Only platform admins can start impersonation.": "مديرو المنصة فقط يمكنهم بدء الانتحال.",
    "Session already ended.": "انتهت الجلسة بالفعل.",
    "No valid impersonation session.": "لا توجد جلسة انتحال صالحة.",
    "Invalid impersonation context.": "سياق الانتحال غير صالح.",
    "Impersonation session is no longer valid.": "جلسة الانتحال لم تعد صالحة.",
    "Forbidden": "ممنوع",
    "Invalid user context.": "سياق المستخدم غير صالح.",
    "Superuser must not have tenant_id.": "يجب ألا يكون لدى المدير العام معرّف متجر.",
    "Platform admin required.": "مطلوب صلاحية مدير المنصة.",
    "Tenant admin required.": "مطلوب صلاحية مدير المتجر.",
    "Voucher not found.": "القسيمة غير موجودة.",
    "Missing method_code.": "رمز الطريقة مفقود.",
    "Markup not found.": "الترميز غير موجود.",
    "Jurisdiction not found.": "المنطقة الضريبية غير موجودة.",
    "Subscription plan not found.": "خطة الاشتراك غير موجودة.",
    "Subscription not found.": "الاشتراك غير موجود.",
    "Digital asset not found.": "الأصل الرقمي غير موجود.",
    "Footer placeholder required.": "عنصر التذييل نائب مطلوب.",
    "Immutable footer marker required.": "علامة التذييل الثابتة مطلوبة.",
    "PayPal client_id and client_secret are required.": "معرّف العميل وسر العميل في PayPal مطلوبان.",
    "Draft order not found.": "طلب المسودة غير موجود.",
    "Draft is no longer editable.": "لم تعد المسودة قابلة للتعديل.",
    "Draft already converted.": "تم تحويل المسودة بالفعل.",
    "Customer email is required to convert a draft.": "بريد العميل مطلوب لتحويل المسودة.",
    "Draft has no items.": "المسودة لا تحتوي على عناصر.",
    "Chat session not found.": "جلسة المحادثة غير موجودة.",
    "Metafield definition not found.": "تعريف الحقل الوصفي غير موجود.",
    "Program not found.": "البرنامج غير موجود.",
    "Affiliate not found.": "الشريك غير موجود.",
    "Bundle not found.": "الحزمة غير موجودة.",
    "Job not found.": "المهمة غير موجودة.",
    "Reconciliation run not found.": "تشغيل المطابقة غير موجود.",
    "Run not found.": "التشغيل غير موجود.",
    "This store is not in the closed beta program.": "هذا المتجر ليس ضمن برنامج التجريب المغلق.",
    "No WhatsApp number is configured for this store.": "رقم واتساب غير مُضبط لهذا المتجر.",
    "The cart is empty.": "السلة فارغة.",
    "Invalid phone number.": "رقم الهاتف غير صالح.",
    "Image URL must start with https:// or /": "رابط الصورة يجب أن يبدأ بـ https:// أو /",
}

EN: dict[str, str] = {ar: en for en, ar in AR.items()}
EN.update(
    {
        "حدث خطأ غير متوقع.": "An unexpected error occurred.",
        "مطلوب تسجيل الدخول.": "Authentication required.",
        "طلب غير صالح.": "Invalid request.",
        "السلة فارغة.": "The cart is empty.",
        "رقم واتساب غير مُضبط لهذا المتجر.": "No WhatsApp number is configured for this store.",
        "رقم الهاتف غير صالح.": "Invalid phone number.",
        "رابط الصورة يجب أن يبدأ بـ https:// أو /": "Image URL must start with https:// or /",
    }
)


def translate_message(text: str, locale: str = "ar") -> str:
    """Translate a known user-facing message into ``locale``."""
    if not isinstance(text, str):
        return text
    table = EN if (locale or "ar").split("_")[0].lower().startswith("en") else AR
    return table.get(text, text)
