document.getElementById('signup-form').addEventListener('submit', (e)=>{
    e.preventDefault();
    // Demo: no hay backend todavía, así que un cliente nuevo pasa directo a su panel.
    window.location.href = '../inicio/inicio-cliente.html';
  });
  document.getElementById('toggle-pass').addEventListener('click', (e)=>{
    const btn = e.currentTarget;
    const input = document.getElementById('password');
    const showing = input.type === 'password';
    input.type = showing ? 'text' : 'password';
    btn.setAttribute('aria-label', showing ? 'Ocultar contraseña' : 'Mostrar contraseña');
    btn.setAttribute('aria-pressed', String(showing));
  });
