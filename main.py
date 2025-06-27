from fastapi import FastAPI, File, UploadFile
from fastapi.responses import JSONResponse
import cv2
import numpy as np
import pytesseract
import re
from tempfile import NamedTemporaryFile


app = FastAPI()

def process_image(image_bytes: bytes):
    # Convert image bytes to OpenCV format
    file_bytes = np.asarray(bytearray(image_bytes), dtype=np.uint8)
    img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # Preprocessing
    img = cv2.resize(img, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    gray = cv2.bilateralFilter(gray, 11, 17, 17)
    thresh = cv2.adaptiveThreshold(gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C,
                                   cv2.THRESH_BINARY, 15, 8)

    # OCR
    custom_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(thresh, config=custom_config)
    return text

def extract_ingredients(ocr_text: str):
    text = ocr_text.replace('\n', ' ').upper()
    match = re.search(r'INGREDIENTS\s*:\s*(.*?)(?:\.?\s*(CONTAINS|MAY CONTAIN|$))', text)
    ingredient_text = match.group(1) if match else ""
    ingredient_text = re.sub(r'\([^)]*\)', '', ingredient_text)
    raw_ingredients = re.split(r',|\band\b|&', ingredient_text)
    ingredients = [ing.strip(" .").title() for ing in raw_ingredients if ing.strip()]
    unique_ingredients = list(dict.fromkeys(ingredients))
    return unique_ingredients

@app.post("/extract-ingredients")
async def extract_ingredients_api(file: UploadFile = File(...)):
    try:
        image_bytes = await file.read()
        ocr_text = process_image(image_bytes)
        ingredients = extract_ingredients(ocr_text)
        return JSONResponse(content={"ingredients": ingredients})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

