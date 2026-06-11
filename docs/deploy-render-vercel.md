# Deploy Render + Vercel

Guia para publicar La Abeja con backend Django y base de datos en Render, y frontend Vite/React en Vercel.

## Arquitectura de deploy

- Render Web Service: Django REST API.
- Render Postgres Free: base de datos principal para demo.
- Render Key Value: Redis compatible para Celery/cache.
- Vercel: frontend estatico Vite.
- Imagenes: Cloudinary/S3/CDN o URLs absolutas. El frontend tambien tiene fallback local.

## 1. Preparar repositorio

Antes de crear servicios:

```bash
git status
npm --prefix frontend run build
DJANGO_SETTINGS_MODULE=config.settings.production PYTHONPATH=backend SECRET_KEY=local-check ALLOWED_HOSTS=localhost .venv/bin/python backend/manage.py check
```

Subi el repo a GitHub en una rama que quieras desplegar, normalmente `main`.

## 2. Backend y BD en Render

El repo ya incluye [`render.yaml`](/Users/braulio/La-Abeja/render.yaml). Usalo como Blueprint.

Pasos:

1. En Render: **New > Blueprint**.
2. Elegi el repositorio.
3. Render va a detectar `render.yaml`.
4. Completa las variables marcadas como `sync: false`.

Variables obligatorias para que frontend/backend hablen bien:

```bash
FRONTEND_URL=https://TU-FRONTEND.vercel.app
BACKEND_URL=https://TU-BACKEND.onrender.com
CORS_ALLOWED_ORIGINS=https://TU-FRONTEND.vercel.app
CSRF_TRUSTED_ORIGINS=https://TU-FRONTEND.vercel.app,https://TU-BACKEND.onrender.com
DEMO_ADMIN_PASSWORD=una-password-larga-y-segura
```

Variables recomendadas para AI/RAG:

```bash
OPENAI_API_KEY=sk-...
AI_LLM_PROVIDER=openai
AI_CHAT_MODEL=gpt-4.1
AI_EMBEDDING_MODEL=text-embedding-3-large
AI_ENABLE_PGVECTOR=True
AI_EMBEDDING_DIMENSIONS=1536
```

Variables para checkout real:

```bash
MERCADOPAGO_ACCESS_TOKEN=...
MERCADOPAGO_PUBLIC_KEY=...
MERCADOPAGO_WEBHOOK_SECRET=...
```

Render hace automaticamente en el `buildCommand`, porque el plan free no soporta `preDeployCommand`:

- `pip install -r requirements/production.txt`
- `python manage.py migrate`
- `python manage.py collectstatic --noinput`
- `python manage.py seed_demo_data`
- `python manage.py seed_ai_knowledge`
- start: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT`

Limitaciones del modo gratis:

- Render Free Web Service puede dormir por inactividad.
- Render Free Postgres expira a los 30 dias.
- Render Free Key Value es in-memory: puede perder datos al reiniciar.
- No hay `preDeployCommand`, shell/SSH ni one-off jobs en el web service free.

Si despues queres hacerlo estable de verdad, cambia el web service y la base a planes pagos y vuelve a mover `python manage.py migrate` a `preDeployCommand`.

Healthcheck:

```text
https://TU-BACKEND.onrender.com/health/
```

## 3. Frontend en Vercel

Crear proyecto en Vercel apuntando al mismo repo.

Configuracion:

- Root Directory: `frontend`
- Framework Preset: `Vite`
- Install Command: `npm install`
- Build Command: `npm run build`
- Output Directory: `dist`

Variables de entorno en Vercel:

```bash
VITE_API_URL=https://TU-BACKEND.onrender.com/api/v1
VITE_ASSET_BASE_URL=https://TU-BACKEND.onrender.com
```

Despues de cambiar variables en Vercel, redeploya. Vite las inyecta en build time.

## 4. Volver a Render y ajustar CORS

Cuando tengas la URL final de Vercel, revisa en Render:

```bash
FRONTEND_URL=https://TU-FRONTEND.vercel.app
CORS_ALLOWED_ORIGINS=https://TU-FRONTEND.vercel.app
CSRF_TRUSTED_ORIGINS=https://TU-FRONTEND.vercel.app,https://TU-BACKEND.onrender.com
```

Redeploy del backend si cambiaste estas variables.

## 5. Smoke test post-deploy

Backend:

```bash
curl https://TU-BACKEND.onrender.com/health/
curl https://TU-BACKEND.onrender.com/api/v1/catalog/wines/
```

Frontend:

- Abrir `https://TU-FRONTEND.vercel.app`
- Abrir `/vinos`
- Abrir `/backoffice/login`
- Login demo:
  - email: `admin@bodegalaabeja.com.ar`
  - password: la que pusiste en `DEMO_ADMIN_PASSWORD`

AI/RAG desde local apuntando a la base de Render, o desde un servicio pago con shell/one-off jobs:

```bash
python manage.py run_ai_evals
python manage.py reindex_ai_knowledge
```

Si `OPENAI_API_KEY` no esta configurada, el RAG queda con busqueda lexica. Funciona, pero recupera peor que con embeddings.

## 6. Opcional: Celery worker en Render

Para automatizaciones reales, crea un Background Worker adicional en Render con:

```bash
cd backend && celery -A config worker -l info
```

Debe usar las mismas variables de entorno que el web service, especialmente `DATABASE_URL`, `REDIS_HOST`, `REDIS_PORT`, `DJANGO_SETTINGS_MODULE=config.settings.production` y secrets.

Para tareas periodicas, agrega luego un Beat/Cron separado.

## 7. Checklist rapido

- Render backend responde `/health/`.
- Render Postgres tiene migraciones aplicadas.
- Vercel tiene `VITE_API_URL` apuntando a Render.
- Render tiene CORS/CSRF apuntando a Vercel.
- Las imagenes del catalogo cargan o caen al fallback local.
- Admin demo puede iniciar sesion.
- Mercado Pago usa `BACKEND_URL` publico para webhooks.
- RAG tiene `OPENAI_API_KEY` si queres embeddings.
