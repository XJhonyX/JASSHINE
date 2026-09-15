(function(){
// JASSHINE — CRUD de Agenda / Reservas (panel administrador)

const RESERVA_ESTADO_BADGE = {
  'Pendiente': 'orange',
  'Confirmada': 'blue',
  'Completada': 'green',
  'Cancelada': 'red',
};

function nombreTipoServicio(id) {
  const t = DB.getById('tiposervicio', id);
  return t ? t.nombre : '—';
}
function nombreEmpleado(id) {
  const e = DB.getById('empleados', id);
  return e ? e.nombre : 'Sin asignar';
}

function renderReservas() {
  const tbody = document.getElementById('reservas-tbody');
  const rows = DB.getAll('reservas').sort((a, b) => (a.fecha + a.hora).localeCompare(b.fecha + b.hora));
  document.getElementById('agenda-fecha').textContent = `Reservas · ${rows.length} en total`;

  if (rows.length === 0) {
    tbody.innerHTML = `<tr class="empty-row"><td colspan="8">No hay citas agendadas todavía.</td></tr>`;
    return;
  }

  tbody.innerHTML = rows.map((r) => {
    const badgeCls = RESERVA_ESTADO_BADGE[r.estado] || 'blue';
    return `
      <tr>
        <td>${r.fecha}</td>
        <td>${r.hora}</td>
        <td>${r.cliente}</td>
        <td>${r.placa}</td>
        <td>${nombreTipoServicio(r.id_tipo_servicio)}</td>
        <td>${nombreEmpleado(r.id_empleado)}</td>
        <td><span class="badge ${badgeCls}">${r.estado}</span></td>
        <td><div class="row-actions">
          <button class="icon-btn" data-edit="${r.id}" title="Editar">✎</button>
          <button class="icon-btn" data-delete="${r.id}" title="Cancelar">${ICON_TRASH}</button>
        </div></td>
      </tr>`;
  }).join('');

  tbody.querySelectorAll('[data-edit]').forEach((btn) => {
    btn.addEventListener('click', () => openReservaForm(btn.dataset.edit));
  });
  tbody.querySelectorAll('[data-delete]').forEach((btn) => {
    btn.addEventListener('click', () => {
      confirmDeleteModal({
        message: '¿Cancelar y eliminar esta cita de la agenda?',
        onConfirm: () => {
          DB.remove('reservas', btn.dataset.delete);
          renderReservas();
          showToast('Cita eliminada');
        },
      });
    });
  });
}

function openReservaForm(id) {
  const editing = id ? DB.getById('reservas', id) : null;
  const tipos = DB.getAll('tiposervicio').map((t) => ({ value: t.id, label: t.nombre }));
  const empleados = [{ value: '', label: 'Sin asignar' }, ...DB.getAll('empleados').map((e) => ({ value: e.id, label: e.nombre }))];

  openFormModal({
    title: editing ? 'Editar cita' : 'Nueva cita',
    submitLabel: editing ? 'Guardar cambios' : 'Crear cita',
    initial: editing || { fecha: '2026-05-25', estado: 'Pendiente' },
    fields: [
      { name: 'cliente', label: 'Cliente', type: 'text', required: true },
      { name: 'placa', label: 'Placa del vehículo', type: 'text', required: true },
      { name: 'id_tipo_servicio', label: 'Servicio', type: 'select', required: true, options: tipos },
      { name: 'id_empleado', label: 'Empleado asignado', type: 'select', options: empleados },
      { name: 'fecha', label: 'Fecha', type: 'text', required: true },
      { name: 'hora', label: 'Hora', type: 'text', required: true },
      { name: 'estado', label: 'Estado', type: 'select', required: true, options: [
        { value: 'Pendiente', label: 'Pendiente' },
        { value: 'Confirmada', label: 'Confirmada' },
        { value: 'Completada', label: 'Completada' },
        { value: 'Cancelada', label: 'Cancelada' },
      ] },
    ],
    onSubmit: (data) => {
      data.id_tipo_servicio = Number(data.id_tipo_servicio);
      data.id_empleado = data.id_empleado ? Number(data.id_empleado) : null;
      if (editing) {
        DB.update('reservas', editing.id, data);
        showToast('Cita actualizada');
      } else {
        DB.insert('reservas', data);
        showToast('Cita creada');
      }
      renderReservas();
    },
  });
}

  renderReservas();
  document.getElementById('btn-nueva-cita').addEventListener('click', () => openReservaForm(null));
})();
