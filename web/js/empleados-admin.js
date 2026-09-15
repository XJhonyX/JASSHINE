(function(){
// JASSHINE — CRUD de Empleados (panel administrador)

const EMPLEADO_ESTADO_BADGE = {
  'Disponible': 'green',
  'En servicio': 'blue',
  'Descansando': 'orange',
  'Inactivo': 'red',
};

function initialsEmp(nombre) {
  return nombre.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
}

function renderEmpleados() {
  const tbody = document.getElementById('empleados-tbody');
  const q = document.getElementById('search-empleados').value.trim().toLowerCase();

  let rows = DB.getAll('empleados');
  document.getElementById('empleados-count').textContent = `TODOS LOS EMPLEADOS · ${rows.length}`;
  if (q) rows = rows.filter((e) => e.nombre.toLowerCase().includes(q) || e.cargo.toLowerCase().includes(q));

  if (rows.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No hay empleados que coincidan con la búsqueda.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map((e) => {
    const badgeCls = EMPLEADO_ESTADO_BADGE[e.estado] || 'green';
    return `
      <tr>
        <td><div class="person"><div class="person-avatar">${initialsEmp(e.nombre)}</div><div><div class="person-name">${e.nombre}</div><div class="person-sub">${e.email}</div></div></div></td>
        <td>${e.cargo}</td>
        <td>${e.telefono}</td>
        <td><span class="badge ${badgeCls}">${e.estado}</span></td>
        <td><div class="row-actions">
          <button class="icon-btn" data-edit="${e.id}" title="Editar">✎</button>
          <button class="icon-btn" data-delete="${e.id}" title="Eliminar">${ICON_TRASH}</button>
        </div></td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('[data-edit]').forEach((btn) => {
    btn.addEventListener('click', () => openEmpleadoForm(btn.dataset.edit));
  });
  tbody.querySelectorAll('[data-delete]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const e = DB.getById('empleados', btn.dataset.delete);
      confirmDeleteModal({
        message: `¿Eliminar a "${e.nombre}" del equipo? Esta acción no se puede deshacer.`,
        onConfirm: () => {
          DB.remove('empleados', btn.dataset.delete);
          renderEmpleados();
          showToast('Empleado eliminado');
        },
      });
    });
  });
}

function openEmpleadoForm(id) {
  const editing = id ? DB.getById('empleados', id) : null;
  openFormModal({
    title: editing ? 'Editar empleado' : 'Nuevo empleado',
    submitLabel: editing ? 'Guardar cambios' : 'Crear empleado',
    initial: editing || { estado: 'Disponible' },
    fields: [
      { name: 'nombre', label: 'Nombre completo', type: 'text', required: true },
      { name: 'email', label: 'Correo electrónico', type: 'email', required: true },
      { name: 'telefono', label: 'Teléfono', type: 'text', required: true },
      { name: 'cargo', label: 'Cargo', type: 'text', required: true },
      { name: 'estado', label: 'Estado', type: 'select', required: true, options: [
        { value: 'Disponible', label: 'Disponible' },
        { value: 'En servicio', label: 'En servicio' },
        { value: 'Descansando', label: 'Descansando' },
        { value: 'Inactivo', label: 'Inactivo' },
      ] },
    ],
    onSubmit: (data) => {
      if (editing) {
        DB.update('empleados', editing.id, data);
        showToast('Empleado actualizado');
      } else {
        DB.insert('empleados', data);
        showToast('Empleado creado');
      }
      renderEmpleados();
    },
  });
}

  renderEmpleados();
  document.getElementById('btn-nuevo-empleado').addEventListener('click', () => openEmpleadoForm(null));
  document.getElementById('search-empleados').addEventListener('input', renderEmpleados);
})();
