from ingestor.ingestor import DirectoryIngestor
from ingestor.link_generator import FileHandler, Normalizer, MarkdownParser
from ingestor.vector_store import VectorStore
from todo_manager.db import init_db

default_vector_store = VectorStore()
ingestor = DirectoryIngestor(default_vector_store)
# Initialize database
init_db()

# Initialize the classes
file_handler = FileHandler()
normalizer = Normalizer()
markdown_parser = MarkdownParser(file_handler, normalizer)

