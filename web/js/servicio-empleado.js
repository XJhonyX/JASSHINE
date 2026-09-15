(function(){
// JASSHINE — Cola de servicio (panel empleado): iniciar y finalizar lavados
// (EMPLEADO_DEMO_ID se define en js/db.js)

function renderColaServicio() {
  const todos = DB.getAll('servicios').filter((s) => s.id_empleado === EMPLEADO_DEMO_ID);
  const espera = todos.filter((s) => s.estado === 'En espera');
  const curso = todos.filter((s) => s.estado === 'En curso');

  document.getElementById('badge-cola-count').textContent = `${espera.length + curso.length} en turno`;

  const espera_el = document.getElementById('cola-espera');
  espera_el.innerHTML = espera.length === 0
    ? `<div class="empty-row" style="padding:22px 0;">No tienes motos en espera.</div>`
    : espera.map((s) => {
        const tipo = DB.getById('tiposervicio', s.id_tipo_servicio);
        return `
          <div class="queue-card">
            <div class="person"><div class="person-avatar">🏍</div><div><div class="plate">${s.placa}</div><div class="person-sub">${tipo ? tipo.nombre : ''} · ${s.cliente}</div></div></div>
            <button class="btn btn-primary btn-sm" data-iniciar="${s.id}">Iniciar lavado</button>
          </div>`;
      }).join('');

  const curso_el = document.getElementById('cola-curso');
  curso_el.innerHTML = curso.length === 0
    ? `<div class="empty-row" style="padding:22px 0;">No tienes ningún lavado en curso.</div>`
    : curso.map((s) => {
        const tipo = DB.getById('tiposervicio', s.id_tipo_servicio);
        return `
          <div class="queue-card">
            <div class="person"><div class="person-avatar">🏍</div><div><div class="plate">${s.placa}</div><div class="person-sub">${tipo ? tipo.nombre : ''} · en curso</div></div></div>
            <button class="btn btn-sm" data-finalizar="${s.id}">Marcar finalizado</button>
          </div>`;
      }).join('');

  document.querySelectorAll('[data-iniciar]').forEach((btn) => {
    btn.addEventListener('click', () => {
      DB.update('servicios', btn.dataset.iniciar, { estado: 'En curso' });
      renderColaServicio();
      showToast('Lavado iniciado');
    });
  });
  document.querySelectorAll('[data-finalizar]').forEach((btn) => {
    btn.addEventListener('click', () => {
      DB.update('servicios', btn.dataset.finalizar, { estado: 'Completado' });
      renderColaServicio();
      showToast('Lavado finalizado ✓');
    });
  });
}

renderColaServicio();
})();
