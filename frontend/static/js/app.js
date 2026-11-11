(() => {
  const passwordForms = document.querySelectorAll("form");

  passwordForms.forEach((form) => {
    const password = form.querySelector('[name="password"], [name="nueva"]');
    const confirmation = form.querySelector('[name="confirmar"]');

    if (!password || !confirmation) return;

    const validateConfirmation = () => {
      const mismatch =
        confirmation.value !== "" && confirmation.value !== password.value;
      confirmation.setCustomValidity(
        mismatch ? "Las contraseñas no coinciden." : "",
      );

      if (mismatch) {
        confirmation.setAttribute("aria-invalid", "true");
      } else {
        confirmation.removeAttribute("aria-invalid");
      }
    };

    password.addEventListener("input", validateConfirmation);
    confirmation.addEventListener("input", validateConfirmation);
  });

  const menu = document.getElementById("menu-state");
  if (!menu) return;

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape" || !menu.checked) return;

    menu.checked = false;
    const toggle = document.querySelector('label.menu-toggle[for="menu-state"]');
    if (toggle) toggle.focus();
  });

  document.querySelectorAll(".sidebar a.nav-item").forEach((link) => {
    link.addEventListener("click", () => {
      menu.checked = false;
    });
  });
})();
