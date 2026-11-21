/** CMS page management for tenant admins — SafeDOM + OrionAPI. */
const OrionAdminPages = {
  async loadPages() {
    const list = document.getElementById("pages-list");
    if (!list) return;
    try {
      const data = await OrionAPI.get("/i18n/pages?all=1");
      const pages = data.pages || [];
      SafeDOM.clear(list);
      if (!pages.length) {
        list.appendChild(SafeDOM.emptyMsg("لا توجد صفحات بعد."));
        return;
      }
      for (const page of pages) {
        const info = SafeDOM.elem("div", { className: "flex-1" }, [
          SafeDOM.elem("div", { className: "font-semibold" }, [page.title]),
          SafeDOM.elem("div", { className: "orion-muted text-xs" }, [
            `/pages/${page.slug} · ${page.is_published ? "منشورة" : "مخفية"}`,
          ]),
        ]);
        const edit = SafeDOM.actionBtn("تعديل", "orion-btn", () => this.fillForm(page));
        const remove = SafeDOM.actionBtn("حذف", "orion-btn", async () => {
          if (!OrionUI.confirmDanger(`حذف "${page.title}"؟`)) return;
          try {
            await OrionAPI.delete(`/i18n/pages/${page.id}`);
            OrionUI.toast("تم حذف الصفحة", "success");
            this.loadPages();
          } catch (err) {
            OrionUI.toast(err.message, "error");
          }
        });
        list.appendChild(
          SafeDOM.elem("div", { className: "flex items-center gap-3 border-b border-slate-800 py-2" }, [
            info,
            edit,
            remove,
          ])
        );
      }
    } catch (err) {
      OrionUI.toast(err.message, "error");
    }
  },

  fillForm(page) {
    document.getElementById("page-edit-id").value = page.id || "";
    document.getElementById("form-title").textContent = "تعديل الصفحة";
    document.getElementById("p-title").value = page.title || "";
    document.getElementById("p-slug").value = page.slug || "";
    document.getElementById("p-published").checked = Boolean(page.is_published);
    document.getElementById("p-trans-title").value = "";
    document.getElementById("p-trans-body").value = "";
  },

  clearForm() {
    document.getElementById("page-form")?.reset();
    document.getElementById("page-edit-id").value = "";
    document.getElementById("form-title").textContent = "إضافة صفحة";
  },

  payload() {
    return {
      title: document.getElementById("p-title").value.trim(),
      slug: document.getElementById("p-slug").value.trim(),
      is_published: document.getElementById("p-published").checked,
    };
  },

  translationPayload(pageTitle) {
    const title = document.getElementById("p-trans-title").value.trim();
    const body = document.getElementById("p-trans-body").value.trim();
    if (!title && !body) return null;
    return {
      locale: document.getElementById("p-locale").value,
      title: title || pageTitle,
      body: body || null,
    };
  },

  init() {
    const form = document.getElementById("page-form");
    if (!form) return;
    this.loadPages();

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const msg = document.getElementById("page-msg");
      const editId = document.getElementById("page-edit-id").value;
      const body = this.payload();
      const translation = this.translationPayload(body.title);
      try {
        const result = await OrionUI.withLoading(form, () =>
          editId
            ? OrionAPI.put(`/i18n/pages/${editId}`, body)
            : OrionAPI.post("/i18n/pages", body)
        );
        const pageId = result.page.id;
        if (translation) {
          await OrionAPI.put(`/i18n/pages/${pageId}/translations/${translation.locale}`, {
            title: translation.title,
            body: translation.body,
          });
        }
        this.clearForm();
        msg.textContent = editId ? "تم تعديل الصفحة" : "تمت إضافة الصفحة";
        OrionUI.toast(msg.textContent, "success");
        this.loadPages();
      } catch (err) {
        msg.textContent = err.message;
        OrionUI.toast(err.message, "error");
      }
    });

    document.getElementById("btn-cancel")?.addEventListener("click", () => this.clearForm());
    document.getElementById("btn-refresh")?.addEventListener("click", () => this.loadPages());
  },
};
