document.getElementById('signup-form').addEventListener('submit', (e)=>{
    e.preventDefault();
    // Demo: no hay backend todavía, así que un cliente nuevo pasa directo a su panel.
    window.location.href = '../inicio/inicio-cliente.html';
  });
  document.getElementById('toggle-pass').addEventListener('click', ()=>{
    const input = document.getElementById('password');
    input.type = input.type === 'password' ? 'text' : 'password';
  });
