/** Live Chat admin — sessions and messages. */
const OrionAdminLiveChat = {
  currentSessionId: null,

  async loadSessions() {
    const el = document.getElementById("chat-sessions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/live-chat/sessions");
      const rows = data.sessions || [];
      if (!rows.length) { el.textContent = "لا توجد جلسات."; return; }
      el.innerHTML = rows.map((s) =>
        `<div class="border-b py-2 flex justify-between items-center">
          <span><strong>#${s.id}</strong> — ${s.customer_email || "زائر"} — ${s.status}</span>
          <button data-open="${s.id}" class="text-blue-600 text-xs">فتح</button>
        </div>`
      ).join("");
      el.querySelectorAll("[data-open]").forEach((btn) => {
        btn.addEventListener("click", () => OrionAdminLiveChat.openSession(parseInt(btn.dataset.open)));
      });
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  async openSession(sessionId) {
    OrionAdminLiveChat.currentSessionId = sessionId;
    document.getElementById("chat-session-id").textContent = `#${sessionId}`;
    document.getElementById("chat-room").style.display = "block";
    await OrionAdminLiveChat.loadMessages(sessionId);
  },

  async loadMessages(sessionId) {
    const el = document.getElementById("chat-messages");
    if (!el) return;
    try {
      const data = await OrionAPI.get(`/live-chat/sessions/${sessionId}/messages`);
      const rows = data.messages || [];
      el.innerHTML = rows.map((m) =>
        `<div class="${m.sender_type === 'agent' ? 'text-blue-700' : 'text-gray-700'}"><strong>${m.sender_type}:</strong> ${m.message}</div>`
      ).join("");
      el.scrollTop = el.scrollHeight;
    } catch (err) { el.textContent = err.message || "تعذّر التحميل"; }
  },

  init() {
    const createForm = document.getElementById("chat-create-form");
    if (createForm) {
      createForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const fd = new FormData(createForm);
        await OrionAPI.post("/live-chat/sessions", { customer_email: fd.get("customer_email") || undefined });
        createForm.reset();
        OrionAdminLiveChat.loadSessions();
      });
    }
    const sendForm = document.getElementById("chat-send-form");
    if (sendForm) {
      sendForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        if (!OrionAdminLiveChat.currentSessionId) return;
        const fd = new FormData(sendForm);
        await OrionAPI.post(`/live-chat/sessions/${OrionAdminLiveChat.currentSessionId}/messages`, {
          sender_type: "agent", message: fd.get("message"),
        });
        sendForm.reset();
        await OrionAdminLiveChat.loadMessages(OrionAdminLiveChat.currentSessionId);
      });
    }
    const closeBtn = document.getElementById("chat-close");
    if (closeBtn) {
      closeBtn.addEventListener("click", () => {
        document.getElementById("chat-room").style.display = "none";
        OrionAdminLiveChat.currentSessionId = null;
      });
    }
    OrionAdminLiveChat.loadSessions();
  },
};