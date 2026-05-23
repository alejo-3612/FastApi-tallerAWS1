# Taller AWS — Sistemas Operativos 2026
**Universidad EIA**

---

## Descripción general

Este es el manual de uso que se genero con el fin de la comprension completa del taller y sus funcionalidades

---

## Punto 1 — Gestión de archivos en Amazon S3

### a. Creación del bucket

Se creó un bucket en Amazon S3 siguiendo el patrón de nombre requerido:

```
user-########-ueia-so
```

### b. Operaciones usando Bash / AWS CLI

**Cargar un archivo al bucket:**
```bash
aws s3 cp archivo.txt s3://user-########-ueia-so/
```

**Verificar que el archivo fue cargado:**
```bash
aws s3 ls s3://user-########-ueia-so/
```

**Descargar el archivo en una carpeta diferente:**
```bash
aws s3 cp s3://user-########-ueia-so/archivo.txt ./descarga/archivo.txt
```

**Verificar que el archivo fue descargado:**
```bash
ls ./descarga/
```

**¿Qué cambia con múltiples archivos?**

Con un solo archivo se usa `cp` que copia un archivo a la vez. Con múltiples archivos se usa el flag `--recursive` que permite copiar carpetas completas de forma recursiva:

```bash
# Cargar múltiples archivos (toda una carpeta)
aws s3 cp ./carpeta/ s3://user-########-ueia-so/carpeta/ --recursive

# Descargar múltiples archivos
aws s3 cp s3://user-########-ueia-so/carpeta/ ./descarga/ --recursive
```

**Ejemplo práctico con múltiples archivos:**
```bash
# Crear archivos de prueba
echo "archivo1" > file1.txt
echo "archivo2" > file2.txt
echo "archivo3" > file3.txt

# Cargar todos
aws s3 cp file1.txt s3://user-########-ueia-so/
aws s3 cp file2.txt s3://user-########-ueia-so/
aws s3 cp file3.txt s3://user-########-ueia-so/

# Verificar
aws s3 ls s3://user-########-ueia-so/

# Descargar todos a carpeta diferente
mkdir ./descargados
aws s3 cp s3://user-########-ueia-so/ ./descargados/ --recursive
```

### c. Operaciones usando boto3 (Python)

**Cargar un archivo:**
```python
import boto3

s3 = boto3.client('s3')
bucket_name = 'user-########-ueia-so'

s3.upload_file('archivo.txt', bucket_name, 'archivo.txt')
print("Archivo cargado correctamente")
```

**Verificar que fue cargado:**
```python
response = s3.list_objects_v2(Bucket=bucket_name)
for obj in response.get('Contents', []):
    print(obj['Key'])
```

**Descargar en carpeta diferente:**
```python
s3.download_file(bucket_name, 'archivo.txt', './descarga/archivo.txt')
print("Archivo descargado correctamente")
```

**¿Qué cambia con múltiples archivos?**

Con un solo archivo se llama `upload_file` o `download_file` una vez. Con múltiples archivos se itera sobre una lista o se usa un bucle. No existe un método nativo de boto3 para carpetas completas como `--recursive` en CLI, por lo que se debe iterar manualmente.

**Prueba con tres archivos de texto:**
```python
import boto3
import os

s3 = boto3.client('s3')
bucket_name = 'user-########-ueia-so'

# Crear y cargar 3 archivos
archivos = ['texto1.txt', 'texto2.txt', 'texto3.txt']
for nombre in archivos:
    with open(nombre, 'w') as f:
        f.write(f"Contenido de {nombre}")
    s3.upload_file(nombre, bucket_name, nombre)
    print(f"{nombre} cargado correctamente")

# Descargar los 3 archivos en carpeta diferente
os.makedirs('./descargados', exist_ok=True)
for nombre in archivos:
    s3.download_file(bucket_name, nombre, f'./descargados/{nombre}')
    print(f"{nombre} descargado correctamente")
```

---

## Punto 2 — Despliegue de aplicación FastAPI en Amazon EC2

### Pasos realizados

**1. Repositorio en GitHub**

Se creó el repositorio en GitHub y se subió el proyecto:
```bash
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/alejo-3612/FastApi-tallerAWS1.git
git push -u origin main
```

**2. Creación de instancia EC2**

Se creó una instancia EC2 con las siguientes características:
- AMI: Ubuntu Server 22.04 LTS
- Tipo: t2.micro (Free Tier)
- Security Group: puerto 22 (SSH) y puerto 8000 (FastAPI) abiertos

**3. Clonar el repositorio en la instancia**
```bash
git clone https://github.com/alejo-3612/FastApi-tallerAWS1.git
cd FastApi-tallerAWS1
```

