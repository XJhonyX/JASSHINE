(function(){
// JASSHINE — Configuración (panel administrador): guarda datos del negocio

  const negocio = DB.getAll('negocio')[0];
  if (negocio) {
    document.getElementById('f-nombre').value = negocio.nombre;
    document.getElementById('f-correo').value = negocio.correo;
    document.getElementById('f-telefono').value = negocio.telefono;
    document.getElementById('f-direccion').value = negocio.direccion;
  }

  wireToggles();

  document.getElementById('btn-guardar-negocio').addEventListener('click', () => {
    DB.update('negocio', negocio.id, {
      nombre: document.getElementById('f-nombre').value,
      correo: document.getElementById('f-correo').value,
      telefono: document.getElementById('f-telefono').value,
      direccion: document.getElementById('f-direccion').value,
    });
    showToast('Datos del negocio guardados');
  });
})();
