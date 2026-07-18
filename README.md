# 📅 CitaFácil — Sistema de reservas con recordatorios por WhatsApp

Aplicación **full-stack** para que pequeños negocios (barberías, peluquerías, clínicas, consultoras…) reciban reservas en línea y envíen **recordatorios automáticos por WhatsApp**.

Backend en **Python (FastAPI)** con base de datos **SQL**, API REST **documentada (Swagger)** e integración real con **Twilio**. Frontend liviano en **HTML/CSS/JS**: una página pública de reservas y un panel de administración.

> Proyecto de portafolio creado por **Giancarlos Alfaro** ([gianca675.github.io](https://gianca675.github.io)).

---

## ✨ Características

- **Reserva en 3 pasos**: el cliente elige servicio → día → hora libre, y deja su nombre y celular.
- **Sin choques de horario**: el motor de disponibilidad calcula los espacios libres según la duración de cada servicio y **evita el doble-booking**.
- **Recordatorios por WhatsApp**: envío automático (programado) X horas antes de la cita, además de confirmación al reservar.
- **Panel de administración**: estadísticas, gestión de reservas (confirmar / cancelar / realizar / eliminar) y de servicios (crear / activar / eliminar), protegido por token.
- **API REST documentada**: Swagger UI interactivo en `/docs`.
- **Validación de datos**: teléfonos chilenos normalizados a formato E.164, horarios de atención y días cerrados configurables.
- **Listo para desplegar**: Dockerfile, blueprint de Render y configuración por variables de entorno (SQLite en local → PostgreSQL en producción).

---

## 🧱 Stack técnico

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

## 🚀 Demo

- **Reservas (frontend):** _añade aquí tu URL de GitHub Pages_
- **Panel admin:** `.../admin.html`
- **API + documentación:** _añade aquí tu URL de Render_ `/docs`

---

## 📂 Estructura

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

## 🖥️ Ejecutar en local

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

## 🔌 Endpoints principales

| Método | Ruta | Descripción | Auth |
|--------|------|-------------|------|
| GET  | `/api/config` | Datos del negocio (nombre, horario) | — |
| GET  | `/api/services` | Servicios activos | — |
| GET  | `/api/availability?service_id=&date=` | Horarios libres de un día | — |
| POST | `/api/appointments` | Crear una reserva | — |
| GET  | `/api/admin/appointments` | Listar reservas (filtros) | 🔒 |
| PATCH| `/api/admin/appointments/{id}` | Cambiar estado | 🔒 |
| DELETE | `/api/admin/appointments/{id}` | Eliminar reserva | 🔒 |
| GET/POST/PUT/DELETE | `/api/admin/services` | Gestionar servicios | 🔒 |
| GET  | `/api/admin/stats` | Estadísticas | 🔒 |
| POST | `/api/admin/reminders/run` | Enviar recordatorios ahora | 🔒 |

🔒 = requiere la cabecera `X-Admin-Token`.

---

## ⚙️ Configuración (variables de entorno)

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

## ☁️ Desplegar en Render (gratis)

1. Sube este proyecto a un repositorio de GitHub.
2. En [Render](https://render.com): **New + → Blueprint** y conecta el repo. Render leerá `render.yaml` y creará la API + una base de datos PostgreSQL.
3. Cuando termine, tu API quedará en `https://citafacil-api.onrender.com` (con `/docs`).
4. Copia esa URL en el frontend: abre la página con `?api=https://tu-api.onrender.com` o usa el enlace **“Configurar API”** del pie de página.
5. Publica el `frontend/` en GitHub Pages.

El `ADMIN_TOKEN` se genera automáticamente; puedes verlo en **Environment** dentro del panel de Render.

---

## 💬 Activar WhatsApp real (Twilio)

1. Crea una cuenta en [twilio.com](https://www.twilio.com) y activa el **WhatsApp Sandbox** (Messaging → Try it out → Send a WhatsApp message).
2. Copia tu **Account SID**, **Auth Token** y el número del sandbox (`whatsapp:+14155238886`).
3. Define en Render (o en tu `.env`): `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_WHATSAPP_FROM`.
4. Para recibir mensajes en tu celular, primero únete al sandbox enviando el código que indica Twilio (ej: `join <palabra>`).

Sin estas variables, la app funciona igual en **modo demo** (registra los mensajes en el log).

---

## 🧪 Tests

```bash
cd backend
python -m pytest
```

Cubren la validación de teléfono, el cálculo de disponibilidad, la prevención de doble-booking y la autenticación del panel.

---

## 🛣️ Posibles mejoras

Notificaciones por correo, soporte multi-sucursal o multi-profesional, pagos en línea, recordatorio configurable por servicio, e internacionalización.

---

## 👤 Autor

**Giancarlos Alfaro** — Desarrollador de Software
[Portafolio](https://gianca675.github.io) · [GitHub](https://github.com/gianca675) · [LinkedIn](https://www.linkedin.com/in/giancarlos-alfaro-echeverr%C3%ADa-9ab57b2a8)

Licencia MIT.
