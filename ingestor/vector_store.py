import chromadb
import sqlite3
from chromadb.utils.embedding_functions import OpenCLIPEmbeddingFunction
from chromadb.utils.data_loaders import ImageLoader
import chromadb.utils.embedding_functions as embedding_functions

from config.settings import OPEN_AI_API_KEY

openai_ef = embedding_functions.OpenAIEmbeddingFunction(
    api_key=OPEN_AI_API_KEY,
    model_name="text-embedding-3-large"
)


class VectorStore:
    def __init__(self, db_path="source_ids.db"):
        # Initialize Chroma client
        self.directory = "./vector_store"
        self.client = chromadb.PersistentClient(path=self.directory)

        # Set up the text collection
        self.text_collection = self.client.get_or_create_collection(
            name="text_collection",
            embedding_function=openai_ef,
        )

        # Initialize embedding function and data loader for multimodal data
        self.clip_embedding_function = OpenCLIPEmbeddingFunction()
        self.image_loader = ImageLoader()

        # Create or get a multimodal collection for images, now to be used for both text and images
        self.multimodal_collection = self.client.get_or_create_collection(
            name="multimodal_collection",
            embedding_function=self.clip_embedding_function,
            data_loader=self.image_loader
        )

        # Initialize the SQLite database to store source-ids mapping
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS source_ids (
                            source TEXT PRIMARY KEY,
                            ids TEXT)''')
        conn.commit()
        conn.close()

    def update_db(self, source, ids):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('INSERT OR REPLACE INTO source_ids (source, ids) VALUES (?, ?)', (source, ','.join(ids)))
        conn.commit()
        conn.close()

    def get_ids_by_source(self, source):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT ids FROM source_ids WHERE source = ?', (source,))
        row = cursor.fetchone()
        conn.close()
        return row[0].split(',') if row else []

    def delete_source_from_db(self, source):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('DELETE FROM source_ids WHERE source = ?', (source,))
        conn.commit()
        conn.close()

    def multimodal_index(self, ids, contents=None, image_uris=None, metadatas=None):
        if contents is not None:
            self.text_collection.add(
                ids=ids,
                documents=contents,
                metadatas=metadatas
            )

        if image_uris is not None:
            images = self.image_loader(image_uris)
            embeddings = self.clip_embedding_function(images)
            self.multimodal_collection.add(
                ids=ids,
                embeddings=embeddings,
                uris=image_uris,
                metadatas=metadatas if metadatas else [{'source': uri} for uri in image_uris]
            )

        # Update the source-ids mapping in the SQLite database
        if metadatas:
            for metadata in metadatas:
                source = metadata.get('source')
                if source:
                    existing_ids = self.get_ids_by_source(source)
                    new_ids = list(set(existing_ids + ids))  # Ensure IDs are unique
                    self.update_db(source, new_ids)

    def search_text(self, queries, top_k=2):
        results = self.text_collection.query(
            query_texts=queries,
            n_results=top_k,
        )
        return results

    def search_text_to_image(self, queries, top_k=2):
        embeddings = self.clip_embedding_function(queries)
        results = self.multimodal_collection.query(
            query_embeddings=embeddings,
            n_results=top_k,
        )
        return results

    def image_to_image(self, queries, top_k=2):
        images = self.image_loader(queries)
        embeddings = self.clip_embedding_function(images)
        results = self.multimodal_collection.query(
            query_embeddings=embeddings,
            n_results=top_k
        )
        return results

    def delete_by_source(self, source):
        ids = self.get_ids_by_source(source)
        if ids:
            self.text_collection.delete(where={"id": {"$in": ids}})
            self.multimodal_collection.delete(where={"id": {"$in": ids}})
            self.delete_source_from_db(source)

    def update_source(self, old_source, new_source):
        ids = self.get_ids_by_source(old_source)
        if ids:
            # Update source in text collection
            self.text_collection.update(
                ids=ids,
                metadatas=[{"source": new_source} for _ in ids]
            )

            # Update source in multimodal collection
            self.multimodal_collection.update(
                ids=ids,
                metadatas=[{"source": new_source} for _ in ids]
            )

            # Update the source-ids mapping in the SQLite database
            self.delete_source_from_db(old_source)
            self.update_db(new_source, ids)

# img_loader = ImageLoader()
# image = img_loader(uris=['/Users/rohanverma/PycharmProjects/NoteAI/working/img1.jpeg'])
# embedding_func = OpenCLIPEmbeddingFunction()
# res = embedding_func(image)
# print(res)