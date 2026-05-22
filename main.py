from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Depends
from pydantic import BaseModel
import mysql.connector
import os
import boto3
from mangum import Mangum

app = FastAPI()

# ---------- Conexión lazy a MySQL ----------
_db = None

def get_db():
    global _db
    if _db is None or not _db.is_connected():
        _db = mysql.connector.connect(
            host=os.getenv("DB_HOST"),
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME"),
            connection_timeout=5,
        )
    return _db


def db_cursor():
    conn = get_db()
    cursor = conn.cursor()
    try:
        yield cursor, conn
    finally:
        cursor.close()


# ---------- Modelos ----------
class Item(BaseModel):
    name: str = "Mateo"
    description: str = "Testing"
    price: float = 2000.35


# ---------- Endpoints simples ----------
@app.get("/")
def read_root():
    return {"message": "Universidad EIA"}


@app.get("/items/{item_id}")
def read_item(item_id: int, query: str = None):
    return {"item_id": item_id, "query": query}


@app.post("/items/")
def create_item(item: Item):
    return {
        "name": item.name,
        "description": item.description,
        "price": item.price
    }


# ---------- Subir imagen a S3 + guardar metadata en RDS ----------
@app.post("/upload-image")
def upload_image(
    username: str = Form(...),
    image: UploadFile = File(...),
    db_dep = Depends(db_cursor),
):
    cursor, conn = db_dep

    # Validar formato de imagen
    if not image.filename.lower().endswith((".png", ".jpg", ".jpeg")):
        raise HTTPException(
            status_code=400,
            detail="Solo se permiten imágenes PNG, JPG o JPEG"
        )

    s3 = boto3.client("s3")
    bucket_name = "alejo-362009-ueia-so"
    s3_key = f"{username}/{image.filename}"

    try:
        # Subir archivo a S3
        s3.upload_fileobj(image.file, bucket_name, s3_key)

        # URL pública del archivo
        image_url = f"https://{bucket_name}.s3.amazonaws.com/{s3_key}"

        # Guardar metadata en RDS
        sql = "INSERT INTO images (username, image_url) VALUES (%s, %s)"
        cursor.execute(sql, (username, image_url))
        conn.commit()

        return {
            "message": "Imagen guardada correctamente",
            "usuario": username,
            "archivo": image.filename,
            "ruta_s3": image_url
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error al subir imagen: {str(e)}"
        )


# ---------- Consultar imagen ----------
@app.get("/get-image")
def get_image(
    username: str,
    image_name: str,
    db_dep = Depends(db_cursor),
):
    cursor, _ = db_dep

    cursor.execute(
        "SELECT image_url, created_at FROM images WHERE username=%s AND image_url LIKE %s",
        (username, f"%{image_name}%")
    )
    result = cursor.fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Imagen o usuario no encontrado")

    image_url, created_at = result

    # Si la URL viene en formato s3:// la convertimos a HTTPS
    if image_url.startswith("s3://"):
        s3_path = image_url.replace("s3://", "")
        bucket, key = s3_path.split("/", 1)
        public_url = f"https://{bucket}.s3.amazonaws.com/{key}"
    else:
        public_url = image_url

    return {
        "usuario": username,
        "imagen": image_name,
        "url": public_url,
        "created_at": created_at
    }


# ---------- Handler para AWS Lambda ----------
handler = Mangum(app)