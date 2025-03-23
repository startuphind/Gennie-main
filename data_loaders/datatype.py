from typing import List, Optional
from pydantic import BaseModel, Field


class Span(BaseModel):
    offset: int = None
    length: int = None


class BoundingRegion(BaseModel):
    pageNumber: int = None
    polygon: List[float] = None


class Word(BaseModel):
    content: str = None
    polygon: List[float] = None
    confidence: float = None
    span: Span = None


class Line(BaseModel):
    content: str = None
    polygon: List[float] = None
    spans: List[Span] = None


class Cell(BaseModel):
    rowIndex: int = None
    columnIndex: int = None
    content: str = None
    boundingRegions: List[BoundingRegion] = None
    spans: List[Span] = None 
    elements: List[str] = None


class Table(BaseModel):
    rowCount: int = None
    columnCount: int = None
    cells: List[Cell] = None
    boundingRegions: List[BoundingRegion] = None
    spans: List[Span] = None


class Paragraph(BaseModel):
    spans: List[Span] = None
    boundingRegions: List[BoundingRegion] = None
    role: Optional[str] = None
    content: Optional[str] = None


class Section(BaseModel):
    spans: List[Span] = None
    elements: List[str] = None


class Figure(BaseModel):
    boundingRegions: List[BoundingRegion] = None
    spans: List[Span] = None
    elements: List[str] = None
    caption: Optional[Paragraph] = None


class Page(BaseModel):
    pageNumber: int = None
    angle: float = None
    width: float = None
    height: float = None
    unit: str = None
    words: List[Word] = None
    lines: List[Line] = None
    spans: List[Span] = None


class Document(BaseModel):
    apiVersion: str = ""
    modelId: str= ""
    stringIndexType: str = ""
    content: str = ""
    pages: List[Page] = []
    tables: List[Table] = [] 
    paragraphs: List[Paragraph] = []
    contentFormat: str = []
    sections: List[Section] = []
    figures: List[Figure] = []

    def get_list_of_pages_with_metadata(self, source:str):
        pages = []
        for page in self.pages:
            page_content = {
                "content": "",
                "metadata": {
                    "source": source,
                    "page_number": page.pageNumber
                }
            }

            for span in page.spans:
                page_content['content'] += self.content[span.offset:span.offset + span.length]
            pages.append(page_content)

        return pages
