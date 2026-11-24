/** Live Chat admin — sessions and messages. */
const OrionAdminLiveChat = {
  currentSessionId: null,

  async loadSessions() {
    const el = document.getElementById("chat-sessions-list");
    if (!el) return;
    try {
      const data = await OrionAPI.get("/live-chat/sessions");
      const rows = data.sessions || [];
      if (!rows.length) { el.textContent = OrionI18n.t('لا توجد جلسات.', 'No sessions found.'); return; }
      SafeDOM.clear(el);
      for (const s of rows) {
        el.appendChild(SafeDOM.elem("div", { className: "border-b py-2 flex justify-between items-center" }, [
          SafeDOM.elem("span", {}, [
            SafeDOM.elem("strong", {}, [`#${s.id}`]),
            " — ", s.customer_email || OrionI18n.t('زائر', 'Visitor'), " — ", s.status
          ]),
          SafeDOM.elem("button", { "data-open": s.id, className: "text-blue-600 text-xs" }, [OrionI18n.t('فتح', 'Open')])
        ]));
      }
      el.querySelectorAll("[data-open]").forEach((btn) => {
        btn.addEventListener("click", () => OrionAdminLiveChat.openSession(parseInt(btn.dataset.open)));
      });
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
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
      SafeDOM.clear(el);
      for (const m of rows) {
        el.appendChild(SafeDOM.elem("div", { className: m.sender_type === 'agent' ? 'text-blue-700' : 'text-gray-700' }, [
          SafeDOM.elem("strong", {}, [m.sender_type + ":"]),
          " ", m.message
        ]));
      }
      el.scrollTop = el.scrollHeight;
    } catch (err) { el.textContent = err.message || OrionI18n.t('تعذّر التحميل', 'Failed to load'); }
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