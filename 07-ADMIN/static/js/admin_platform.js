/** Platform admin — dashboard, tenants, users, settings. */
const OrionAdminPlatform = {
  tenantNames: {},

  async initDashboard() {
    const ids = {
      tenants: "stat-tenants",
      active_tenants: "stat-active-tenants",
      users: "stat-users",
      active_users: "stat-active-users",
    };
    const show = (key, value) => {
      const el = document.getElementById(ids[key]);
      if (el) el.textContent = Number(value || 0).toLocaleString(document.documentElement.lang || "ar");
    };
    try {
      const data = await OrionAPI.get("/platform/stats");
      const s = data.stats || {};
      Object.keys(ids).forEach((key) => show(key, s[key]));
    } catch (err) {
      Object.keys(ids).forEach((key) => show(key, "—"));
      OrionUI.toast(OrionI18n.t("تعذّر تحميل إحصاءات المنصة", "Failed to load platform stats"), "error");
    }
  },

  async initTenants() {
    await this.loadTenants();
    document.getElementById("btn-new-tenant")?.addEventListener("click", () => this.openTenantModal());
    document.getElementById("btn-cancel-tenant-modal")?.addEventListener("click", () => this.closeTenantModal());
    const form = document.getElementById("tenant-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const id = document.getElementById("tenant-id").value;
        const payload = {
          name: form.querySelector("[name='name']").value,
          name_en: form.querySelector("[name='name_en']").value || undefined,
          logo_url: form.querySelector("[name='logo_url']").value || undefined,
          slug: form.querySelector("[name='slug']").value,
          email: form.querySelector("[name='email']").value,
          domain: form.querySelector("[name='domain']").value || undefined,
          status: form.querySelector("[name='status']").value,
        };
        try {
          if (id) {
            await OrionAPI.put(`/tenants/${id}`, payload);
          } else {
            await OrionAPI.post("/tenants/", payload);
          }
          this.closeTenantModal();
          await this.loadTenants();
        } catch (err) {
          alert(err.message || OrionI18n.t("فشل الحفظ", "Save failed"));
        }
      });
    }
  },

  async loadTenants() {
    const el = document.getElementById("tenants-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/tenants/");
      const rows = data.tenants || [];
      if (!rows.length) {
        SafeDOM.clear(el);
        el.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3", colspan: "5" }, [OrionI18n.t("لا توجد متاجر.", "No stores.")])
        ]));
        return;
      }
      SafeDOM.clear(el);
      for (const t of rows) {
        const nameTd = SafeDOM.elem("td", { className: "p-3" }, [t.name]);
        const slugTd = SafeDOM.elem("td", { className: "p-3" }, [t.slug]);
        const emailTd = SafeDOM.elem("td", { className: "p-3" }, [t.email]);
        const statusTd = SafeDOM.elem("td", { className: "p-3" }, [t.status]);
        const enterLink = SafeDOM.elem("a", {
          className: "orion-btn text-sm ml-2",
          href: `/admin/login?tenant_slug=${encodeURIComponent(t.slug)}`,
        }, [OrionI18n.t("دخول المتجر", "Enter store")]);
        const editBtn = SafeDOM.actionBtn(OrionI18n.t("تعديل", "Edit"), "text-blue-600 text-sm ml-2", () => OrionAdminPlatform.editTenant(t.id));
        const deleteBtn = SafeDOM.actionBtn(OrionI18n.t("حذف", "Delete"), "text-red-600 text-sm", () => OrionAdminPlatform.deleteTenant(t.id));
        const financeLink = SafeDOM.elem("a", {
          className: "text-blue-600 text-sm ml-2",
          href: `/admin/platform/stores/${t.id}/finance`,
        }, [OrionI18n.t("مالية", "Finance")]);
        const actionsTd = SafeDOM.elem("td", { className: "p-3" }, [enterLink, editBtn, financeLink, deleteBtn]);
        el.appendChild(SafeDOM.elem("tr", { className: "border-b" }, [nameTd, slugTd, emailTd, statusTd, actionsTd]));
      }
    } catch (err) {
      SafeDOM.clear(el);
      el.appendChild(SafeDOM.elem("tr", null, [
        SafeDOM.elem("td", { className: "p-3 text-red-600", colspan: "5" }, [err.message])
      ]));
    }
  },

  openTenantModal() {
    document.getElementById("tenant-id").value = "";
    document.getElementById("tenant-form").reset();
    document.getElementById("tenant-modal-title").textContent = OrionI18n.t("إضافة متجر", "Add store");
    document.getElementById("tenant-modal").classList.remove("hidden");
  },

  closeTenantModal() {
    document.getElementById("tenant-modal").classList.add("hidden");
  },

  async editTenant(id) {
    try {
      const data = await OrionAPI.get(`/tenants/${id}`);
      const t = data.tenant;
      document.getElementById("tenant-id").value = t.id;
      document.getElementById("tenant-name").value = t.name;
      document.getElementById("tenant-slug").value = t.slug;
      document.getElementById("tenant-email").value = t.email;
      document.getElementById("tenant-domain").value = t.domain || "";
      document.getElementById("tenant-status").value = t.status;
      document.getElementById("tenant-modal-title").textContent = OrionI18n.t("تعديل متجر", "Edit store");
      document.getElementById("tenant-modal").classList.remove("hidden");
    } catch (err) {
      alert(err.message);
    }
  },

  async deleteTenant(id) {
    if (!confirm(OrionI18n.t("هل أنت متأكد من حذف المتجر؟", "Delete this store?"))) return;
    try {
      await OrionAPI.delete(`/tenants/${id}`);
      await this.loadTenants();
    } catch (err) {
      alert(err.message);
    }
  },

  async initUsers() {
    document.getElementById("btn-new-user")?.addEventListener("click", () => this.openUserModal());
    document.getElementById("btn-cancel-user-modal")?.addEventListener("click", () => this.closeUserModal());
    await this.loadTenantsSelect();
    await this.loadUsers();
    const form = document.getElementById("user-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const type = form.querySelector("[name='user_type']").value;
        const payload = {
          email: form.querySelector("[name='email']").value,
          password: form.querySelector("[name='password']").value,
          is_superuser: type === "platform_admin",
          tenant_id: type === "tenant_admin" ? parseInt(form.querySelector("[name='tenant_id']").value) : null,
        };
        try {
          await OrionAPI.post("/users/", payload);
          this.closeUserModal();
          await this.loadUsers();
        } catch (err) {
          alert(err.message || OrionI18n.t("فشل الحفظ", "Save failed"));
        }
      });
    }
    const typeSelect = document.getElementById("user-type");
    if (typeSelect) {
      typeSelect.addEventListener("change", () => {
        document.getElementById("user-tenant-wrap").classList.toggle("hidden", typeSelect.value === "platform_admin");
      });
    }
  },

  async loadTenantsSelect() {
    const select = document.getElementById("user-tenant-id");
    if (!select) return;
    try {
      const data = await OrionAPI.get("/tenants/");
      const rows = data.tenants || [];
      SafeDOM.clear(select);
      for (const t of rows) {
        select.appendChild(SafeDOM.elem("option", { value: t.id }, [`${t.name} (${t.slug})`]));
      }
    } catch (err) {
      SafeDOM.clear(select);
    }
  },

  async loadUsers() {
    const el = document.getElementById("users-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/users/");
      const rows = data.users || [];
      if (!rows.length) {
        SafeDOM.clear(el);
        el.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3", colspan: "6" }, [OrionI18n.t("لا يوجد مستخدمين.", "No users.")])
        ]));
        return;
      }
      SafeDOM.clear(el);
      for (const u of rows) {
        const emailTd = SafeDOM.elem("td", { className: "p-3" }, [u.email]);
        const nameTd = SafeDOM.elem("td", { className: "p-3" }, [`${u.first_name || ""} ${u.last_name || ""}`]);
        const tenantTd = SafeDOM.elem("td", { className: "p-3" }, [u.tenant_id || "—"]);
        const roleTd = SafeDOM.elem("td", { className: "p-3" }, [u.is_superuser ? OrionI18n.t("مدير منصة", "Platform admin") : (u.is_admin ? OrionI18n.t("مدير متجر", "Store admin") : "—")]);
        const activeTd = SafeDOM.elem("td", { className: "p-3" }, [u.is_active ? OrionI18n.t("نشط", "Active") : OrionI18n.t("معطل", "Inactive")]);
        const roleBtn = SafeDOM.actionBtn(OrionI18n.t("الأدوار", "Roles"), "text-purple-600 text-sm ml-2", () => OrionAdminPlatform.assignUserRole(u));
        const deleteBtn = SafeDOM.actionBtn(OrionI18n.t("حذف", "Delete"), "text-red-600 text-sm", () => OrionAdminPlatform.deleteUser(u.id));
        const actionsTd = SafeDOM.elem("td", { className: "p-3" }, [roleBtn, deleteBtn]);
        el.appendChild(SafeDOM.elem("tr", { className: "border-b" }, [emailTd, nameTd, tenantTd, roleTd, activeTd, actionsTd]));
      }
    } catch (err) {
      SafeDOM.clear(el);
      el.appendChild(SafeDOM.elem("tr", null, [
        SafeDOM.elem("td", { className: "p-3 text-red-600", colspan: "6" }, [err.message])
      ]));
    }
  },

  openUserModal() {
    document.getElementById("user-form")?.reset();
    document.getElementById("user-modal")?.classList.remove("hidden");
  },

  closeUserModal() {
    document.getElementById("user-modal")?.classList.add("hidden");
  },

  async deleteUser(id) {
    if (!confirm(OrionI18n.t("هل أنت متأكد من حذف المستخدم؟", "Delete this user?"))) return;
    try {
      await OrionAPI.delete(`/users/${id}`);
      await this.loadUsers();
    } catch (err) {
      alert(err.message);
    }
  },

  async assignUserRole(user) {
    // Minimal assignment UI: no role-list endpoint exists yet, so the code is
    // entered directly. Full role/permission management is deferred.
    const roleCode = (prompt(OrionI18n.t("رمز الدور (مثال: store_staff)", "Role code (e.g. store_staff)")) || "").trim();
    if (!roleCode) return;
    const tenantRaw = (prompt(
      OrionI18n.t("معرّف المتجر (اتركه فارغاً لاستخدام متجر المستخدم)", "Store ID (leave blank to use the user’s store)"),
      user.tenant_id || ""
    ) || "").trim();
    const payload = { role_code: roleCode };
    if (tenantRaw) payload.tenant_id = parseInt(tenantRaw, 10);
    try {
      await OrionAPI.post(`/users/${user.public_id}/roles`, payload);
      OrionUI.toast(OrionI18n.t("تم تعيين الدور", "Role assigned"), "success");
      await this.loadUsers();
    } catch (err) {
      OrionUI.toast(err.message || OrionI18n.t("فشل تعيين الدور", "Failed to assign role"), "error");
    }
  },

  async initSettings() {
    const form = document.getElementById("settings-form");
    if (!form) return;
    try {
      const data = await OrionAPI.get("/platform/settings");
      const s = data.settings || {};
      document.getElementById("setting-platform-name").value = s.platform_name || "";
      document.getElementById("setting-owner-name").value = s.owner_name || "";
      document.getElementById("setting-support-email").value = s.support_email || "";
      document.getElementById("setting-default-currency").value = s.default_currency || "";
      document.getElementById("setting-default-language").value = s.default_language || "";
    } catch (err) {
      console.error("settings", err);
    }
    form.addEventListener("submit", async (e) => {
      e.preventDefault();
      const payload = {
        platform_name: form.querySelector("[name='platform_name']").value,
        owner_name: form.querySelector("[name='owner_name']").value,
        support_email: form.querySelector("[name='support_email']").value,
        default_currency: form.querySelector("[name='default_currency']").value,
        default_language: form.querySelector("[name='default_language']").value,
      };
      try {
        await OrionAPI.put("/platform/settings", payload);
        alert(OrionI18n.t("تم الحفظ", "Saved"));
      } catch (err) {
        alert(err.message || OrionI18n.t("فشل الحفظ", "Save failed"));
      }
    });
  },
};
function orionWireTableSearch(inputId) {
  const input = document.getElementById(inputId);
  if (!input || input.dataset.wired) return;
  input.dataset.wired = "1";
  input.addEventListener("input", function () {
    const q = input.value.trim().toLowerCase();
    document.querySelectorAll("table tbody tr").forEach(function (tr) {
      tr.hidden = q ? (tr.textContent || "").toLowerCase().indexOf(q) === -1 : false;
    });
  });
}
document.addEventListener("DOMContentLoaded", function () {
  orionWireTableSearch("tenant-search");
  orionWireTableSearch("user-search");
});
