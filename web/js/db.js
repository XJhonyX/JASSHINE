// JASSHINE — Capa de datos local (simula la base de datos)
//
// Mientras no exista el backend real, esta "base de datos" vive en el
// localStorage del navegador. Las tablas y campos siguen el mismo esquema
// del script SQL (Usuario, Cliente, Empleado, TipoServicio, Reserva,
// Servicio, Comision, Recibo) para que, cuando construyamos el backend,
// cambiar DB.* por llamadas fetch() a la API sea lo más parecido posible.
//
// Uso básico:
//   DB.getAll('empleados')
//   DB.insert('empleados', {nombre:'...', email:'...'})
//   DB.update('empleados', id, {estado:'inactivo'})
//   DB.remove('empleados', id)

// Identidad de la sesión de demostración (mientras no hay login real conectado al backend)
const CLIENTE_DEMO_NOMBRE = 'Juan Esteban Torres';
const CLIENTE_DEMO_ID = 1; // id en la tabla "clientes" de este mismo archivo
const EMPLEADO_DEMO_ID = 1; // Juan Esteban (id en la tabla "empleados" de este mismo archivo)

const DB_KEY = 'jasshine_db_v1';

const DB_SEED = {
  usuarios: [
    { id: 1, nombre: 'Admin Principal', email: 'admin@jasshine.co', rol: 'admin', estado: 'activo' },
    { id: 2, nombre: 'Juan Esteban', email: 'juan@jasshine.co', rol: 'empleado', estado: 'activo' },
    { id: 3, nombre: 'Santiago Ariza', email: 'santiago@jasshine.co', rol: 'empleado', estado: 'activo' },
    { id: 4, nombre: 'David Andrade', email: 'david@jasshine.co', rol: 'empleado', estado: 'activo' },
    { id: 5, nombre: 'Maria Alejandra', email: 'maria@jasshine.co', rol: 'empleado', estado: 'activo' },
    { id: 6, nombre: 'Camila Rojas', email: 'camila@jasshine.co', rol: 'empleado', estado: 'activo' },
    { id: 7, nombre: 'Luis Peña', email: 'luis@jasshine.co', rol: 'empleado', estado: 'inactivo' },
    { id: 8, nombre: 'Juan Esteban Torres', email: 'juan.torres@correo.com', rol: 'cliente', estado: 'activo' },
    { id: 9, nombre: 'Laura Nieto', email: 'laura.nieto@correo.com', rol: 'cliente', estado: 'activo' },
    { id: 10, nombre: 'Sara Molano', email: 'sara.molano@correo.com', rol: 'cliente', estado: 'suspendida' },
  ],
  empleados: [
    { id: 1, id_usuario: 2, nombre: 'Juan Esteban', email: 'juan@jasshine.co', telefono: '+57 311 234 5678', cargo: 'Lavador senior', estado: 'Disponible' },
    { id: 2, id_usuario: 3, nombre: 'Santiago Ariza', email: 'santiago@jasshine.co', telefono: '+57 300 456 7812', cargo: 'Lavador', estado: 'En servicio' },
    { id: 3, id_usuario: 4, nombre: 'David Andrade', email: 'david@jasshine.co', telefono: '+57 315 908 2231', cargo: 'Lavador', estado: 'Disponible' },
    { id: 4, id_usuario: 5, nombre: 'Maria Alejandra', email: 'maria@jasshine.co', telefono: '+57 320 118 4470', cargo: 'Lavadora senior', estado: 'Descansando' },
    { id: 5, id_usuario: 6, nombre: 'Camila Rojas', email: 'camila@jasshine.co', telefono: '+57 301 774 9902', cargo: 'Pulido y detallado', estado: 'Disponible' },
    { id: 6, id_usuario: 7, nombre: 'Luis Peña', email: 'luis@jasshine.co', telefono: '+57 312 665 3390', cargo: 'Lavador', estado: 'Inactivo' },
  ],
  tiposervicio: [
    { id: 1, nombre: 'Lavado básico', descripcion: 'Exterior completo', precio: 8000, duracion_min: 20 },
    { id: 2, nombre: 'Lavado completo', descripcion: 'Exterior + interior', precio: 15000, duracion_min: 35 },
    { id: 3, nombre: 'Lavado + Pulido', descripcion: 'Brillo de todas las piezas', precio: 22000, duracion_min: 55 },
    { id: 4, nombre: 'Lavado Full', descripcion: 'Interior, exterior y pulida', precio: 25000, duracion_min: 70 },
  ],
  reservas: [
    { id: 1, cliente: 'Juan Esteban Torres', placa: 'WPQ 341', id_tipo_servicio: 2, id_empleado: 1, fecha: '2026-05-25', hora: '15:00', estado: 'Confirmada' },
    { id: 2, cliente: 'Laura Nieto', placa: 'LMN 565', id_tipo_servicio: 4, id_empleado: 4, fecha: '2026-05-25', hora: '13:15', estado: 'Completada' },
    { id: 3, cliente: 'Sara Molano', placa: 'ABC 123', id_tipo_servicio: 3, id_empleado: 5, fecha: '2026-05-25', hora: '11:00', estado: 'Completada' },
  ],
  servicios: [
    { id: 1, placa: 'LMN 565', cliente: 'Laura Nieto', id_tipo_servicio: 4, id_empleado: 1, estado: 'En espera' },
    { id: 2, placa: 'TQY 771', cliente: 'Camilo Duarte', id_tipo_servicio: 2, id_empleado: 1, estado: 'En espera' },
    { id: 3, placa: 'ABC 123', cliente: 'Sara Molano', id_tipo_servicio: 3, id_empleado: 1, estado: 'En curso' },
  ],
  clientes: [
    { id: 1, nombre: 'Juan Esteban Torres', email: 'juan.torres@correo.com', telefono: '+57 300 987 6543', moto: 'Yamaha MT-03 · Placa WPQ 341' },
  ],
  negocio: [
    { id: 1, nombre: 'JASSHINE — Lavadero Inteligente', correo: 'contacto@jasshine.co', telefono: '+57 311 234 5678', direccion: 'Cra 45 #12-30, Bogotá' },
  ],
};

