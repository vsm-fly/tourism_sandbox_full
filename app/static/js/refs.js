document.addEventListener("DOMContentLoaded", function () {
  // --- Быстрое добавление типа (как было) ---
  const qtForm = document.getElementById("quickTypeForm");
  const qtErr  = document.getElementById("qtErr");
  if (qtForm) {
    qtForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      if (qtErr) { qtErr.classList.add("d-none"); qtErr.textContent = ""; }
      const fd = new FormData(qtForm);
      try {
        const r = await fetch(qtForm.action || qtForm.getAttribute("data-action"), {
          method: "POST", headers: { "X-Requested-With": "XMLHttpRequest" }, body: fd
        });
        const data = await r.json();
        if (!data.ok) {
          if (qtErr) { qtErr.textContent = data.error || (data.errors && JSON.stringify(data.errors)) || "Ошибка"; qtErr.classList.remove("d-none"); }
          return;
        }
        const sel = document.getElementById("type_id") || document.querySelector("select[name='type_id']");
        if (sel) {
          const exists = Array.from(sel.options).some(o => String(o.value) === String(data.id));
          if (!exists) sel.add(new Option(data.name, data.id, true, true));
          sel.value = data.id;
        }
        const modalEl = document.getElementById("quickTypeModal");
        if (modalEl && window.bootstrap) {
          const modal = bootstrap.Modal.getInstance(modalEl) || new bootstrap.Modal(modalEl);
          modal.hide();
        }
        qtForm.reset();
      } catch (e) {
        if (qtErr) { qtErr.textContent = "Сбой сети"; qtErr.classList.remove("d-none"); }
      }
    });
  }

  // --- Batch per-form ---
  document.querySelectorAll('form[action*="/refs/codes/batch"]').forEach((form) => {
    const checkAll = form.querySelector('[id="checkAll"], [data-checkall]');
    const rowChecks = Array.from(form.querySelectorAll(".row-check"));
    const actionSel = form.querySelector('select[name="action"]');
    // именно в этой форме (не перепутает с фильтрами)
    const typeSel   = form.querySelector('select[name="type_id"]');
    const applyBtn  = form.querySelector('#batchDo, button[type="submit"]');

    function anyChecked() { return rowChecks.some(c => c.checked); }
    function needType() { return actionSel && actionSel.value === "set_type"; }
    function hasType() { return typeSel && typeSel.value && typeSel.value !== "0"; }
    function hasAction() { return actionSel && !!actionSel.value; }

    function syncUI() {
      if (typeSel) {
        if (needType()) typeSel.classList.remove("d-none"); else typeSel.classList.add("d-none");
      }
      const enable = anyChecked() && hasAction() && (!needType() || hasType());
      if (applyBtn) applyBtn.disabled = !enable;
    }

    rowChecks.forEach(c => c.addEventListener("change", syncUI));
    if (checkAll) {
      checkAll.addEventListener("change", () => {
        rowChecks.forEach(c => c.checked = checkAll.checked);
        syncUI();
      });
    }
    if (actionSel) actionSel.addEventListener("change", syncUI);
    if (typeSel) typeSel.addEventListener("change", syncUI);
    syncUI();

    form.addEventListener("submit", (e) => {
      // подстрахуем, даже если disabled не сработал
      if (!hasAction()) { e.preventDefault(); alert("Выберите действие"); return; }
      if (!anyChecked()) { e.preventDefault(); alert("Выберите хотя бы одну запись"); return; }
      if (needType() && !hasType()) { e.preventDefault(); alert("Выберите тип"); return; }
      if (actionSel && actionSel.value === "delete") {
        if (!confirm("Удалить выбранные записи? Это действие необратимо.")) { e.preventDefault(); return; }
      }
    });
  });
});
