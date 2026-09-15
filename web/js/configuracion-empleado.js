(function(){
// JASSHINE — Configuración (panel empleado): guarda el perfil real en "empleados"

  const empleado = DB.getById('empleados', EMPLEADO_DEMO_ID);
  if (empleado) {
    document.getElementById('f-nombre').value = empleado.nombre;
    document.getElementById('f-telefono').value = empleado.telefono;
    document.getElementById('f-email').value = empleado.email;
  }

  wireToggles();

  document.getElementById('btn-guardar-perfil').addEventListener('click', () => {
    DB.update('empleados', EMPLEADO_DEMO_ID, {
      nombre: document.getElementById('f-nombre').value,
      telefono: document.getElementById('f-telefono').value,
      email: document.getElementById('f-email').value,
    });
    showToast('Perfil actualizado');
  });
})();
