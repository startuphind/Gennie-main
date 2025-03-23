import json
import logging
from typing import Any, Iterator, List, Optional

from langchain_community.document_loaders.base import BaseBlobParser
from langchain_community.document_loaders.blob_loaders import Blob
from data_loaders.datatype import Document
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.ai.documentintelligence.models import DocumentAnalysisFeature, AnalyzeDocumentRequest
from azure.core.credentials import AzureKeyCredential

logger = logging.getLogger(__name__)


class AzureAIDocumentIntelligenceParser(BaseBlobParser):
    """Loads a PDF with Azure Document Intelligence (formerly Forms Recognizer)."""

    def __init__(
            self,
            api_endpoint: str,
            api_key: str,
            api_version: Optional[str] = None,
            api_model: str = "prebuilt-layout",
            mode: str = "markdown",
            analysis_features: Optional[List[str]] = None,
    ):
        kwargs = {}
        if api_version:
            kwargs["api_version"] = api_version

        features = None
        if analysis_features:
            supported_features = [DocumentAnalysisFeature.OCR_HIGH_RESOLUTION]
            features = [
                DocumentAnalysisFeature(feature) for feature in analysis_features
                if feature in supported_features
            ]

        self.client = DocumentIntelligenceClient(
            endpoint=api_endpoint,
            credential=AzureKeyCredential(api_key),
            headers={"x-ms-useragent": "langchain-parser/1.0.0"},
            features=features,
            **kwargs,
        )
        self.api_model = api_model
        self.mode = mode
        assert self.mode in ["single", "page", "markdown"]

    def lazy_parse(self, blob: Blob) -> Any:
        """Lazily parse the blob and return the result."""
        with blob.as_bytes_io() as file_obj:
            poller = self.client.begin_analyze_document(
                self.api_model,
                file_obj,
                content_type="application/octet-stream",
                output_content_format="markdown" if self.mode == "markdown" else "text",
            )
            result = poller.result()
            print(result)
            return Document(**result)

    def lazy_parse_file_obj(self, file_obj: Any) -> Any:
        poller = self.client.begin_analyze_document(
            self.api_model,
            file_obj,
            content_type="application/octet-stream",
            output_content_format="markdown" if self.mode == "markdown" else "text",
        )
        result = poller.result()
        print(result)
        return Document(**result)

    def parse_url(self, url: str) -> Any:
        """Parse the document from a URL and return the result."""
        poller = self.client.begin_analyze_document(
            self.api_model,
            AnalyzeDocumentRequest(url_source=url),
            content_type="application/octet-stream",
            output_content_format="markdown" if self.mode == "markdown" else "text",
        )
        result = poller.result()
        return Document(**result)


def generate_markdown_pages(doc: Document, source: str) -> Iterator[Document]:
    """Generate markdown pages from the document."""
    return doc.get_list_of_pages_with_metadata(source=source)