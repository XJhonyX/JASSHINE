(function(){
// JASSHINE — Configuración (panel cliente): guarda el perfil real en "clientes"

  const cliente = DB.getById('clientes', CLIENTE_DEMO_ID);
  if (cliente) {
    document.getElementById('f-nombre').value = cliente.nombre;
    document.getElementById('f-telefono').value = cliente.telefono;
    document.getElementById('f-email').value = cliente.email;
    document.getElementById('f-moto').value = cliente.moto;
  }

  wireToggles();

  document.getElementById('btn-guardar-perfil').addEventListener('click', () => {
    DB.update('clientes', CLIENTE_DEMO_ID, {
      nombre: document.getElementById('f-nombre').value,
      telefono: document.getElementById('f-telefono').value,
      email: document.getElementById('f-email').value,
      moto: document.getElementById('f-moto').value,
    });
    showToast('Perfil actualizado');
  });
})();
