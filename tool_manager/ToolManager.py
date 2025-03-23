import json
import logging
from typing import Callable, Type, List, Dict, Any
from pydantic import BaseModel, Field
from tool_manager.BaseToolManager import BaseToolManager


class ToolManager(BaseToolManager):

    def __init__(self):
        self.tools = {}

    def register_tool(self, func: Callable, name: str, description: str,
                      full_arg_spec: Type[BaseModel], return_direct: bool,
                      exposed_args: List[str]) -> None:
        self.tools[name] = {
            "func": func,
            "description": description,
            "full_arg_spec": full_arg_spec,
            "return_direct": return_direct,
            "exposed_args": exposed_args
        }

    def unregister_tool(self, tool_name: str) -> None:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered.")
        del self.tools[tool_name]

    def execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Any:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered.")
        tool = self.tools[tool_name]
        validated_args = tool["full_arg_spec"](**tool_args)
        result = tool["func"](**validated_args.model_dump())
        return result if tool["return_direct"] else {"result": result}

    def get_tool_description(self, tool_name: str) -> dict:
        if tool_name not in self.tools:
            raise ValueError(f"Tool '{tool_name}' not registered.")
        tool = self.tools[tool_name]
        schema = tool["full_arg_spec"].model_json_schema()
        properties = {}

        for field in tool["exposed_args"]:
            field_schema = schema['properties'][field]
            field_type = field_schema['type']

            # Handling array type
            if field_type == 'array':
                item_type = field_schema['items']['type']
                properties[field] = {
                    "type": "array",
                    "items": {"type": item_type},
                    "description": field_schema.get('description', 'No description available')
                }
            # Handling other types
            else:
                properties[field] = {
                    "type": field_type,
                    "description": field_schema.get('description', 'No description available')
                }

        openai_tool_description = {
            "type": "function",
            "function": {
                "name": tool_name,
                "description": tool["description"],
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": tool["exposed_args"]
                },
            }
        }
        return openai_tool_description

    def get_all_tool_descriptions(self) -> List[dict]:
        """
        Get the OpenAI tool descriptions for all registered tools.
        """
        if not self.tools:
            return []
        # Get the OpenAI tool descriptions for all registered tools.
        # tool_descriptions = [self.get_tool_description(name) for name in self.tools]
        # return tool_descriptions
        # Get the OpenAI tool descriptions for all registered tools.
        tool_descriptions = [self.get_tool_description(name) for name in self.tools]
        return tool_descriptions

    def list_tools(self) -> Dict[str, Any]:
        return {name: tool["description"] for name, tool in self.tools.items()}




# # TESTS
# class CalculatorInput(BaseModel):
#     a: int = Field(default=0, description="first number")
#     b: int = Field(default=0, description="second number")
#
#
# class AdvancedCalculatorInput(CalculatorInput):
#     c: int = Field(default=1, description="Hidden multiplier")
#     d: int = Field(default=1, description="Another hidden multiplier")
#
#
# def multiply(a: int, b: int, c: int = 1, d: int = 1) -> int:
#     """Multiply the numbers."""
#     return a * b * c * d
#
#
# tool_manager = ToolManager()
#
# tool_manager.register_tool(
#     func=multiply,
#     name="advanced_multiply",
#     description="Multiply numbers with optional hidden multipliers.",
#     full_arg_spec=AdvancedCalculatorInput,
#     return_direct=True,
#     exposed_args=['a', 'b']
# )
#
# # Example tool execution
# result = tool_manager.execute_tool("advanced_multiply", {"a": 3, "b": 4, "c": 5, "d": 6})
# print(result)
#
# # Get the OpenAI-compatible description
# description = tool_manager.get_tool_description("advanced_multiply")
# print(description)
