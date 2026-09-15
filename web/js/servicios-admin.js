(function(){
// JASSHINE — CRUD del catálogo de servicios (TipoServicio)

function formatCOP(n) {
  return '$' + Number(n).toLocaleString('es-CO');
}

function renderTiposServicio() {
  const list = document.getElementById('tiposervicio-list');
  const rows = DB.getAll('tiposervicio');

  if (rows.length === 0) {
    list.innerHTML = `<div class="empty-row" style="padding:24px 0;">Aún no hay servicios en el catálogo.</div>`;
    return;
  }

  list.innerHTML = rows.map((s) => `
    <div class="service-row">
      <div>
        <div class="service-name">${s.nombre}</div>
        <div class="service-sub">${s.descripcion || ''} · ${s.duracion_min} min</div>
      </div>
      <div style="display:flex; align-items:center; gap:12px;">
        <b>${formatCOP(s.precio)}</b>
        <div class="row-actions">
          <button class="icon-btn" data-edit="${s.id}" title="Editar">✎</button>
          <button class="icon-btn" data-delete="${s.id}" title="Eliminar">${ICON_TRASH}</button>
        </div>
      </div>
    </div>
  `).join('');

  list.querySelectorAll('[data-edit]').forEach((btn) => {
    btn.addEventListener('click', () => openTipoServicioForm(btn.dataset.edit));
  });
  list.querySelectorAll('[data-delete]').forEach((btn) => {
    btn.addEventListener('click', () => {
      const s = DB.getById('tiposervicio', btn.dataset.delete);
      confirmDeleteModal({
        message: `¿Eliminar "${s.nombre}" del catálogo? Los servicios ya prestados con este tipo no se ven afectados.`,
        onConfirm: () => {
          DB.remove('tiposervicio', btn.dataset.delete);
          renderTiposServicio();
          showToast('Servicio eliminado del catálogo');
        },
      });
    });
  });
}

function openTipoServicioForm(id) {
  const editing = id ? DB.getById('tiposervicio', id) : null;
  openFormModal({
    title: editing ? 'Editar servicio' : 'Nuevo servicio',
    submitLabel: editing ? 'Guardar cambios' : 'Crear servicio',
    initial: editing || {},
    fields: [
      { name: 'nombre', label: 'Nombre del servicio', type: 'text', required: true },
      { name: 'descripcion', label: 'Descripción', type: 'text' },
      { name: 'precio', label: 'Precio (COP)', type: 'number', required: true },
      { name: 'duracion_min', label: 'Duración (minutos)', type: 'number', required: true },
    ],
    onSubmit: (data) => {
      if (editing) {
        DB.update('tiposervicio', editing.id, data);
        showToast('Servicio actualizado');
      } else {
        DB.insert('tiposervicio', data);
        showToast('Servicio agregado al catálogo');
      }
      renderTiposServicio();
    },
  });
}

  renderTiposServicio();
  document.getElementById('btn-nuevo-tiposervicio').addEventListener('click', () => openTipoServicioForm(null));
})();
