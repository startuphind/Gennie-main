from langchain_core.document_loaders import Blob

from data_loaders.AzureAIDocumentIntelligenceParser import AzureAIDocumentIntelligenceParser, generate_markdown_pages


def ocr_pdf(file_obj, source: str):
    ocr = AzureAIDocumentIntelligenceParser(
        api_endpoint="AZURE_DOCUMENT_INTELLIGENCE_API_ENDPOINT",
        api_key="AZURE_DOCUMENT_INTELLIGENCE_API_KEY",
        api_model="prebuilt-layout",
        mode="markdown",
    )
    doc = ocr.lazy_parse_file_obj(file_obj)
    pages = generate_markdown_pages(doc, source)
    return pages


def ocr_image(file_obj, source: str):
    ocr = AzureAIDocumentIntelligenceParser(
        api_endpoint="AZURE_DOCUMENT_INTELLIGENCE_API_ENDPOINT",
        api_key="AZURE_DOCUMENT_INTELLIGENCE_API_KEY",
        api_model="prebuilt-layout",
        mode="markdown",
    )
    doc = ocr.lazy_parse_file_obj(file_obj)
    return doc.content

# file_obj = open("Karan Chavan Resume.pdf", "rb")
# blob = Blob(path="Karan Chavan Resume.pdf")
# doc = ocr.lazy_parse(blob)
# pages = generate_markdown_pages(doc, "Karan Chavan Resume.pdf")
