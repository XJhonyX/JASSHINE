# JASSHINE — Lavadero Inteligente

Aplicación web en Python / Flask con persistencia en MongoDB Atlas. Los documentos se guardan en colecciones independientes (`usuarios`, `clientes`, `vehiculos`, `empleados`, `tipos_servicio`, `reservas`, `servicios`, `comisiones`, `recibos`, `negocio` y `preferencias`).

El proyecto separa el código del servidor en `backend/jasshine/` y la interfaz en `frontend/`: las plantillas HTML están en `frontend/templates/` y los estilos, scripts e imágenes en `frontend/static/`. Flask sigue renderizando las páginas y sirviendo sus recursos, por lo que la aplicación conserva el mismo funcionamiento y no requiere un servidor frontend independiente.

## Conectar MongoDB Atlas

1. En MongoDB Atlas crea un clúster, un usuario de base de datos y autoriza la IP del servidor donde publicarás la app en **Network Access**.
2. En **Connect → Drivers**, copia la URI de Python y reemplaza el usuario, contraseña y nombre de base de datos. No publiques ni subas esa URI al repositorio.
3. Configura estas variables en el servicio de hosting (por ejemplo, en su panel **Environment Variables / Secrets**):
   * `MONGODB_URI`: URI completa `mongodb+srv://...` de Atlas.
   * `MONGODB_DB`: nombre de la base, por ejemplo `jasshine` (opcional; ese es el valor predeterminado).
   * `JASSHINE_SECRET`: clave larga y aleatoria para firmar las sesiones.
4. Instala las dependencias con `pip install -r requirements.txt` y ejecuta `python app.py` o usa un servidor WSGI como Waitress/Gunicorn.

La aplicación crea índices y colecciones al iniciar; si la base está vacía, agrega los datos iniciales y la cuenta `admin@jasshine.co`. Cambia la contraseña inicial desde **Configuración → Seguridad**. Si falta `MONGODB_URI`, el inicio falla con un mensaje explícito en vez de guardar datos en una base local.

Para desarrollo local en Windows PowerShell, define las variables antes de ejecutarla:

```powershell
$env:MONGODB_URI = "mongodb+srv://USUARIO:CONTRASENA@CLUSTER.mongodb.net/?retryWrites=true&w=majority"
$env:MONGODB_DB = "jasshine"
$env:JASSHINE_SECRET = "reemplaza-por-una-clave-aleatoria-larga"
python app.py
```

Si la contraseña contiene caracteres reservados de URI, codifícalos para URL. Mantén `MONGODB_URI` como secreto del hosting; no la escribas en `app.py`, en este archivo ni en Git.

## Cómo iniciar

Con `MONGODB_URI` configurada, ejecuta `iniciar.bat` o:

```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Abre http://127.0.0.1:5000.

## Cuentas

* Al registrarte se crea tu cuenta de cliente y queda con la sesión iniciada.
* El administrador inicial es `admin@jasshine.co` con contraseña `Admin12345`; cámbiala al entrar.
* El administrador crea empleados en **Empleados**. El equipo de ejemplo no tiene contraseña hasta que se le asigne una.
* Las contraseñas se almacenan con hash y los formularios están protegidos contra CSRF.

## Funciones

La aplicación conserva login, sesión, CRUD, agenda, cola de lavados, comisiones y recibos. Al finalizar un lavado, calcula la comisión (18 %) y genera el recibo.

| Antes (JS) | Ahora (Python) |
|---|---|
| `db.js` (base local en el navegador) | `backend/jasshine/models.py` + MongoDB Atlas |
| `auth.js`, `login.js`, `registro.js`, `recuperar.js` | `backend/jasshine/security.py`, `backend/jasshine/views/auth.py` |
| `usuarios-admin.js` | `backend/jasshine/views/usuarios.py` |
| `empleados-admin.js` | `backend/jasshine/views/empleados.py` |
| `servicios-admin.js`, `servicio-cliente.js`, `servicio-empleado.js` | `backend/jasshine/views/servicio.py` + `backend/jasshine/logic.py` |
| `agenda-admin.js`, `agenda-cliente.js` | `backend/jasshine/views/agenda.py` |
| `configuracion-*.js` | `backend/jasshine/views/configuracion.py` |

## Pruebas

```powershell
pip install -r requirements-dev.txt
python -m pytest -q
```

Las pruebas usan una base MongoDB simulada y aislada por prueba; no necesitan acceder a Atlas.

## Publicación

Define `MONGODB_URI`, `MONGODB_DB` y `JASSHINE_SECRET` en el panel seguro del hosting, autoriza la IP de salida del servidor en Atlas, activa HTTPS y ejecuta Flask detrás de un servidor WSGI. No incluyas credenciales en el repositorio.
