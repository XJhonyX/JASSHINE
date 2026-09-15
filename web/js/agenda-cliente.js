(function(){
// JASSHINE — Mi agenda (panel cliente): lee reservas reales y permite cancelar

function renderMisCitas() {
  const list = document.getElementById('mis-citas-list');
  const rows = DB.getAll('reservas')
    .filter((r) => r.cliente === CLIENTE_DEMO_NOMBRE)
    .sort((a, b) => (b.fecha + b.hora).localeCompare(a.fecha + a.hora));

  if (rows.length === 0) {
    list.innerHTML = `<div class="empty-row" style="padding:28px 0;">Todavía no tienes citas agendadas. Ve a "Servicio" para reservar una.</div>`;
    return;
  }

  list.innerHTML = rows.map((r) => {
    const tipo = DB.getById('tiposervicio', r.id_tipo_servicio);
    const badgeCls = RESERVA_ESTADO_BADGE_CLIENTE[r.estado] || 'blue';
    const [dia, mesTxt] = fechaCorta(r.fecha);
    const puedeCancel = r.estado !== 'Cancelada' && r.estado !== 'Completada';
    return `
      <div class="appt-card">
        <div class="appt-date"><b>${dia}</b><span>${mesTxt}</span></div>
        <div style="flex:1;">
          <div class="person-name">${tipo ? tipo.nombre : 'Servicio'} · ${r.hora}</div>
          <div class="person-sub">${r.placa} · ${tipo ? '$' + tipo.precio.toLocaleString('es-CO') : ''}</div>
        </div>
        <span class="badge ${badgeCls}">${r.estado}</span>
        ${puedeCancel ? `<button class="icon-btn" data-cancel="${r.id}" title="Cancelar cita" style="margin-left:10px;">${ICON_TRASH}</button>` : ''}
      </div>`;
  }).join('');

  list.querySelectorAll('[data-cancel]').forEach((btn) => {
    btn.addEventListener('click', () => {
      confirmDeleteModal({
        message: '¿Cancelar esta cita?',
        onConfirm: () => {
          DB.update('reservas', btn.dataset.cancel, { estado: 'Cancelada' });
          renderMisCitas();
          showToast('Cita cancelada');
        },
      });
    });
  });
}

const RESERVA_ESTADO_BADGE_CLIENTE = {
  'Pendiente': 'orange',
  'Confirmada': 'blue',
  'Completada': 'green',
  'Cancelada': 'red',
};

const MESES = ['Ene','Feb','Mar','Abr','May','Jun','Jul','Ago','Sep','Oct','Nov','Dic'];
function fechaCorta(fechaISO) {
  const d = new Date(fechaISO + 'T00:00:00');
  if (isNaN(d)) return [fechaISO, ''];
  return [String(d.getDate()).padStart(2, '0'), MESES[d.getMonth()]];
}

renderMisCitas();
})();
