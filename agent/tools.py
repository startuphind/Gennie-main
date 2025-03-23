import asyncio
import json
from pydantic import BaseModel, Field
from typing import List, Optional, Any

from code_interpreter.code_interpreter import CodeInterpreter
from code_interpreter.code_interpreter_utils import execute_python_code
from ingestor.ingestor import Ingestor
from ingestor.vector_store import VectorStore
from init_setup import default_vector_store
from todo_manager.todo_manager import TodoManager
from tool_manager.ToolManager import ToolManager


class SemanticDocumentSearchInput(BaseModel):
    queries: List[str] = Field(default=[], description="List of meaningful queries")
    top_k: int = Field(default=2, description="No. of items to retrieve for each queries")
    vector_store: Optional[Any] = Field(default=None, description="Optional VectorStore instance")

    class Config:
        arbitrary_types_allowed = True


class SemanticTextToImageSearchInput(BaseModel):
    queries: List[str] = Field(default=[], description="List of meaningful queries")
    top_k: int = Field(default=2, description="No. of items to retrieve for each queries")
    vector_store: Optional[Any] = Field(default=None, description="Optional VectorStore instance")

    class Config:
        arbitrary_types_allowed = True


class SemanticImageToImageSearchInput(BaseModel):
    queries: List[str] = Field(default=[], description="List of image URIs/paths")
    top_k: int = Field(default=2, description="No. of items to retrieve for each queries")
    vector_store: Optional[Any] = Field(default=None, description="Optional VectorStore instance")

    class Config:
        arbitrary_types_allowed = True


class IndexContentsInVectorStoreInput(BaseModel):
    contents: List[str] = Field(default=[], description="List of relevant and meaningful information")
    ingestor: Optional[Any] = Field(default=None, description="Optional Ingestor instance")

    class Config:
        arbitrary_types_allowed = True


class SQLQueryInput(BaseModel):
    sql: str = Field(description="The SQL query to execute")

    class Config:
        arbitrary_types_allowed = True


class CodeInterpreterInput(BaseModel):
    python_code: str = Field(description="Python Code Snippet")


def search(queries: List[str], top_k: int = 2, vector_store: Optional[VectorStore] = None):
    vector_store = vector_store or default_vector_store
    results = vector_store.search_text(queries=queries, top_k=top_k)
    return json.dumps(results, indent=4,
                      ensure_ascii=False) + "\n\n\nNote: If you are using this information to provide an answer, you must cite the sources (if applicable).".upper()


def text_to_image_search(queries: List[str], top_k: int = 2, vector_store: Optional[VectorStore] = None):
    vector_store = vector_store or default_vector_store
    results = vector_store.search_text_to_image(queries=queries, top_k=top_k)
    return json.dumps(results, indent=4, ensure_ascii=False)


def image_to_image_search(queries: List[str], top_k: int = 2, vector_store: Optional[VectorStore] = None):
    vector_store = vector_store or default_vector_store
    results = vector_store.image_to_image(queries=queries, top_k=top_k)
    return json.dumps(results, indent=4, ensure_ascii=False)


def index_contents_in_vector_store(contents: List[str], ingestor: Optional[Ingestor] = None):
    if ingestor:
        asyncio.run(ingestor.ingest_content(contents))
    return "All memories/contents indexed in vector store"


todo_manager = TodoManager()


def execute_todo_query(sql: str):
    results = todo_manager.execute_sql_query(sql)
    return json.dumps(results, indent=4, ensure_ascii=False)


python_interpreter_obj = CodeInterpreter()


def python_interpreter(python_code: str):
    return str(execute_python_code(pycode=python_code, code_interpreter=python_interpreter_obj))[:500]


tool_manager = ToolManager()

tool_manager.register_tool(
    func=search,
    name="search",
    description="To retrieve information(similar to queries) from indexed content",
    full_arg_spec=SemanticDocumentSearchInput,
    return_direct=True,
    exposed_args=['queries', 'top_k']
)

tool_manager.register_tool(
    func=text_to_image_search,
    name="text_to_image_search",
    description="To retrieve images that are similar to queries.",
    full_arg_spec=SemanticTextToImageSearchInput,
    return_direct=True,
    exposed_args=['queries', 'top_k']
)

tool_manager.register_tool(
    func=image_to_image_search,
    name="image_to_image_search",
    description="To retrieve images that are similar to the input image.",
    full_arg_spec=SemanticImageToImageSearchInput,
    return_direct=True,
    exposed_args=['queries', 'top_k']
)

tool_manager.register_tool(
    func=index_contents_in_vector_store,
    name="index_contents_in_vector_store",
    description="To store/memoize relevant information in the vector store.",
    full_arg_spec=IndexContentsInVectorStoreInput,
    return_direct=True,
    exposed_args=['contents']
)

tool_manager.register_tool(
    func=execute_todo_query,
    name="execute_todo_query",
    description="To execute a custom SQL query to manage ToDo.",
    full_arg_spec=SQLQueryInput,
    return_direct=True,
    exposed_args=['sql']
)

tool_manager.register_tool(
    func=python_interpreter,
    name="python_interpreter",
    description="To execute python code in stateful Ipykernel Environment",
    full_arg_spec=CodeInterpreterInput,
    return_direct=True,
    exposed_args=['python_code']
)

# # Example tool execution
# result = tool_manager.execute_tool("search", {"queries": ["example query"]})
# print(result)
#
# result = tool_manager.execute_tool("text_to_image_search", {"queries": ["example query"]})
# print(result)
#
# # result = tool_manager.execute_tool("image_to_image_search", {"img": ["example_image_uri"]})
# # print(result)
#
# # Get the OpenAI-compatible description
# description = tool_manager.get_tool_description("search")
# print(description)
#
# description = tool_manager.get_tool_description("text_to_image_search")
# print(description)
#
# # description = tool_manager.get_tool_description("image_to_image_search")
# # print(description)
#
# print(tool_manager.get_all_tool_descriptions())
