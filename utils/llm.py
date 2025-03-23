import asyncio
import logging
import os
import time

import aiohttp
import openai
import requests

from config.settings import OPEN_AI_API_KEY
from tool_manager import ToolManager


json_mode_supported_models = [
    "gpt-4o-mini",
    "gpt-4o",
    "gpt-3.5-turbo-1106",
    "gpt-3.5-turbo-0125",
    "gpt-4-1106-preview",
    "gpt-4-0125-preview"
]

async def openai_chat_async(model, messages, temperature, max_tokens, max_retries=4, **kwargs):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPEN_AI_API_KEY}"
    }
    # print(f"\n\n\n ========NEW REQUEST======== \n\n\n")
    retries = 0
    while retries < max_retries:
        try:
            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }

            if kwargs.get("is_json_mode_enabled") and model in json_mode_supported_models:
                payload["response_format"] = {"type": "json_object"}

            if kwargs.get("tools"):
                payload["tools"] = kwargs.get("tools")

            async with aiohttp.ClientSession() as session:
                print("new_request")
                async with session.post("https://api.openai.com/v1/chat/completions", headers=headers,
                                        json=payload) as response:
                    response_json = await response.json()
                    # print(json.dumps(response_json))

                    print(f"\n\n\n ========NEW REQUEST======== \n\n\n")
                    return response_json
        except Exception as e:
            print(f"An error occurred: {e}")
            retries += 1
            backoff_time = (3 ** retries)  # exponential backoff time
            await asyncio.sleep(backoff_time)  # wait for backoff_time seconds before retrying
    print("Max retries exceeded. Please check your inputs or try again later.")


import json
from typing import List, Dict, Any


# Assuming the ToolManager class as provided previously

# Place your ToolManager class definition here...
def open_ai_tools_execution(tool_manager: ToolManager, tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    responses = []

    for tool in tools:
        try:
            tool_id = tool["id"]
            function_name = tool["function"]["name"]
            arguments = json.loads(tool["function"]["arguments"])

            # Execute the tool using the provided ToolManager instance
            function_response = tool_manager.execute_tool(function_name, arguments)
            function_response_str = str(function_response)

            # Check if the response is longer than 7000 characters
            if len(function_response_str) > 7000:
                function_response_str = function_response_str[
                                        :7000] + " RESPONSE IS CUTTED BECAUSE OF MORE THAN 1000 CHARS"

            # Format the successful response
            response = {
                "tool_call_id": tool_id,
                "role": "tool",
                "name": function_name,
                "content": function_response_str
            }
        except Exception as e:
            # Format the error response
            response = {
                "tool_call_id": tool_id,
                "role": "tool",
                "name": function_name,
                "content": f"Error: {str(e)}"
            }

        responses.append(response)

    return responses


# # Example usage
# tools_input = [
#     {
#         "id": "call_Hz0kaYHs0tOYQ5rGaCvxuScT",
#         "type": "function",
#         "function": {
#             "name": "semantic_document_search",
#             "arguments": "{\"queries\":[\"Rohan's phone number\",\"Rohan contact information\",\"Rohan phone\"]}"
#         }
#     }
# ]
#
# # Assuming `tool_manager` is already created and tools are registered
# result = open_ai_tools_execution(tool_manager, tools_input)
# print(result)
