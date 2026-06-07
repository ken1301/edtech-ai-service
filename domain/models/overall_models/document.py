from pydantic import BaseModel, Field
from typing import Optional

class PDFDocument(BaseModel):
    id: str 
    filename: str  
    content: bytes 
    size_bytes: Optional[int]

class ImageDocument(BaseModel):
    id: str 
    filename: str  
    content: bytes 
    parent_pdf_id: Optional[str] 

class MarkdownDocument(BaseModel):
    id: str 
    filename: str  
    content: str  
    parent_pdf_id: Optional[str]