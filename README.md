# CitaFácil — Sistema de reservas con recordatorios por WhatsApp

> **Proyecto 1 · Tópicos Especiales II (Feature Sprint con IA).** Este repositorio es una copia de [gianca675/citafacil](https://github.com/gianca675/citafacil) sobre la que se desarrollaron 5 historias de usuario con una herramienta de IA de escritorio, trabajando los roles Developer / Reviewer / QA. Ver [`docs/AI_DEVELOPMENT_LOG.md`](docs/AI_DEVELOPMENT_LOG.md).

Aplicación **full-stack** para que pequeños negocios (barberías, peluquerías, clínicas, consultoras…) reciban reservas en línea y envíen **recordatorios automáticos por WhatsApp**.

Backend en **Python (FastAPI)** con base de datos **SQL**, API REST **documentada (Swagger)** e integración real con **Twilio**. Frontend liviano en **HTML/CSS/JS**: una página pública de reservas y un panel de administración.

> Proyecto de portafolio creado por **Giancarlos Alfaro** ([gianca675.github.io](https://gianca675.github.io)).

---

## Características

- **Reserva en 3 pasos**: el cliente elige servicio → día → hora libre, y deja su nombre y celular.
- **Sin choques de horario**: el motor de disponibilidad calcula los espacios libres según la duración de cada servicio y **evita el doble-booking**.
- **Recordatorios por WhatsApp**: envío automático (programado) X horas antes de la cita, además de confirmación al reservar.
- **Panel de administración**: estadísticas, gestión de reservas (confirmar / cancelar / realizar / eliminar) y de servicios (crear / activar / eliminar), protegido por token.
- **API REST documentada**: Swagger UI interactivo en `/docs`.
- **Validación de datos**: teléfonos chilenos normalizados a formato E.164, horarios de atención y días cerrados configurables.
- **Listo para desplegar**: Dockerfile, blueprint de Render y configuración por variables de entorno (SQLite en local → PostgreSQL en producción).

---

## Stack técnico

| Capa        | Tecnología |
|-------------|------------|
| Backend     | Python 3, FastAPI, SQLAlchemy, Pydantic |
| Base de datos | SQLite (local) · PostgreSQL (producción) |
| Notificaciones | Twilio API (WhatsApp) |
| Tareas programadas | APScheduler |
| Frontend    | HTML5, CSS3, JavaScript (sin framework) |
| Tests       | pytest |
| Despliegue  | Docker · Render |

---

## Demo

- **Reservas (frontend):** _añade aquí tu URL de GitHub Pages_
- **Panel admin:** `.../admin.html`
- **API + documentación:** _añade aquí tu URL de Render_ `/docs`

---

## Estructura

```
citafacil/
├── backend/
│   ├── app/
│   │   ├── main.py           # App FastAPI, CORS, programador de recordatorios
│   │   ├── config.py         # Configuración por variables de entorno
│   │   ├── database.py       # Conexión SQLAlchemy (SQLite/PostgreSQL)
│   │   ├── models.py         # Modelos: Service, Appointment
│   │   ├── schemas.py        # Esquemas Pydantic (validación)
│   │   ├── crud.py           # Operaciones de base de datos
│   │   ├── availability.py   # Motor de horarios + anti doble-booking
│   │   ├── notifications.py  # Envío de WhatsApp (Twilio)
│   │   ├── reminders.py      # Recordatorios automáticos
│   │   ├── auth.py           # Autenticación del panel admin
│   │   └── routers/          # Endpoints (público / admin)
│   ├── tests/                # Pruebas con pytest
│   ├── seed.py               # Datos de ejemplo (barbería)
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── index.html            # Página pública de reservas
│   └── admin.html            # Panel de administración
├── render.yaml               # Despliegue en Render (API + PostgreSQL)
└── README.md
```

---

## Ejecutar en local

Requisitos: Python 3.10+.

```bash
cd backend
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env          # ajusta ADMIN_TOKEN y lo que quieras
python seed.py                # carga servicios y citas de ejemplo (opcional)
python -m uvicorn app.main:app --reload
```

- API y documentación: <http://localhost:8000/docs>
- Frontend: abre `frontend/index.html` en el navegador (usa `http://localhost:8000` por defecto).
  Panel admin en `frontend/admin.html` (ingresa tu `ADMIN_TOKEN`).

> Sin credenciales de Twilio, la app corre en **modo demo**: los mensajes de WhatsApp se registran en el log en vez de enviarse.

---

## Endpoints principales

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET  | `/api/config` | Datos del negocio (nombre, horario) | — |
| GET  | `/api/services` | Servicios activos | — |
| GET  | `/api/availability?service_id=&date=` | Horarios libres de un día | — |
| POST | `/api/appointments` | Crear una reserva | — |
| GET  | `/api/admin/appointments` | Listar reservas (filtros) | Admin |
| PATCH| `/api/admin/appointments/{id}` | Cambiar estado | Admin |
| DELETE | `/api/admin/appointments/{id}` | Eliminar reserva | Admin |
| GET/POST/PUT/DELETE | `/api/admin/services` | Gestionar servicios | Admin |
| GET  | `/api/admin/stats` | Estadísticas | Admin |
| POST | `/api/admin/reminders/run` | Enviar recordatorios ahora | Admin |

### Endpoints agregados en el Feature Sprint

| Historia | Método | Ruta | Descripción | Auth |
|---|---|---|---|---|
| US2 | GET | `/api/calendar?service_id=&month=YYYY-MM` | Estado de cada día del mes: `available`, `full`, `closed`, `past` | — |
| US1 | POST | `/api/appointments` | Ahora acepta `payment` (tarjeta nueva, opcional `save`) o `use_saved_payment` | `X-Customer-Token` si usa tarjeta guardada |
| US1 | GET / DELETE | `/api/customers/me` | Ver u olvidar mis datos guardados (solo marca y últimos 4 dígitos) | `X-Customer-Token` |
| US4 | POST | `/api/appointments/cancel` | Cancelar con el código recibido al reservar | — |
| US3 | GET | `/api/admin/forecast?days=` | Histórico, promedio semanal y previsión de demanda con sugerencia de precio | Admin |
| US5 | GET | `/api/admin/appointments/export.csv` | Exporta las reservas (mismos filtros que el listado) | Admin |

Admin = requiere la cabecera `X-Admin-Token`.

### Pagos simulados (US1)

La pasarela es **simulada** (`backend/app/payments.py`): valida Luhn, vencimiento y CVV, y solo conserva marca + últimos 4 dígitos.
Tarjetas de prueba: `4242 4242 4242 4242` (Visa, aprobada), `5555 5555 5555 4444` (Mastercard, aprobada),
`4000 0000 0000 0002` (siempre rechazada). Usa cualquier vencimiento futuro y un CVV de 3 dígitos (4 para Amex).

### Datos de demostración para la previsión (US3)

```bash
cd backend
python seed.py            # servicios y citas de ejemplo
python seed_history.py    # 12 semanas de historial sintético para los gráficos
```

---

## Configuración (variables de entorno)

| Variable | Por defecto | Descripción |
|----------|-------------|-------------|
| `DATABASE_URL` | `sqlite:///./citafacil.db` | Conexión a la base de datos |
| `ADMIN_TOKEN` | `cambia-este-token-admin` | Token del panel admin |
| `CORS_ORIGINS` | `*` | Dominios permitidos del frontend |
| `BUSINESS_NAME` | `Barbería Don Lucho` | Nombre del negocio |
| `OPEN_HOUR` / `CLOSE_HOUR` | `10` / `20` | Horario de atención |
| `SLOT_INTERVAL_MINUTES` | `30` | Separación entre horarios |
| `CLOSED_WEEKDAYS` | `6` | Días cerrados (0=lun … 6=dom) |
| `TWILIO_ACCOUNT_SID` / `TWILIO_AUTH_TOKEN` / `TWILIO_WHATSAPP_FROM` | — | Credenciales de Twilio |
| `REMINDER_HOURS_BEFORE` | `24` | Horas antes para recordar |

---

## Desplegar en Render (gratis)

1. Sube este proyecto a un repositorio de GitHub.
2. En [Render](https://render.com): **New + → Blueprint** y conecta el repo. Render leerá `render.yaml` y creará la API + una base de datos PostgreSQL.
3. Cuando termine, tu API quedará en `https://citafacil-api.onrender.com` (con `/docs`).
4. Copia esa URL en el frontend: abre la página con `?api=https://tu-api.onrender.com` o usa el enlace **“Configurar API”** del pie de página.
5. Publica el `frontend/` en GitHub Pages.

El `ADMIN_TOKEN` se genera automáticamente; puedes verlo en **Environment** dentro del panel de Render.

---

## Activar WhatsApp real (Twilio)

1. Crea una cuenta en [twilio.com](https://www.twilio.com) y activa el **WhatsApp Sandbox** (Messaging → Try it out → Send a WhatsApp message).
2. Copia tu **Account SID**, **Auth Token** y el número del sandbox (`whatsapp:+14155238886`).
3. Define en Render (o en tu `.env`): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`.
4. Para recibir mensajes en tu celular, primero únete al sandbox enviando el código que indica Twilio (ej: `join <palabra>`).

Sin estas variables, la app funciona igual en **modo demo** (registra los mensajes en el log).

---

## Tests

```bash
cd backend
python -m pytest
```

Son **69 tests** (la línea base tenía 6). Cubren validación de teléfono, disponibilidad, doble-booking, autenticación, y las nuevas
funciones: calendario, cancelación con código, migración de esquema, pagos simulados y reserva rápida (incluida la verificación de que
nunca se guarda el número completo ni el CVV), previsión de demanda, exportación CSV con neutralización de fórmulas, escape de HTML (XSS)
y los scripts de siembra en consolas Windows.

> **Python 3.14 / Windows:** las versiones fijadas en `requirements.txt` están pensadas para Python 3.12 (el del `Dockerfile`).
> Con una versión más nueva de Python instala las dependencias sin fijar versión: `pip install fastapi "uvicorn[standard]" sqlalchemy pydantic pydantic-settings python-dotenv apscheduler httpx tzdata pytest twilio`.

---

## Posibles mejoras

*Rate limiting* en la cancelación y el perfil, pasarela de pago real con campos alojados por el proveedor, notificaciones por correo, soporte multi-sucursal o multi-profesional, pagos en línea, recordatorio configurable por servicio, e internacionalización.

---

## Autor

**Giancarlos Alfaro** — Desarrollador de Software
[Portafolio](https://gianca675.github.io) · [GitHub](https://github.com/gianca675) · [LinkedIn](https://www.linkedin.com/in/giancarlos-alfaro-echeverr%C3%ADa-9ab57b2a8)

Licencia MIT.
