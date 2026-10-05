// JASSHINE — Modal reutilizable para formularios CRUD (crear/editar/borrar)
// Accesible: role="dialog", foco atrapado dentro del modal, Escape para
// cerrar, foco devuelto al botón que lo abrió, y labels conectados a sus
// campos con for/id.

const ICON_TRASH = '<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 6h18"/><path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/><path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6"/><path d="M10 11v6M14 11v6"/></svg>';

let lastFocusedBeforeModal = null;

function crudModalRoot() {
  let root = document.getElementById('crud-modal-root');
  if (!root) {
    root = document.createElement('div');
    root.id = 'crud-modal-root';
    document.body.appendChild(root);
  }
  return root;
}

function getFocusable(container) {
  return [...container.querySelectorAll('a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])')];
}

function trapFocus(e, dialog) {
  if (e.key !== 'Tab') return;
  const focusable = getFocusable(dialog);
  if (focusable.length === 0) return;
  const first = focusable[0];
  const last = focusable[focusable.length - 1];
  if (e.shiftKey && document.activeElement === first) {
    e.preventDefault();
    last.focus();
  } else if (!e.shiftKey && document.activeElement === last) {
    e.preventDefault();
    first.focus();
  }
}

function onModalKeydown(e) {
  const root = document.getElementById('crud-modal-root');
  const dialog = root && root.querySelector('.crud-dialog');
  if (!dialog) return;
  if (e.key === 'Escape') {
    e.preventDefault();
    closeCrudModal();
  } else {
    trapFocus(e, dialog);
  }
}

function closeCrudModal() {
  const root = crudModalRoot();
  root.innerHTML = '';
  document.removeEventListener('keydown', onModalKeydown);
  if (lastFocusedBeforeModal && document.contains(lastFocusedBeforeModal)) {
    lastFocusedBeforeModal.focus();
  }
  lastFocusedBeforeModal = null;
}

function openModalShell() {
  lastFocusedBeforeModal = document.activeElement;
  document.addEventListener('keydown', onModalKeydown);
}

// fields: [{ name, label, type: 'text'|'email'|'number'|'select'|'textarea', options?: [{value,label}], required?: bool }]
function openFormModal({ title, fields, initial = {}, submitLabel = 'Guardar', onSubmit }) {
  const root = crudModalRoot();

  const fieldsHtml = fields.map((f) => {
    const fieldId = `crud-field-${f.name}`;
    const val = initial[f.name] !== undefined ? initial[f.name] : '';
    if (f.type === 'select') {
      const opts = f.options.map((o) =>
        `<option value="${o.value}" ${String(o.value) === String(val) ? 'selected' : ''}>${o.label}</option>`
      ).join('');
      return `<div class="field"><label for="${fieldId}">${f.label}</label><select id="${fieldId}" name="${f.name}" ${f.required ? 'required' : ''}>${opts}</select></div>`;
    }
    if (f.type === 'textarea') {
      return `<div class="field"><label for="${fieldId}">${f.label}</label><textarea id="${fieldId}" name="${f.name}" ${f.required ? 'required' : ''}>${val}</textarea></div>`;
    }
    return `<div class="field"><label for="${fieldId}">${f.label}</label><input type="${f.type || 'text'}" id="${fieldId}" name="${f.name}" value="${val}" ${f.required ? 'required' : ''}></div>`;
  }).join('');

  root.innerHTML = `
    <div class="crud-backdrop">
      <div class="crud-dialog" role="dialog" aria-modal="true" aria-labelledby="crud-dialog-title">
        <div class="crud-dialog-head">
          <h3 id="crud-dialog-title">${title}</h3>
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

  openModalShell();

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

  const firstField = form.querySelector('input, select, textarea');
  if (firstField) firstField.focus();
}

function confirmDeleteModal({ message, onConfirm }) {
  const root = crudModalRoot();
  root.innerHTML = `
    <div class="crud-backdrop">
      <div class="crud-dialog crud-dialog-sm" role="dialog" aria-modal="true" aria-labelledby="crud-dialog-title" aria-describedby="crud-dialog-msg">
        <div class="crud-dialog-head">
          <h3 id="crud-dialog-title">Confirmar</h3>
          <button type="button" class="crud-close" aria-label="Cerrar">✕</button>
        </div>
        <p class="crud-confirm-msg" id="crud-dialog-msg">${message}</p>
        <div class="crud-dialog-actions">
          <button type="button" class="btn crud-cancel">Cancelar</button>
          <button type="button" class="btn crud-danger">Eliminar</button>
        </div>
      </div>
    </div>
  `;

  openModalShell();

  const backdrop = root.querySelector('.crud-backdrop');
  root.querySelector('.crud-close').addEventListener('click', closeCrudModal);
  root.querySelector('.crud-cancel').addEventListener('click', closeCrudModal);
  backdrop.addEventListener('click', (e) => { if (e.target === backdrop) closeCrudModal(); });
  root.querySelector('.crud-danger').addEventListener('click', () => {
    onConfirm();
    closeCrudModal();
  });

  root.querySelector('.crud-cancel').focus();
}

function showToast(message) {
  let toast = document.getElementById('crud-toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.id = 'crud-toast';
    toast.setAttribute('role', 'status');
    toast.setAttribute('aria-live', 'polite');
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 2200);
}

// Activa cualquier .toggle[data-toggle] de la página como un switch accesible
// (role="switch", aria-checked, operable con clic o con teclado: Espacio/Enter).
// Devuelve un objeto {clave: true/false} con el estado actual de cada uno.
function wireToggles() {
  const state = {};
  document.querySelectorAll('.toggle[data-toggle]').forEach((el) => {
    const isOn = el.classList.contains('on');
    state[el.dataset.toggle] = isOn;
    el.setAttribute('role', 'switch');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-checked', String(isOn));
    if (!el.hasAttribute('aria-label') && el.previousElementSibling) {
      const labelText = el.previousElementSibling.querySelector('.settings-label');
      if (labelText) el.setAttribute('aria-label', labelText.textContent.trim());
    }

    const toggle = () => {
      el.classList.toggle('on');
      const nowOn = el.classList.contains('on');
      el.setAttribute('aria-checked', String(nowOn));
      state[el.dataset.toggle] = nowOn;
    };
    el.addEventListener('click', toggle);
    el.addEventListener('keydown', (e) => {
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        toggle();
      }
    });
  });
  return state;
}
