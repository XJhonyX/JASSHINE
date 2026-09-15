(function(){
// JASSHINE — Agendar servicio (panel cliente) → crea una Reserva real,
// con selección de lavador y asignación automática según su disponibilidad.
// (CLIENTE_DEMO_NOMBRE se define en js/db.js, compartido entre páginas de cliente)

let servicioSeleccionado = null;
let empleadoSeleccionadoId = null; // null = "Cualquiera disponible"

// Estados en los que el empleado SÍ está trabajando hoy ("en operación").
// Dentro de esos, "Disponible" = libre ahora mismo; "En servicio" = ocupado
// pero en turno. "Descansando"/"Inactivo" = no está operando hoy.
const EN_OPERACION = ['Disponible', 'En servicio'];

function formatCOP2(n) {
  return '$' + Number(n).toLocaleString('es-CO');
}

const TIPO_ICONS = {
  'Lavado básico': '🏍️',
  'Lavado completo': '💧',
  'Lavado + Pulido': '✨',
  'Lavado Full': '🏆',
};

function renderTiposServicioCliente() {
  const list = document.getElementById('tipos-servicio-list');
  const tipos = DB.getAll('tiposervicio');

  list.innerHTML = tipos.map((t) => `
    <div class="tipo-card" data-id="${t.id}">
      <div class="tipo-icon">${TIPO_ICONS[t.nombre] || '🧴'}</div>
      <div class="tipo-name">${t.nombre}</div>
      <div class="tipo-desc">${t.descripcion || ''}</div>
      <div class="tipo-price">${formatCOP2(t.precio)}</div>
    </div>
  `).join('');

  list.querySelectorAll('.tipo-card').forEach((card) => {
    card.addEventListener('click', () => {
      list.querySelectorAll('.tipo-card').forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
      const t = DB.getById('tiposervicio', card.dataset.id);
      servicioSeleccionado = t;
      document.getElementById('resumen-precio').textContent = `${t.nombre} · ${formatCOP2(t.precio)}`;
    });
  });
}

const ESTADO_MINI_BADGE = {
  'Disponible': 'green',
  'En servicio': 'blue',
  'Descansando': 'orange',
  'Inactivo': 'red',
};

function initialsPick(nombre) {
  return nombre.split(' ').filter(Boolean).slice(0, 2).map((w) => w[0].toUpperCase()).join('');
}

function renderEmpleadosPicker() {
  const picker = document.getElementById('empleados-picker');
  const empleados = DB.getAll('empleados');

  const cualquieraCard = `
    <div class="staff-card selectable selected" data-id="">
      <div class="staff-avatar">✓</div>
      <div class="staff-name">Cualquiera</div>
      <div class="staff-role">disponible</div>
    </div>`;

  const empleadoCards = empleados.map((e) => {
    const enOperacion = EN_OPERACION.includes(e.estado);
    const cls = enOperacion ? 'staff-card selectable' : 'staff-card disabled';
    const badge = ESTADO_MINI_BADGE[e.estado] || 'green';
    return `
      <div class="${cls}" data-id="${e.id}" ${enOperacion ? '' : 'title="No está operando hoy"'}>
        <div class="staff-avatar">${initialsPick(e.nombre)}</div>
        <div class="staff-name">${e.nombre}</div>
        <div class="staff-role">${e.cargo}</div>
        <span class="mini-badge ${badge}">${e.estado}</span>
      </div>`;
  }).join('');

  picker.innerHTML = cualquieraCard + empleadoCards;

  picker.querySelectorAll('.staff-card.selectable').forEach((card) => {
    card.addEventListener('click', () => {
      picker.querySelectorAll('.staff-card').forEach((c) => c.classList.remove('selected'));
      card.classList.add('selected');
      empleadoSeleccionadoId = card.dataset.id ? Number(card.dataset.id) : null;
      updateEmpleadoHint();
    });
  });

  updateEmpleadoHint();
}

function updateEmpleadoHint() {
  const hint = document.getElementById('empleado-hint');
  if (empleadoSeleccionadoId === null) {
    hint.textContent = 'Se asignará el primer lavador que quede libre.';
    return;
  }
  const e = DB.getById('empleados', empleadoSeleccionadoId);
  if (e.estado === 'Disponible') {
    hint.textContent = `${e.nombre} está libre ahora — tu cita se le asigna y confirma de una vez.`;
  } else {
    hint.textContent = `${e.nombre} está en servicio en este momento — tu cita entra en su cola y la iniciará en cuanto termine.`;
  }
}

renderTiposServicioCliente();
renderEmpleadosPicker();

document.getElementById('btn-confirmar-cita').addEventListener('click', () => {
  const placa = document.getElementById('input-placa').value.trim();
  const fecha = document.getElementById('input-fecha').value;
  const hora = document.getElementById('input-hora').value;

  if (!servicioSeleccionado) { showToast('Elige un tipo de servicio'); return; }
  if (!placa || !fecha || !hora) { showToast('Completa placa, fecha y hora'); return; }

  let estadoReserva = 'Pendiente';
  let mensaje = '¡Cita agendada con éxito!';

  if (empleadoSeleccionadoId !== null) {
    const empleado = DB.getById('empleados', empleadoSeleccionadoId);

    if (!EN_OPERACION.includes(empleado.estado)) {
      // Defensivo: esta tarjeta debería estar deshabilitada, pero por si acaso.
      showToast(`${empleado.nombre} no está operando hoy. Elige otro lavador.`);
      return;
    }

    if (empleado.estado === 'Disponible') {
      // Libre y en operación -> se asigna de una vez y queda aceptada.
      estadoReserva = 'Confirmada';
      mensaje = `¡Listo! ${empleado.nombre} aceptó tu cita de inmediato.`;
    } else {
      // En operación pero ocupado -> entra en su cola para después.
      estadoReserva = 'Pendiente';
      mensaje = `Tu cita quedó en la cola de ${empleado.nombre}. La iniciará cuando termine su lavado actual.`;
    }

    // En ambos casos (libre u ocupado pero en turno) la cita entra a la cola
    // de servicio del empleado; él la marca "Iniciar lavado" cuando le toque.
    DB.insert('servicios', {
      placa,
      cliente: CLIENTE_DEMO_NOMBRE,
      id_tipo_servicio: servicioSeleccionado.id,
      id_empleado: empleadoSeleccionadoId,
      estado: 'En espera',
    });
  }

  DB.insert('reservas', {
    cliente: CLIENTE_DEMO_NOMBRE,
    placa,
    id_tipo_servicio: servicioSeleccionado.id,
    id_empleado: empleadoSeleccionadoId,
    fecha,
    hora,
    estado: estadoReserva,
  });

  showToast(mensaje);
  setTimeout(() => { window.location.href = '../agenda/agenda-cliente.html'; }, 1100);
});
})();
