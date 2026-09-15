(function(){
// JASSHINE — CRUD de Usuarios (panel administrador)

const ROL_BADGE = {
  admin: { label: 'Administrador', cls: 'purple' },
  empleado: { label: 'Empleado', cls: 'blue' },
  cliente: { label: 'Cliente', cls: 'orange' },
};

const ESTADO_BADGE = {
  activo: { label: 'Activo', cls: 'green' },
  inactivo: { label: 'Inactivo', cls: 'red' },
  suspendida: { label: 'Suspendida', cls: 'red' },
};

function initials(nombre) {
  return nombre.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
}

function renderUsuarios() {
  const tbody = document.getElementById('usuarios-tbody');
  const rolFiltro = document.getElementById('filter-rol').value;
  const q = document.getElementById('search-usuarios').value.trim().toLowerCase();

  let rows = DB.getAll('usuarios');
  if (rolFiltro) rows = rows.filter((u) => u.rol === rolFiltro);
  if (q) rows = rows.filter((u) => u.nombre.toLowerCase().includes(q) || u.email.toLowerCase().includes(q));

  document.getElementById('stat-total').textContent = DB.getAll('usuarios').length;
  document.getElementById('stat-admin').textContent = DB.getAll('usuarios').filter((u) => u.rol === 'admin').length;
  document.getElementById('stat-empleado').textContent = DB.getAll('usuarios').filter((u) => u.rol === 'empleado').length;
  document.getElementById('stat-cliente').textContent = DB.getAll('usuarios').filter((u) => u.rol === 'cliente').length;

  if (rows.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="5">No hay usuarios que coincidan con la búsqueda.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map((u) => {
    const rolInfo = ROL_BADGE[u.rol] || { label: u.rol, cls: 'blue' };
    const estadoInfo = ESTADO_BADGE[u.estado] || { label: u.estado, cls: 'green' };
    return `
      <tr>
        <td><div class="person"><div class="person-avatar">${initials(u.nombre)}</div>${u.nombre}</div></td>
        <td><span class="badge ${rolInfo.cls}">${rolInfo.label}</span></td>
        <td>${u.email}</td>
        <td><span class="badge ${estadoInfo.cls}">${estadoInfo.label}</span></td>
        <td><div class="row-actions">
          <button class="icon-btn" data-edit="${u.id}" title="Editar">✎</button>
          <button class="icon-btn" data-delete="${u.id}" title="Eliminar">${ICON_TRASH}</button>
        </div></td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('[data-edit]').forEach((btn) => {
    btn.addEventListener('click', () => openUsuarioForm(btn.dataset.edit));
  });
  tbody.querySelectorAll('[data-delete]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const u = DB.getById('usuarios', btn.dataset.delete);
      confirmDeleteModal({
        message: `¿Eliminar la cuenta de "${u.nombre}"? Esta acción no se puede deshacer.`,
        onConfirm: () => {
          DB.remove('usuarios', btn.dataset.delete);
          renderUsuarios();
          showToast('Usuario eliminado');
        },
      });
    });
  });
}

function openUsuarioForm(id) {
  const editing = id ? DB.getById('usuarios', id) : null;
  openFormModal({
    title: editing ? 'Editar usuario' : 'Nuevo usuario',
    submitLabel: editing ? 'Guardar cambios' : 'Crear usuario',
    initial: editing || { estado: 'activo', rol: 'cliente' },
    fields: [
      { name: 'nombre', label: 'Nombre completo', type: 'text', required: true },
      { name: 'email', label: 'Correo electrónico', type: 'email', required: true },
      { name: 'rol', label: 'Rol', type: 'select', required: true, options: [
        { value: 'admin', label: 'Administrador' },
        { value: 'empleado', label: 'Empleado' },
        { value: 'cliente', label: 'Cliente' },
      ] },
      { name: 'estado', label: 'Estado', type: 'select', required: true, options: [
        { value: 'activo', label: 'Activo' },
        { value: 'inactivo', label: 'Inactivo' },
        { value: 'suspendida', label: 'Suspendida' },
      ] },
    ],
    onSubmit: (data) => {
      if (editing) {
        DB.update('usuarios', editing.id, data);
        showToast('Usuario actualizado');
      } else {
        DB.insert('usuarios', data);
        showToast('Usuario creado');
      }
      renderUsuarios();
    },
  });
}

  renderUsuarios();
  document.getElementById('btn-nuevo-usuario').addEventListener('click', () => openUsuarioForm(null));
  document.getElementById('filter-rol').addEventListener('change', renderUsuarios);
  document.getElementById('search-usuarios').addEventListener('input', renderUsuarios);
})();
