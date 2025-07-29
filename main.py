from fastapi import FastAPI, UploadFile, File, BackgroundTasks, Request
from fastapi.responses import FileResponse, StreamingResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pdf2image import convert_from_path
from PIL import Image
import os
import shutil
import uuid
import base64
from io import BytesIO

app = FastAPI()

# ✅ CORS (frontend connection ke liye)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Change to frontend domain in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ✅ Poppler and output folder setup
POPPLER_PATH = r"C:\Users\chaud\Downloads\Release-24.08.0-0 (1)\poppler-24.08.0\Library\bin"
OUTPUT_FOLDER = "output"
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ✅ File delete utility
def delete_file(path: str):
    if os.path.exists(path):
        os.remove(path)

# ✅ Route: Convert PDF to PNG
@app.post("/convert-pdf/")
async def convert_pdf(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = None
):
    if file.content_type != "application/pdf":
        return {"error": "Invalid file type. Please upload a PDF file."}

    temp_pdf_name = f"{uuid.uuid4()}.pdf"
    pdf_path = os.path.join(OUTPUT_FOLDER, temp_pdf_name)
    with open(pdf_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    images = convert_from_path(pdf_path, dpi=400, poppler_path=POPPLER_PATH)
    image_filename = f"{uuid.uuid4()}.png"
    image_path = os.path.join(OUTPUT_FOLDER, image_filename)
    images[0].save(image_path, "PNG")

    delete_file(pdf_path)
    background_tasks.add_task(delete_file, image_path)

    return FileResponse(image_path, media_type="image/png", filename=image_filename)

# ✅ Route: Save edited image
@app.post("/save-edited-image/")
async def save_edited_image(request: Request):
    data = await request.json()
    image_data = data["image_data"]

    header, encoded = image_data.split(",", 1)
    decoded_bytes = base64.b64decode(encoded)
    image = Image.open(BytesIO(decoded_bytes)).convert("RGB")

    expected_width = 3306
    expected_height = 4678
    if image.size != (expected_width, expected_height):
        image = image.resize((expected_width, expected_height), resample=Image.NEAREST)

    output_buffer = BytesIO()
    image.save(output_buffer, format="PNG", dpi=(400, 400))
    output_buffer.seek(0)

    return StreamingResponse(output_buffer, media_type="image/png")

from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ✅ Mount the static folder (update path if needed)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Serve index.html at root
@app.get("/", response_class=FileResponse)
async def serve_index():
    return FileResponse("static/index.html")

# ✅ Optional: Serve edit_screen.html at separate route
@app.get("/editor", response_class=FileResponse)
async def serve_editor():
    return FileResponse("static/edit_screen.html")

