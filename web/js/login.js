const roleBtns = document.querySelectorAll('.role-btn');
  let target = '../inicio/inicio-cliente.html';
  roleBtns.forEach(btn=>{
    btn.addEventListener('click', ()=>{
      roleBtns.forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      target = btn.dataset.target;
    });
  });
  document.getElementById('login-form').addEventListener('submit', (e)=>{
    e.preventDefault();
    // Demo: no hay backend todavía, así que solo redirigimos según el rol elegido.
    window.location.href = target;
  });
  document.getElementById('toggle-pass').addEventListener('click', ()=>{
    const input = document.getElementById('password');
    input.type = input.type === 'password' ? 'text' : 'password';
  });
