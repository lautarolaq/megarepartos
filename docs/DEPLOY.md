# Deploy a Cloud Run

## Resumen

El Dockerfile compila el frontend (Vite) y lo serve desde el backend (FastAPI)
en un único container. Esto significa que para deployar Megarepartos a producción
necesitás:

1. Una base de datos Postgres accesible (Cloud SQL o Neon).
2. Un servicio Cloud Run.
3. Variables de entorno con los secretos.
4. Un dominio (opcional, pero recomendado para que el OAuth funcione).

## Pre-requisitos

- `gcloud` instalado y autenticado (`gcloud auth login`).
- Proyecto GCP activo. En esta cuenta: `fechitas-prod`.
- Docker corriendo localmente si querés hacer el build local. Sino, Cloud Build
  lo hace en la nube.

```bash
gcloud config set project fechitas-prod
```

## 1) Base de datos

### Opción A: Neon (recomendada para MVP, gratis hasta 500MB)

1. Andá a https://neon.tech → crea proyecto.
2. Copiate la connection string. Te queda algo como:
   ```
   postgresql://user:pass@ep-xxx.region.aws.neon.tech/megarepartos?sslmode=require
   ```
3. Convertila al formato async para SQLAlchemy:
   ```
   postgresql+asyncpg://user:pass@ep-xxx.region.aws.neon.tech/megarepartos
   ```
   (sin `?sslmode=require` — asyncpg lo maneja distinto).

### Opción B: Cloud SQL (más caro pero todo en GCP)

```bash
gcloud sql instances create megarepartos-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1
gcloud sql databases create megarepartos --instance=megarepartos-db
gcloud sql users create megarepartos --instance=megarepartos-db --password=...
```

## 2) Migrar el schema

Una sola vez, antes del primer deploy:

```bash
# Setear DATABASE_URL local apuntando a la DB de prod
export DATABASE_URL="postgresql+asyncpg://..."
cd backend
source .venv/bin/activate
alembic upgrade head
```

Esto crea las tablas, RLS, role `megarepartos_app`, etc.

## 3) Secretos en Secret Manager

```bash
# Habilitar Secret Manager
gcloud services enable secretmanager.googleapis.com

# Crear secretos
echo -n "postgresql+asyncpg://..." | gcloud secrets create database-url --data-file=-
echo -n "$(openssl rand -hex 32)" | gcloud secrets create jwt-secret --data-file=-
echo -n "458974100451-...apps.googleusercontent.com" | gcloud secrets create google-oauth-client-id --data-file=-
echo -n "GOCSPX-..." | gcloud secrets create google-oauth-client-secret --data-file=-

# Dar permiso al service account de Cloud Run para leerlos
PROJECT_NUMBER=$(gcloud projects describe fechitas-prod --format="value(projectNumber)")
SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
for SECRET in database-url jwt-secret google-oauth-client-id google-oauth-client-secret; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:$SA" \
    --role="roles/secretmanager.secretAccessor"
done
```

## 4) Build de la imagen

```bash
# Cloud Build (recomendado, no requiere Docker local)
gcloud builds submit --tag us-central1-docker.pkg.dev/fechitas-prod/megarepartos/app:latest .

# O Docker local
docker build -t us-central1-docker.pkg.dev/fechitas-prod/megarepartos/app:latest .
docker push us-central1-docker.pkg.dev/fechitas-prod/megarepartos/app:latest
```

> Antes, crear el repo de Artifact Registry:
> ```bash
> gcloud artifacts repositories create megarepartos --repository-format=docker --location=us-central1
> ```

## 5) Deploy a Cloud Run

```bash
gcloud run deploy megarepartos \
  --image us-central1-docker.pkg.dev/fechitas-prod/megarepartos/app:latest \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --min-instances 0 \
  --max-instances 5 \
  --cpu 1 \
  --memory 512Mi \
  --set-env-vars="APP_ENV=production,SERVE_FRONTEND=1,FRONTEND_DIST=/app/frontend/dist,GOOGLE_OAUTH_REDIRECT_URL=https://TU-DOMINIO/api/auth/google/callback,FRONTEND_BASE_URL=https://TU-DOMINIO" \
  --set-secrets="DATABASE_URL=database-url:latest,JWT_SECRET=jwt-secret:latest,GOOGLE_OAUTH_CLIENT_ID=google-oauth-client-id:latest,GOOGLE_OAUTH_CLIENT_SECRET=google-oauth-client-secret:latest"
```

El comando te imprime al final una URL tipo `https://megarepartos-xxx-uc.a.run.app`. Esa es la URL pública.

## 6) Configurar Google OAuth

En https://console.cloud.google.com/apis/credentials → editá el OAuth 2.0 Client:

- **Authorized JavaScript origins**: agregá `https://megarepartos-xxx-uc.a.run.app` (o tu dominio).
- **Authorized redirect URIs**: agregá `https://megarepartos-xxx-uc.a.run.app/api/auth/google/callback`.

Después actualizá las env vars de Cloud Run para que `FRONTEND_BASE_URL` y
`GOOGLE_OAUTH_REDIRECT_URL` apunten a esa URL:

```bash
gcloud run services update megarepartos --region us-central1 \
  --set-env-vars="FRONTEND_BASE_URL=https://megarepartos-xxx-uc.a.run.app,GOOGLE_OAUTH_REDIRECT_URL=https://megarepartos-xxx-uc.a.run.app/api/auth/google/callback"
```

## 7) Dominio propio (opcional)

```bash
gcloud beta run domain-mappings create --service megarepartos --domain app.megarepartos.com.ar --region us-central1
```

Luego en tu DNS, agregar los registros que te indica el comando (CNAME o A records).

Una vez activo, repetir el paso 6 con tu dominio real.

## Actualizaciones (después del primer deploy)

Para deployar una versión nueva:

```bash
# 1. Build
gcloud builds submit --tag us-central1-docker.pkg.dev/fechitas-prod/megarepartos/app:latest .

# 2. Deploy (reusa todas las env vars/secrets)
gcloud run services update megarepartos \
  --region us-central1 \
  --image us-central1-docker.pkg.dev/fechitas-prod/megarepartos/app:latest

# 3. Si hay nuevas migraciones de Alembic:
export DATABASE_URL="..."
cd backend && alembic upgrade head
```

## Costos esperados (free tier-ish)

Cloud Run free tier mensual:
- 2 millones de requests
- 360,000 GB-seconds de memoria
- 180,000 vCPU-seconds

Una sodería con ~100 clientes y 4 campañas/mes está MUY lejos del cap.
Con `min-instances=0` el container se duerme cuando no hay tráfico — los
primeros requests después del idle tardan ~2s en arrancar (cold start),
pero después es rápido.

Si querés evitar el cold start: `--min-instances 1`. Eso te factura
aprox. USD 5/mes por mantener 1 instancia tibia.

Neon: 500MB gratis es ~150,000 clientes con sus pedidos. Lejos.

Total estimado: **USD 0/mes** hasta que escales fuera del free tier.