**4. Instalar dependencias**
```bash
sudo apt update
sudo apt install python3-pip python3-venv -y
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**5. Ejecutar la aplicación**
```bash
uvicorn main:app --host 0.0.0.0 --port 8000
```

**6. Configurar daemon con systemd**

Se creó el archivo `/etc/systemd/system/fastapi.service`:
```ini
[Unit]
Description=FastAPI App
After=network.target

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/FastApi-tallerAWS1
ExecStart=/home/ubuntu/FastApi-tallerAWS1/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Activar el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable fastapi
sudo systemctl start fastapi
sudo systemctl status fastapi
```

**7. Acceso por IP pública**

La aplicación quedó accesible en:
```
http://<IP-PUBLICA-EC2>:8000
```

---

## Punto 3 — Desarrollo y despliegue de aplicación FastAPI

### a & b. Endpoints implementados

#### POST `/upload-image`

Recibe el nombre de un usuario y una imagen (PNG, JPG, JPEG), la almacena en S3 organizada por usuario y registra los metadatos en RDS.

**Validaciones:**
- Solo acepta archivos `.png`, `.jpg`, `.jpeg`
- Retorna HTTP 400 si el formato es inválido

**Ejemplo de uso:**
```bash
curl -X POST https://<lambda-url>/upload-image \
  -F "username=alejo" \
  -F "image=@foto.jpg"
```

**Respuesta exitosa:**
```json
{
  "message": "Imagen guardada correctamente",
  "usuario": "alejo",
  "archivo": "foto.jpg",
  "ruta_s3": "https://alejo-362009-ueia-so.s3.amazonaws.com/alejo/foto.jpg"
}
```

#### GET `/get-image`

Recibe el nombre de usuario y el nombre de la imagen, consulta la base de datos y retorna la URL de acceso y la fecha de almacenamiento.

**Ejemplo de uso:**
```bash
curl "https://<lambda-url>/get-image?username=alejo&image_name=foto.jpg"
```

**Respuesta exitosa:**
```json
{
  "usuario": "alejo",
  "imagen": "foto.jpg",
  "url": "https://alejo-362009-ueia-so.s3.amazonaws.com/alejo/foto.jpg",
  "created_at": "2026-05-23 02:14:45"
}
```

**Si el usuario o imagen no existen:**
```json
{
  "detail": "Imagen o usuario no encontrado"
}
```

### Base de datos RDS

Se creó una instancia RDS MySQL con la siguiente tabla:

```sql
CREATE DATABASE imagenes_db;
USE imagenes_db;

CREATE TABLE images (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL,
    image_url TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### c. Contenerización

**Dockerfile:**
```dockerfile
FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}
RUN pip install -r requirements.txt --target ${LAMBDA_TASK_ROOT}

COPY . ${LAMBDA_TASK_ROOT}

CMD ["main.handler"]
```

**Construir y probar localmente:**
```bash
docker build --platform linux/amd64 -t fastapi-taller .

docker run -p 9000:8080 \
  -e DB_HOST=<rds-endpoint> \
  -e DB_USER=admin \
  -e DB_PASSWORD=<password> \
  -e DB_NAME=imagenes_db \
  fastapi-taller
```

### d. Publicación en Amazon ECR

```bash
# Crear repositorio
aws ecr create-repository --repository-name fastapi-taller --region us-east-2

# Autenticarse
aws ecr get-login-password --region us-east-2 | docker login --username AWS --password-stdin 911526871150.dkr.ecr.us-east-2.amazonaws.com

# Tag y push
docker tag fastapi-taller:latest 911526871150.dkr.ecr.us-east-2.amazonaws.com/fastapi-taller:latest
docker push 911526871150.dkr.ecr.us-east-2.amazonaws.com/fastapi-taller:latest
```

### e. Despliegue en AWS Lambda

**Configuración de la función Lambda:**
- Nombre: `fastapi-taller`
- Tipo: Container image
- Imagen: `911526871150.dkr.ecr.us-east-2.amazonaws.com/fastapi-taller:latest`
- Architecture: x86_64
- Timeout: 30 segundos
- Permisos: `AmazonS3FullAccess`

**Variables de entorno configuradas:**

| Variable | Descripción |
|----------|-------------|
| `DB_HOST` | Endpoint del RDS |
| `DB_USER` | Usuario de MySQL |
| `DB_PASSWORD` | Contraseña de MySQL |
| `DB_NAME` | Nombre de la base de datos |

**URL pública de la función:**
```
https://aqrel4wyrmqcptfavljj3ezchu0svtgs.lambda-url.us-east-2.on.aws/
```

**Endpoints disponibles:**

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/` | Health check — retorna `{"message": "Universidad EIA"}` |
| POST | `/upload-image` | Sube imagen a S3 y registra en RDS |
| GET | `/get-image` | Consulta imagen por usuario y nombre |

---

## Variables de entorno requeridas

Para ejecutar la aplicación se necesitan las siguientes variables de entorno:

```
DB_HOST=<endpoint-rds>
DB_USER=<usuario-mysql>
DB_PASSWORD=<contraseña-mysql>
DB_NAME=imagenes_db
```

Las credenciales de AWS se configuran mediante el rol IAM asignado a la función Lambda.

---

## Realizado por

Sebastian Higuita & Alejandro Sanchez