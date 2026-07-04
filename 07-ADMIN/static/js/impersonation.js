/** Impersonation banner controller (AZ-0.18). */
(function () {
  const banner = document.getElementById("impersonation-banner");
  const exitBtn = document.getElementById("btn-exit-impersonation");
  if (!banner || !exitBtn) return;

  let exiting = false;

  async function exitImpersonation() {
    if (exiting) return;
    exiting = true;
    exitBtn.disabled = true;
    exitBtn.textContent = "جاري الخروج...";

    try {
      const res = await OrionAPI.post("/platform/impersonation/end");
      if (res.ok) {
        window.location.reload();
      } else {
        const err = await res.json().catch(() => ({ message: "فشل الخروج" }));
        alert(err.message || "فشل إنهاء انتحال الهوية");
      }
    } catch (e) {
      console.error("Exit impersonation error:", e);
      alert("حدث خطأ غير متوقع");
    } finally {
      exiting = false;
      exitBtn.disabled = false;
      exitBtn.textContent = "إنهاء انتحال الهوية";
    }
  }

  exitBtn.addEventListener("click", exitImpersonation);
})();