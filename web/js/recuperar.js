// JASSHINE — Recuperar contraseña
// Flujo de demostración (sin backend todavía): valida el formulario en el
// navegador y avanza entre los 4 estados de la pantalla.

function showStep(id) {
  document.querySelectorAll('.form-card').forEach(card => card.classList.add('hidden'));
  document.getElementById(id).classList.remove('hidden');
}

// Paso 1 -> Paso 2: pedir el correo y "enviar" el código
const requestForm = document.getElementById('request-form');
requestForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const email = document.getElementById('email').value;
  document.getElementById('sent-email').textContent = email;
  showStep('step-code');
  const firstDigit = document.querySelector('.code-digit');
  if (firstDigit) firstDigit.focus();
});

// Autoavance entre las casillas del código
document.querySelectorAll('.code-digit').forEach((input, index, all) => {
  input.addEventListener('input', () => {
    if (input.value && index < all.length - 1) {
      all[index + 1].focus();
    }
  });
  input.addEventListener('keydown', (e) => {
    if (e.key === 'Backspace' && !input.value && index > 0) {
      all[index - 1].focus();
    }
  });
});

// Paso 2 -> Paso 3: verificar el código
const codeForm = document.getElementById('code-form');
codeForm.addEventListener('submit', (e) => {
  e.preventDefault();
  showStep('step-reset');
});

const resend = document.getElementById('resend');
if (resend) {
  resend.addEventListener('click', (e) => {
    e.preventDefault();
    resend.textContent = 'Código reenviado ✓';
    setTimeout(() => { resend.textContent = 'Reenviar código'; }, 2500);
  });
}

// Paso 3 -> Paso 4: guardar la nueva contraseña
const resetForm = document.getElementById('reset-form');
resetForm.addEventListener('submit', (e) => {
  e.preventDefault();
  const pass = document.getElementById('new-password').value;
  const confirm = document.getElementById('confirm-password').value;
  const errorMsg = document.getElementById('error-msg');
  if (pass !== confirm) {
    errorMsg.classList.remove('hidden');
    return;
  }
  errorMsg.classList.add('hidden');
  showStep('step-done');
});

// Mostrar/ocultar contraseña
document.querySelectorAll('.toggle-pass').forEach((icon) => {
  icon.addEventListener('click', () => {
    const input = icon.previousElementSibling;
    input.type = input.type === 'password' ? 'text' : 'password';
  });
});
