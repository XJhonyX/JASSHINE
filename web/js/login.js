const roleBtns = document.querySelectorAll('.role-btn');
  let target = '../inicio/inicio-cliente.html';
  roleBtns.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      roleBtns.forEach(b=>{ b.classList.remove('active'); b.setAttribute('aria-checked','false'); });
      btn.classList.add('active');
      btn.setAttribute('aria-checked','true');
      target = btn.dataset.target;
    });
  });
  document.getElementById('login-form').addEventListener('submit', (e)=>{
    e.preventDefault();
    // Demo: no hay backend todavía, así que solo redirigimos según el rol elegido.
    window.location.href = target;
  });
  document.getElementById('toggle-pass').addEventListener('click', (e)=>{
    const btn = e.currentTarget;
    const input = document.getElementById('password');
    const showing = input.type === 'password';
    input.type = showing ? 'text' : 'password';
    btn.setAttribute('aria-label', showing ? 'Ocultar contraseña' : 'Mostrar contraseña');
    btn.setAttribute('aria-pressed', String(showing));
  });
