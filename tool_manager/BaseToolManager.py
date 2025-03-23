from abc import ABC, abstractmethod
from typing import Callable, Type, Dict, Any, List
from pydantic import BaseModel


class BaseToolManager(ABC):

    @abstractmethod
    def register_tool(self, func: Callable, name: str, description: str,
                      full_arg_spec: Type[BaseModel], return_direct: bool,
                      exposed_args: List[str]) -> None:
        """
        Register a new tool with the manager.
        """
        pass

    @abstractmethod
    def unregister_tool(self, tool_name: str) -> None:
        """
        Unregister a tool by name.
        """
        pass

    @abstractmethod
    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        """
        Execute a tool by name with the provided arguments.
        """
        pass

    @abstractmethod
    def get_tool_description(self, tool_name: str) -> dict:
        """
        Get the OpenAI tool description for a specific tool by name.
        """
        pass

    @abstractmethod
    def get_all_tool_descriptions(self) -> List[dict]:
        """
        Get the OpenAI tool descriptions for all registered tools.
        """
        pass

    @abstractmethod
    def list_tools(self) -> Dict[str, Any]:
        """
        List all registered tools and return their metadata.
        """
        pass
