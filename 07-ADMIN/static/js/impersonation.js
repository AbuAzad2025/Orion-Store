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
    exitBtn.textContent = OrionI18n.t('جاري الخروج...', 'Exiting...');

    try {
      await OrionAPI.post("/end");
      window.location.reload();
    } catch (e) {
      console.error("Exit impersonation error:", e);
      OrionUI.toast(OrionI18n.t('حدث خطأ غير متوقع', 'An unexpected error occurred'), "error");
    } finally {
      exiting = false;
      exitBtn.disabled = false;
      exitBtn.textContent = OrionI18n.t('إنهاء انتحال الهوية', 'End impersonation');
    }
  }

  exitBtn.addEventListener("click", exitImpersonation);
})();