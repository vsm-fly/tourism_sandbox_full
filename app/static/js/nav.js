document.addEventListener("keydown", function(e){
  if (e.altKey && e.shiftKey && (e.key || "").toLowerCase() === "s") {
    const el = document.getElementById("ddRefs");
    if (!el || !window.bootstrap) return;
    e.preventDefault();
    const dd = bootstrap.Dropdown.getOrCreateInstance(el);
    dd.show();
    // фокус на первый пункт
    const first = document.querySelector("#menuRefs .dropdown-menu a.dropdown-item");
    if (first) first.focus();
  }
});
