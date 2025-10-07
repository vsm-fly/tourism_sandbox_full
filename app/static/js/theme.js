document.addEventListener("DOMContentLoaded", () => {
  const body = document.body;
  const btn = document.getElementById("themeToggle");

  // Загружаем состояние
  if (localStorage.getItem("theme") === "dark") {
    body.classList.add("dark-theme");
  }

  btn.addEventListener("click", () => {
    body.classList.toggle("dark-theme");
    if (body.classList.contains("dark-theme")) {
      localStorage.setItem("theme", "dark");
      btn.innerHTML = '<i class="bi bi-brightness-high"></i> Светлая';
    } else {
      localStorage.setItem("theme", "light");
      btn.innerHTML = '<i class="bi bi-moon"></i> Тёмная';
    }
  });
});