function loadDB() {
  const raw = localStorage.getItem(DB_KEY);
  if (raw) {
    try { return JSON.parse(raw); } catch (e) { /* corrupto, se reinicia abajo */ }
  }
  saveDB(DB_SEED);
  return JSON.parse(JSON.stringify(DB_SEED));
}

function saveDB(db) {
  localStorage.setItem(DB_KEY, JSON.stringify(db));
}

const DB = {
  getAll(table) {
    const db = loadDB();
    return db[table] ? [...db[table]] : [];
  },
  getById(table, id) {
    return this.getAll(table).find((r) => String(r.id) === String(id)) || null;
  },
  insert(table, obj) {
    const db = loadDB();
    if (!db[table]) db[table] = [];
    const nextId = db[table].reduce((max, r) => Math.max(max, r.id), 0) + 1;
    const row = { id: nextId, ...obj };
    db[table].push(row);
    saveDB(db);
    return row;
  },
  update(table, id, changes) {
    const db = loadDB();
    const idx = (db[table] || []).findIndex((r) => String(r.id) === String(id));
    if (idx === -1) return null;
    db[table][idx] = { ...db[table][idx], ...changes };
    saveDB(db);
    return db[table][idx];
  },
  remove(table, id) {
    const db = loadDB();
    db[table] = (db[table] || []).filter((r) => String(r.id) !== String(id));
    saveDB(db);
  },
  // Reinicia SOLO esta "base de datos" del navegador a los datos de ejemplo originales.
  reset() {
    saveDB(DB_SEED);
  },
};
