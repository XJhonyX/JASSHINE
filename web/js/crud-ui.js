// JASSHINE — Modal reutilizable para formularios CRUD (crear/editar/borrar)

const ICON_TRASH = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>';


function crudModalRoot() {
  let root = document.getElementById('crud-modal-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'crud-modal-root';
    document.body.appendChild(root);
  }
  return root;
}

function closeCrudModal() {
  const root = crudModalRoot();
  root.innerHTML = '';
}

// fields: [{ name, label, type: 'text'|'email'|'number'|'select'|'textarea', options?: [{value,label}], required?: bool }]
function openFormModal({ title, fields, initial = {}, submitLabel = 'Guardar', onSubmit }) {
  const root = crudModalRoot();

  const fieldsHtml = fields.map((f) => {
    const val = initial[f.name] !== undefined ? initial[f.name] : '';
    if (f.type === 'select') {
      const opts = f.options.map((o) =>
        `<option value="${o.value}" ${String(o.value) === String(val) ? 'selected' : ''}>${o.label}</option>`
      ).join('');
      return `<div class="field"><label>${f.label}</label><select name="${f.name}" ${f.required ? 'required' : ''}>${opts}</select></div>`;
    }
    if (f.type === 'textarea') {
      return `<div class="field"><label>${f.label}</label><textarea name="${f.name}" ${f.required ? 'required' : ''}>${val}</textarea></div>`;
    }
    return `<div class="field"><label>${f.label}</label><input type="${f.type || 'text'}" name="${f.name}" value="${val}" ${f.required ? 'required' : ''}></div>`;
  }).join('');

  root.innerHTML = `
    <div class="crud-backdrop">
      <div class="crud-dialog">
        <div class="crud-dialog-head">
          <h3>${title}</h3>
          <button type="button" class="crud-close" aria-label="Cerrar">✕</button>
        </div>
        <form class="crud-form">
          ${fieldsHtml}
          <div class="crud-dialog-actions">
            <button type="button" class="btn crud-cancel">Cancelar</button>
            <button type="submit" class="btn btn-primary">${submitLabel}</button>
          </div>
        </form>
      </div>
    </div>
  `;

  const backdrop = root.querySelector('.crud-backdrop');
  const form = root.querySelector('.crud-form');
  root.querySelector('.crud-close').addEventListener('click', closeCrudModal);
  root.querySelector('.crud-cancel').addEventListener('click', closeCrudModal);
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeCrudModal(); });

  form.addEventListener('submit', (e) => {
    e.preventDefault();
    const data = {};
    fields.forEach((f) => {
      const el = form.elements[f.name];
      data[f.name] = f.type === 'number' ? Number(el.value) : el.value;
    });
    onSubmit(data);
    closeCrudModal();
  });
}

function confirmDeleteModal({ message, onConfirm }) {
  const root = crudModalRoot();
  root.innerHTML = `
    <div class="crud-backdrop">
      <div class="crud-dialog crud-dialog-sm">
        <div class="crud-dialog-head">
          <h3>Confirmar</h3>
          <button type="button" class="crud-close" aria-label="Cerrar">✕</button>
        </div>
        <p class="crud-confirm-msg">${message}</p>
        <div class="crud-dialog-actions">
          <button type="button" class="btn crud-cancel">Cancelar</button>
          <button type="button" class="btn crud-danger">Eliminar</button>
        </div>
      </div>
    </div>
  `;
  const backdrop = root.querySelector('.crud-backdrop');
  root.querySelector('.crud-close').addEventListener('click', closeCrudModal);
  root.querySelector('.crud-cancel').addEventListener('click', closeCrudModal);
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeCrudModal(); });
  root.querySelector('.crud-danger').addEventListener('click', () => {
    onConfirm();
    closeCrudModal();
  });
}

function showToast(message) {
  let toast = document.getElementById('crud-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'crud-toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 2200);
}

// Activa el click en cualquier .toggle[data-toggle] de la página (on/off visual).
// Devuelve un objeto {clave: true/false} con el estado actual de cada uno.
function wireToggles() {
  const state = {};
  document.querySelectorAll('.toggle[data-toggle]').forEach((el) => {
    state[el.dataset.toggle] = el.classList.contains('on');
    el.addEventListener('click', () => {
      el.classList.toggle('on');
      state[el.dataset.toggle] = el.classList.contains('on');
    });
  });
  return state;
}
