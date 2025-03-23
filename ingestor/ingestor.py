import hashlib
import mimetypes
import os
import uuid

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from watchdog.observers import Observer

from data_loaders.doc_loaders import ocr_pdf, ocr_image
from todo_manager.db import retry_on_lock, init_db

from vector_store import VectorStore




class Ingestor:
    def __init__(self, vector_store: VectorStore):
        init_db()
        self.vector_store = vector_store

    def get_file_hash(self, file_path):
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()

    @retry_on_lock
    def file_already_processed(self, file_path):
        conn = get_db_connection()
        try:
            file_hash = self.get_file_hash(file_path)
            result = conn.execute(
                text('SELECT * FROM files WHERE path = :path AND hash = :hash'),
                {'path': file_path, 'hash': file_hash}
            )
            record = result.fetchone()
        finally:
            conn.close()
        return record is not None

    @retry_on_lock
    def save_file_record(self, file_path):
        conn = get_db_connection()
        try:
            file_hash = self.get_file_hash(file_path)
            file_url = os.path.abspath(file_path)
            print(f"Saving file record: Path={file_path}, Hash={file_hash}, URL={file_url}")
            conn.execute(
                text('INSERT INTO files (path, hash, url) VALUES (:path, :hash, :url)'),
                {'path': file_path, 'hash': file_hash, 'url': file_url}
            )
            conn.commit()
        except OperationalError as e:
            print(f"An error occurred while saving the file record: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    @retry_on_lock
    def update_file_record(self, old_path, new_path):
        conn = get_db_connection()
        try:
            conn.execute(
                text('UPDATE files SET path = :new_path, url = :url WHERE path = :old_path'),
                {'new_path': new_path, 'url': os.path.abspath(new_path), 'old_path': old_path}
            )
            conn.commit()
        except OperationalError as e:
            print(f"An error occurred while updating the file record: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    @retry_on_lock
    def delete_file_record(self, file_path):
        conn = get_db_connection()
        try:
            conn.execute(
                text('DELETE FROM files WHERE path = :path'),
                {'path': file_path}
            )
            conn.commit()
        except OperationalError as e:
            print(f"An error occurred while deleting the file record: {e}")
            conn.rollback()
            raise
        finally:
            conn.close()

    async def ingest_pdf(self, file_path):
        if self.file_already_processed(file_path):
            return
        with open(file_path, 'rb') as f:
            page_contents = ocr_pdf(file_obj=f, source=f"file:///{file_path}")
        contents = []
        metadatas = []
        for page_content in page_contents:
            contents.append(page_content['content'])
            metadatas.append(page_content['metadata'])
            metadatas[-1]['type'] = 'document'
            metadatas[-1]['source'] = os.path.abspath(file_path)
        self.vector_store.multimodal_index(
            ids=[str(uuid.uuid4()) for _ in contents],
            contents=contents,
            image_uris=None,
            metadatas=metadatas
        )
        self.save_file_record(file_path)
        print(f'PDF file ingested: {file_path}')

    async def ingest_content(self, contents: list[str]):
        self.vector_store.multimodal_index(
            ids=[str(uuid.uuid4()) for _ in contents],
            contents=contents,
            image_uris=None,
            metadatas=[{'type': "memory"} for _ in contents]
        )

    async def ingest_image(self, file_path):
        if self.file_already_processed(file_path):
            return
        self.save_file_record(file_path)

        metadata = {'type': 'image', 'source': os.path.abspath(file_path)}
        image_id = str(uuid.uuid4())
        self.vector_store.multimodal_index(ids=[image_id], contents=None, image_uris=[file_path], metadatas=[metadata])
        print(f'Image file ingested: {file_path}')

        # Ingest Image Content
        try:
            with open(file_path, 'rb') as f:
                content = ocr_image(file_obj=f, source=f"file:///{file_path}")
                self.vector_store.multimodal_index(
                    ids=[image_id],
                    contents=[content],
                    image_uris=None,
                    metadatas=[{'type': "Image", 'source': f"file:///{file_path}"}]
                )
        except:
            print("Image doesn't have any content")

        return f'Image file ingested: {file_path}'

    async def ingest_document(self, file_path):
        mime_type, _ = mimetypes.guess_type(file_path)
        if mime_type:
            if mime_type == 'application/pdf':
                await self.ingest_pdf(file_path)
            elif mime_type.startswith('image'):
                await self.ingest_image(file_path)


import os
import mimetypes
import asyncio
from todo_manager.db import get_db_connection
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class DirectoryIngestor(Ingestor):
    def __init__(self, vector_store: VectorStore):
        super().__init__(vector_store)
        self.observers = {}

    @retry_on_lock
    def resolve_directory_conflicts(self, directory_path):
        conn = get_db_connection()
        try:
            result = conn.execute(text('SELECT * FROM directories'))
            all_dirs = result.fetchall()

            parent_dir = None
            child_dirs = []

            abs_directory_path = os.path.abspath(directory_path)

            for dir in all_dirs:
                abs_dir_path = os.path.abspath(dir[1])  # Change from dir['path'] to dir[1]
                if os.path.commonpath([abs_directory_path, abs_dir_path]) == abs_dir_path:
                    parent_dir = abs_dir_path
                elif os.path.commonpath([abs_dir_path, abs_directory_path]) == abs_directory_path:
                    child_dirs.append(abs_dir_path)

            if parent_dir:
                conn.execute(text('DELETE FROM directories WHERE path = :path'), {'path': parent_dir})
            for child_dir in child_dirs:
                conn.execute(text('DELETE FROM directories WHERE path = :path'), {'path': child_dir})
            conn.commit()
        finally:
            conn.close()

        return parent_dir

    async def ingest_directory(self, directory_path):
        if self.resolve_directory_conflicts(directory_path):
            print(f"Directory already processed: {directory_path}")
            return

        # Track existing files in the directory
        existing_files = set()
        for root, dirs, files in os.walk(directory_path):
            for file in files:
                file_path = os.path.join(root, file)
                existing_files.add(os.path.abspath(file_path))
                mime_type, _ = mimetypes.guess_type(file_path)
                if mime_type:
                    if mime_type == 'application/pdf':
                        await self.ingest_pdf(file_path)
                    elif mime_type.startswith('image'):
                        await self.ingest_image(file_path)

        # Fetch records from the database to find missing files
        conn = get_db_connection()
        try:
            result = conn.execute(text('SELECT path FROM files'))
            db_files = result.fetchall()
        finally:
            conn.close()

        db_files_set = set(os.path.abspath(file[0]) for file in db_files)  # Change from file['path'] to file[0]

        # Detect deleted or moved files
        missing_files = db_files_set - existing_files
        for missing_file in missing_files:
            self.vector_store.delete_by_source(missing_file)
            self.delete_file_record(missing_file)

        self.start_file_watcher(directory_path)

    def start_file_watcher(self, directory_path):
        abs_directory_path = os.path.abspath(directory_path)
        if abs_directory_path in self.observers:
            print(f"Directory watcher already running for: {abs_directory_path}")
            return

        event_handler = IngestionEventHandler(self)
        observer = Observer()
        observer.schedule(event_handler, abs_directory_path, recursive=True)
        observer.start()
        self.observers[abs_directory_path] = observer
        print(f'Started watching directory: {abs_directory_path}')

    def stop_all_watchers(self):
        for observer in self.observers.values():
            observer.stop()
            observer.join()
        self.observers.clear()


import os
import asyncio
from watchdog.events import FileSystemEventHandler

class IngestionEventHandler(FileSystemEventHandler):
    def __init__(self, ingestor):
        """
        Initialize the event handler with a reference to the ingestor.

        :param ingestor: Instance of Ingestor or DirectoryIngestor to handle the events.
        """
        self.ingestor = ingestor

    async def handle_event(self, event):
        """
        Handle file system events and perform the appropriate ingestion or deletion action.

        :param event: File system event object.
        """
        if not event.is_directory:
            if event.event_type == 'deleted':
                # Handle file deletion event
                self.ingestor.vector_store.delete_by_source(os.path.abspath(event.src_path))
                self.ingestor.delete_file_record(os.path.abspath(event.src_path))
            elif event.event_type == 'moved':
                # Handle file move event
                self.ingestor.vector_store.update_source(
                    os.path.abspath(event.src_path),
                    os.path.abspath(event.dest_path)
                )
                self.ingestor.update_file_record(os.path.abspath(event.src_path), os.path.abspath(event.dest_path))
            else:
                # Handle file creation or modification event
                await self.ingestor.ingest_document(event.src_path)

    def on_created(self, event):
        """
        Triggered when a file or directory is created.

        :param event: File system event object.
        """
        asyncio.run(self.handle_event(event))

    def on_deleted(self, event):
        """
        Triggered when a file or directory is deleted.

        :param event: File system event object.
        """
        asyncio.run(self.handle_event(event))

    def on_moved(self, event):
        """
        Triggered when a file or directory is moved or renamed.

        :param event: File system event object.
        """
        asyncio.run(self.handle_event(event))
