import io
import uuid
import re
import pytesseract
import pymupdf
from PIL import Image
from fastapi import UploadFile

from schema import DocumentModel
from .chat import refine_text
from db.mongo import insert_into


async def do_processing(file: UploadFile, username: str):
    doc = pymupdf.Document(stream=file.file.read())
    document_id = str(uuid.uuid4())
    pages_data = []

    for page_num, page in enumerate(doc, start=1):
        pix = page.get_pixmap()
        img = pix.pil_image()
        text = pytesseract.image_to_string(img)

        # Refine the entire page at once

        refined_text = refine_text(text).content
        print(refined_text)
        # Optional: split the refined page into paragraphs
        refined_paragraphs = [
            p.strip() for p in re.split(r"\n\s*\n", refined_text) if p.strip()
        ]
        para_data = [
            {"paragraph": i + 1, "refined_text": p}
            for i, p in enumerate(refined_paragraphs)
        ]

        pages_data.append({
            "page": page_num,
            "original_text": text,
            "refined_text": refined_text,
            "paragraphs": para_data
        })

    mongo_data: DocumentModel = {
        "username": username,
        "document_id": document_id,
        "filename": file.filename,
        "pages": pages_data
    }

    print("inserting")
    await insert_into(mongo_data)

    return {"status": "ok", "document_id": document_id, "pages": len(pages_data), "document": mongo_data,
            "filename": file.filename}


async def process_image_file(file: UploadFile, username: str):
    image_data = await file.read()
    image = Image.open(io.BytesIO(image_data))
    original_text = pytesseract.image_to_string(image)

    # Refine the entire image text (treated as one page)
    refined_text = refine_text(original_text).content

    # Split refined text into paragraphs
    refined_paragraphs = [
        p.strip() for p in re.split(r"\n\s*\n", refined_text) if p.strip()
    ]
    para_data = [
        {"paragraph": i + 1, "refined_text": p}
        for i, p in enumerate(refined_paragraphs)
    ]

    document_id = str(uuid.uuid4())
    page_data = {
        "page": 1,
        "original_text": original_text,
        "refined_text": refined_text,
        "paragraphs": para_data
    }

    mongo_data = {
        "username": username,
        "document_id": document_id,
        "filename": file.filename,
        "pages": [page_data]
    }

    await insert_into(mongo_data)

    return {
        "status": "ok",
        "document_id": document_id,
        "filename": file.filename,
        "document": mongo_data
    }
