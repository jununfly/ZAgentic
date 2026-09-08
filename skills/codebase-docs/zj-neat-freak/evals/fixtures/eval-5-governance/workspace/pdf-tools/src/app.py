from fastapi import FastAPI, UploadFile
from pypdf import PdfReader, PdfWriter

api = FastAPI()

@api.post("/split")
async def split(file: UploadFile, pages_per_chunk: int = 10):
    reader = PdfReader(file.file)
    chunks = []
    for start in range(0, len(reader.pages), pages_per_chunk):
        writer = PdfWriter()
        for p in reader.pages[start:start + pages_per_chunk]:
            writer.add_page(p)
        chunks.append(writer)
    return {"chunks": len(chunks)}
