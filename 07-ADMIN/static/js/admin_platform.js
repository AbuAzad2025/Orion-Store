/** Platform admin — dashboard, tenants, users, settings. */
const OrionAdminPlatform = {

  async initDashboard() {
    try {
      const data = await OrionAPI.get("/platform/stats");
      const s = data.stats || {};
      document.getElementById("stat-tenants").textContent = s.tenants || 0;
      document.getElementById("stat-active-tenants").textContent = s.active_tenants || 0;
      document.getElementById("stat-users").textContent = s.users || 0;
      document.getElementById("stat-active-users").textContent = s.active_users || 0;
    } catch (err) {
      console.error("stats", err);
    }
  },

  async initTenants() {
    await this.loadTenants();
    const form = document.getElementById("tenant-form");
    if (form) {
      form.addEventListener("submit", async (e) => {
        e.preventDefault();
        const id = document.getElementById("tenant-id").value;
        const payload = {
          name: form.querySelector("[name='name']").value,
          slug: form.querySelector("[name='slug']").value,
          email: form.querySelector("[name='email']").value,
          domain: form.querySelector("[name='domain']").value || undefined,
          status: form.querySelector("[name='status']").value,
        };
        try {
          if (id) {
            await OrionAPI.put(`/tenants/${id}`, payload);
          } else {
            await OrionAPI.post("/tenants", payload);
          }
          this.closeTenantModal();
          await this.loadTenants();
        } catch (err) {
          alert(err.message || "فشل الحفظ");
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
        el.innerHTML = '<tr><td colspan="5" class="p-3">لا توجد متاجر.</td></tr>';
        return;
      }
      el.innerHTML = rows.map((t) => `
        <tr class="border-b">
          <td class="p-3">${t.name}</td>
          <td class="p-3">${t.slug}</td>
          <td class="p-3">${t.email}</td>
          <td class="p-3">${t.status}</td>
          <td class="p-3">
            <button onclick="OrionAdminPlatform.editTenant(${t.id})" class="text-blue-600 text-sm ml-2">تعديل</button>
            <button onclick="OrionAdminPlatform.deleteTenant(${t.id})" class="text-red-600 text-sm">حذف</button>
          </td>
        </tr>
      `).join("");
    } catch (err) {
      el.innerHTML = `<tr><td colspan="5" class="p-3 text-red-600">${err.message}</td></tr>`;
    }
  },

  openTenantModal() {
    document.getElementById("tenant-id").value = "";
    document.getElementById("tenant-form").reset();
    document.getElementById("tenant-modal-title").textContent = "إضافة متجر";
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
      document.getElementById("tenant-modal-title").textContent = "تعديل متجر";
      document.getElementById("tenant-modal").classList.remove("hidden");
    } catch (err) {
      alert(err.message);
    }
  },

  async deleteTenant(id) {
    if (!confirm("هل أنت متأكد من حذف المتجر؟")) return;
    try {
      await OrionAPI.delete(`/tenants/${id}`);
      await this.loadTenants();
    } catch (err) {
      alert(err.message);
    }
  },

  async initUsers() {
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
          await OrionAPI.post("/users", payload);
          this.closeUserModal();
          await this.loadUsers();
        } catch (err) {
          alert(err.message || "فشل الحفظ");
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
      select.innerHTML = rows.map((t) => `<option value="${t.id}">${t.name} (${t.slug})</option>`).join("");
    } catch (err) {
      select.innerHTML = "";
    }
  },

  async loadUsers() {
    const el = document.getElementById("users-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/users/");
      const rows = data.users || [];
      if (!rows.length) {
        el.innerHTML = '<tr><td colspan="6" class="p-3">لا يوجد مستخدمين.</td></tr>';
        return;
      }
      el.innerHTML = rows.map((u) => `
        <tr class="border-b">
          <td class="p-3">${u.email}</td>
          <td class="p-3">${u.first_name || ""} ${u.last_name || ""}</td>
          <td class="p-3">${u.tenant_id || "—"}</td>
          <td class="p-3">${u.is_superuser ? "مدير منصة" : (u.is_admin ? "مدير متجر" : "—")}</td>
          <td class="p-3">${u.is_active ? "نشط" : "معطل"}</td>
          <td class="p-3">
            <button onclick="OrionAdminPlatform.deleteUser(${u.id})" class="text-red-600 text-sm">حذف</button>
          </td>
        </tr>
      `).join("");
    } catch (err) {
      el.innerHTML = `<tr><td colspan="6" class="p-3 text-red-600">${err.message}</td></tr>`;
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
    if (!confirm("هل أنت متأكد من حذف المستخدم؟")) return;
    try {
      await OrionAPI.delete(`/users/${id}`);
      await this.loadUsers();
    } catch (err) {
      alert(err.message);
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
      document.getElementById("setting-support-email").value = s.owner_email || "";
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
        alert("تم الحفظ");
      } catch (err) {
        alert(err.message || "فشل الحفظ");
      }
    });
  },
};
