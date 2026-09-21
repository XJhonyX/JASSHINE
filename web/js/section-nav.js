// JASSHINE — Navegación de secciones vía JS
//
// Intercepta los clics en los enlaces del sidebar (menos "Cerrar sesión", que
// sí debe salir del panel) y usa fetch() para traer la página de destino,
// reemplazando solo el topbar y el contenido en vez de recargar todo el sitio.
// Esto le da a cada "apartado" su propio archivo HTML dentro de /views/, pero
// el cambio de sección sigue sintiéndose instantáneo, como en una sola app.
//
// IMPORTANTE: fetch() a archivos locales (file://) está bloqueado por CORS en
// la mayoría de navegadores. Si eso pasa, el catch de abajo deja que el link
// funcione como una navegación normal (recarga completa) — el sitio sigue
// funcionando igual, solo sin la transición instantánea. Para tener la
// transición instantánea hay que servir la carpeta con un servidor local
// (por ejemplo `python -m http.server` o la extensión Live Server de VSCode)
// en vez de abrir el archivo directamente con doble clic.
//
// Páginas con CRUD (usuarios, empleados, servicios, agenda, configuración...)
// tienen su propio archivo .js que dibuja las tablas/formularios. Como el
// intercambio de arriba solo copia HTML (no vuelve a correr <script> por su
// cuenta), después de cada cambio de sección volvemos a inyectar el <script>
// propio de esa página para que su tabla se dibuje. db.js/crud-ui.js/
// section-nav.js NUNCA se reinyectan: ya están cargados una vez y sus
// variables "const" no se pueden declarar dos veces sin error.

const SHARED_SCRIPTS = ['db.js', 'crud-ui.js', 'section-nav.js'];

function runPageScripts(doc) {
  const scripts = [...doc.querySelectorAll('script[src]')]
    .map((s) => s.getAttribute('src'))
    .filter((src) => !SHARED_SCRIPTS.some((shared) => src.endsWith(shared)));

  scripts.forEach((src) => {
    const el = document.createElement('script');
    el.src = src;
    document.body.appendChild(el);
  });
}

// ---------- Menú móvil (sidebar tipo cajón en pantallas angostas) ----------
// El botón #menu-toggle vive DENTRO de .topbar, y .topbar se reemplaza en
// cada cambio de sección (ver arriba), así que el listener del botón usa
// delegación de eventos sobre document en vez de engancharse al botón
// directamente — así sigue funcionando después de cada swap.

function ensureBackdrop() {
  let bd = document.querySelector('.sidebar-backdrop');
  if (!bd) {
    bd = document.createElement('div');
    bd.className = 'sidebar-backdrop';
    document.body.appendChild(bd);
    bd.addEventListener('click', closeSidebar);
  }
  return bd;
}
function openSidebar() {
  document.querySelector('.sidebar')?.classList.add('open');
  ensureBackdrop().classList.add('show');
}
function closeSidebar() {
  document.querySelector('.sidebar')?.classList.remove('open');
  document.querySelector('.sidebar-backdrop')?.classList.remove('show');
}
document.addEventListener('click', (e) => {
  if (e.target.closest('#menu-toggle')) {
    e.preventDefault();
    const sidebar = document.querySelector('.sidebar');
    if (sidebar && sidebar.classList.contains('open')) closeSidebar();
    else openSidebar();
  }
});
window.addEventListener('resize', () => {
  if (window.innerWidth > 880) closeSidebar();
});

document.addEventListener('DOMContentLoaded', () => {
  const links = document.querySelectorAll('.sidebar .nav-item[href]');

  links.forEach((link) => {
    const href = link.getAttribute('href');
    // "Cerrar sesión" apunta a index.html (fuera del panel): navegación normal.
    if (!href || href.includes('index.html')) return;

    link.addEventListener('click', async (e) => {
      e.preventDefault();
      closeSidebar();
      try {
        const res = await fetch(href);
        if (!res.ok) throw new Error('No se pudo cargar ' + href);
        const html = await res.text();
        const doc = new DOMParser().parseFromString(html, 'text/html');

        const newTopbar = doc.querySelector('.topbar');
        const newContent = doc.querySelector('.content');
        if (!newTopbar || !newContent) throw new Error('Página de destino incompleta');

        document.querySelector('.topbar').innerHTML = newTopbar.innerHTML;
        document.querySelector('.content').innerHTML = newContent.innerHTML;
        document.title = doc.title;

        links.forEach((l) => l.classList.remove('active'));
        link.classList.add('active');

        history.pushState({ href }, '', href);

        runPageScripts(doc);
      } catch (err) {
        // Respaldo: si fetch falla (p. ej. por CORS al abrir el archivo
        // directamente), navegamos normalmente a la página de destino.
        window.location.href = href;
      }
    });
  });

  // Botón "atrás/adelante" del navegador: recargamos la URL guardada.
  window.addEventListener('popstate', (e) => {
    if (e.state && e.state.href) {
      window.location.href = e.state.href;
    }
  });
});
