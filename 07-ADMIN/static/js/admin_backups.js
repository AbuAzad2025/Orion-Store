/** Manual backup creation/download for store and platform admin panels. */
const OrionAdminBackups = {
  base() {
    const scope = document.getElementById("backups-root")?.dataset.backupScope || "store";
    return scope === "platform" ? "/platform/backups" : "/tenant/backups";
  },
  isPlatform() {
    return this.base().startsWith("/platform");
  },
  size(bytes) {
    if (!bytes) return "—";
    return bytes >= 1048576
      ? (bytes / 1048576).toFixed(1) + " MB"
      : Math.ceil(bytes / 1024) + " KB";
  },
  link(url, label) {
    return SafeDOM.elem("a", {
      className: "orion-btn text-xs",
      href: url,
      target: "_blank",
      rel: "noopener",
      download: "",
    }, [label]);
  },
  async load() {
    const target = document.getElementById("backups-list");
    if (!target) return;
    try {
      const data = await OrionAPI.get(this.base());
      SafeDOM.clear(target);
      const rows = data.backups || [];
      if (!rows.length) {
        target.appendChild(SafeDOM.elem("tr", null, [
          SafeDOM.elem("td", { className: "p-3 orion-muted", colspan: "4" }, [OrionI18n.t("لا توجد نسخ بعد", "No backups yet")])
        ]));
        return;
      }
      rows.forEach((b) => {
        const date = (b.stamp || "").replace(/(\d{4})(\d{2})(\d{2})-(\d{2})(\d{2})(\d{2})/, "$1-$2-$3 $4:$5:$6");
        const cells = [
          SafeDOM.elem("td", { className: "p-2", dir: "ltr" }, [date]),
        ];
        if (this.isPlatform()) {
          cells.push(SafeDOM.elem("td", { className: "p-2" }, [
            b.dump ? this.link(`/api/v1/platform/backups/${encodeURIComponent(b.dump)}/download?kind=dump`, OrionI18n.t("تنزيل", "Download")) : "—"
          ]));
          cells.push(SafeDOM.elem("td", { className: "p-2" }, [
            b.assets ? this.link(`/api/v1/platform/backups/${encodeURIComponent(b.assets)}/download?kind=assets`, OrionI18n.t("تنزيل", "Download")) : "—"
          ]));
        } else {
          cells.push(SafeDOM.elem("td", { className: "p-2" }, [b.kind]));
          cells.push(SafeDOM.elem("td", { className: "p-2" }, [
            this.link(`/api/v1/tenant/backups/${encodeURIComponent(b.name)}/download`, OrionI18n.t("تنزيل", "Download"))
          ]));
        }
        cells.push(SafeDOM.elem("td", { className: "p-2" }, [this.size(b.size)]));
        target.appendChild(SafeDOM.elem("tr", null, cells));
      });
    } catch (err) {
      target.textContent = err.message;
    }
  },
  async create() {
    const btn = document.getElementById("backup-create");
    const msg = document.getElementById("backup-msg");
    if (!btn) return;
    btn.disabled = true;
    if (msg) msg.textContent = OrionI18n.t("جارٍ إنشاء النسخة…", "Creating backup…");
    try {
      await OrionAPI.post(this.base(), {});
      if (msg) msg.textContent = OrionI18n.t("تم إنشاء النسخة", "Backup created");
      OrionUI.toast(OrionI18n.t("تم إنشاء النسخة", "Backup created"), "success");
      await this.load();
    } catch (err) {
      if (msg) msg.textContent = err.message;
      OrionUI.toast(err.message, "error");
    } finally {
      btn.disabled = false;
    }
  },
  init() {
    document.getElementById("backup-create")?.addEventListener("click", () => this.create());
    this.load();
  },
};
