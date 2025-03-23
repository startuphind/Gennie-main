import asyncio
import json
import logging
import re

import tzlocal
from langchain_core.prompts import PromptTemplate

from code_interpreter.code_interpreter_utils import pycode_parser, code_interpreter_parser, execute_python_code


from datetime import datetime

from tools import tool_manager
from utils.llm import open_ai_tools_execution, openai_chat_async

sys_prompt_template = """You are Gennie, a super-intelligent assistant capable of performing various tasks such as computations, managing ToDo lists, answering user queries, remembering information, and handling file management tasks (limited to the root directory and its subdirectories).
You have full access to the root directory [{root_directory}] and its subdirectories. All documents and images in these directories are indexed in a vector store.

Your capabilities include:
1. **Python Interpreter**:
   - Execute Python code in a stateful Jupyter Notebook-like environment.
   - Perform file management tasks.
   - Solve mathematical and computational problems using Python.

2. **Semantic/Vector Search & Store APIs**:
   - Access and use search apis to retrieve relevant information from local knowledge base.
   - Understand user intent and provide accurate answers with precise citations.
   - Memorize and recall relevant information during interactions.

3. **Database Management**:
   - Execute SQL queries to manage databases using the provided schema:
     ```sql
     ToDoSchema:
     id INTEGER PRIMARY KEY AUTOINCREMENT,
     task TEXT NOT NULL,
     status TEXT NOT NULL,    //["NOT_STARTED", "PROGRESS", "FINISH"]
     created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
     due_date TIMESTAMP,
     categories TEXT
     ```

### Always Follow these Guidelines:
1. Treat access to the root directory ({root_directory}) as access to a physical file system.
2. For LaTeX, use the following syntax:
   $$ <latex_block> $$
   $<latex_inline>$
3. To provide file URIs, must use this markdown format: ![<alt_text>](file://<dir>/<sub_dir>/...file.extension)
    - To cite the exact page of pdf use this format: file://<dir>/<sub_dir>/...file.pdf#page=5
    - Always use markdown format.
4. If the user query demands task completion, break the tasks into multiple subtasks, create a plan, and execute it.
5. When processing an image, always ask the user to verify the image since you only know its path/source.
6. Never Provide Inaccurate Answer and If your response relies on information from search, make sure to cite the sources using proper markdwon format.

### Learn use & innovate on these skills and examples:
**Example 1:**
- **Task:** Answer a user question.
- **Steps:**
  1. Use search to find relevant informations and, if needed, break the query into parts.
  2. Provide a precise answer with **accurate citations** in markdown format, or apologize if you cannot provide an answer.

**Example 2:**
- **Task:** Solve a math problem.
- **Steps:**
  1. Estimate the difficulty level and user intent.
  2. Solve step-by-step using Code Interpreter for computations.
  3. Provide a well-formatted step-by-step solution in LaTeX-markdown syntax.

**Example 3:**
- **Task:** Save a ToDo.
- **Steps:**
  1. Gather required information from the user.
  2. Save the ToDo.

**Example 4:**
- **Task:** Data analysis.
- **Steps:**
  1. If needed, get the file path/source from the user.
  2. Use Code Interpreter to:
     - Download and import necessary libraries.
     - Perform analysis step-by-step.
     - Save and present visual results in markdown format.
  3. If needed interact with user during analysis

**Example 5:**
- **Task:** Find the image [Dog playing in Field], apply Canny edge detection, and provide the new image.
- **Steps:**
  1. Use search to find the top relevant image.
  2. Interact with user for verification
  3. Use Code Interpreter to:
     - Install required libraries.
     - Load the file using source information.
     - Perform image processing.
     - Save the image as a file.
     - Reveal the path to the user using markdown syntax.
"""

sys_prompt = PromptTemplate(
    input_variables=['root_directory'],
    template=sys_prompt_template
)

init_prompt_template = """I am a backend service. Here is a query from a user (name={user_name}):
 ``` 
 {user_query} 
 ``` 
 - **Current Timestamp**: {curr_time_stamp}

Please follow these steps to address the query:
1. **Planning**: Analyze the query and strategize an effective response. Consider the necessity of tools for the task.
2. **Utilize Tools**: Deploy the appropriate tools and functions to provide an accurate response.
3. **Efficient Resolution**: Aim to resolve the user’s query within three interactions to maintain efficiency.
4. **Response Format**: Adhere to the following guidelines and format your response in Markdown. Include proper citations in Markdown where applicable.

Always structure your response as follows:
```
# Processing
<Describe your thought process, planning, and any actions (like ToolCalls) taken to resolve the user query, along with recalling important guidelines>

## Need To Use Tool: Yes/No

# Reply To User: Yes/No      // Yes if you have resolved the user query, otherwise No
<Your reply to the user in Markdown format, or leave empty in case of ToolCalls>
```
"""

continue_prompt = """Please continue, until you obtain the final result."""

termination_string = """"# Reply To User: Yes"""
forced_task_completion_prompt = """NOW, YOU CAN'T EXECUTE CODE & USE TOOLS ANYMORE, NOR CAN WE INTERACT FURTHER. SO, PLEASE REPLY TO USER IN THIS FORMAT:
# Reply To User: Yes
<Your reply to the user in Markdown format, or leave empty in case of ToolCalls>
"""
forced_task_completion_format = """# Reply To User: Yes
<Your reply to the user in Markdown format, or leave empty in case of ToolCalls>
"""
max_loop_count = 5

init_prompt = PromptTemplate(
    input_variables=["user_name", "user_query", "curr_time_stamp"],
    template=init_prompt_template
)


def parser(input_string: str):
    if input_string.endswith("```"):
        input_string = input_string[:-3]

    if input_string.endswith("```\n"):
        input_string = input_string[:-4]

    # Split the response into lines
    lines = input_string.strip().splitlines()

    # Initialize dictionary to hold the content
    content_dict = {
        "processsing": "",
        "reply": "",
    }

    # Temporary variables to hold the current section and content
    current_section = None
    content = []

    # Define a mapping from headers to dictionary keys
    section_headers = {
        "# Processing": "processing",
        "# Reply To User: Yes": "reply",
    }

    # Iterate through each line
    for line in lines:
        # Check if the line is a section header
        if line.strip() in section_headers:
            # If there is an ongoing section, save its content to the dictionary
            if current_section:
                content_dict[current_section] = "\n".join(content).strip()
                content = []  # Reset content for the next section

            # Update the current section
            current_section = section_headers[line.strip()]
        else:
            # If it's not a header, append the line to the content list
            content.append(line)

    # After the loop, save the last section's content
    if current_section:
        content_dict[current_section] = "\n".join(content).strip()
    # print(content_dict)
    return content_dict


def get_beautified_current_time():
    # Get the local timezone
    local_timezone = tzlocal.get_localzone()

    # Get the current time in the local timezone
    now = datetime.now(local_timezone)

    # Format the current time with timezone
    beautified_time = now.strftime('%A, %B %d, %Y, %I:%M %p %Z')

    return beautified_time


async def gennie(model: str = "gpt-4o", user_query="", user_name: str = "", history: list = [],
                 root_directory="./working", verbose: bool = False):
    token_usage = []
    messages = build_initial_messages(user_query=user_query, user_name=user_name, root_directory=root_directory,
                                      history=history)
    # print(f"INPUT MESSAGES:\n{messages}")
    tools = tool_manager.get_all_tool_descriptions()
    gpt_response_count = 0
    while gpt_response_count <= max_loop_count:
        completion = await openai_chat_async(
            model=model,
            messages=messages,
            temperature=0,
            max_tokens=4000,
            tools=tools,
            verbose=verbose
        )
        # print(type(completion))
        # print(completion)

        messages.append(completion['choices'][0]['message'])
        print(json.dumps(messages, indent=4, ensure_ascii=False))

        # Handle Tools Call:
        if 'tool_calls' in completion['choices'][0]['message'] and len(completion['choices'][0]['message']['tool_calls'])>0:
            tool_calls = completion['choices'][0]['message']['tool_calls']
            res = open_ai_tools_execution(tools=tool_calls, tool_manager=tool_manager)
            # print(json.dumps(res, indent=4, ensure_ascii=False))
            messages.extend(res)
            # print(json.dumps(messages, indent=4, ensure_ascii=False))
        else:
            assistant_response = completion['choices'][0]['message']['content']
            # print(f"YESS: {assistant_response}")
            log_verbose(verbose, f"\n\nAssistant Response: \n {assistant_response}")
            update_token_usage(token_usage, model, completion['usage'])

            res = parser(assistant_response)
            # print("TERMINATED")
            if res['reply'] != "":
                return {
                    "reply": res['reply'],
                    "token_usage": token_usage,
                    "messages": messages,
                }
            else:
                messages.append({
                    "role": "user",
                    "content": continue_prompt
                })
        gpt_response_count += 1

    result = await handle_exceeded_interactions_async(messages, model, token_usage, verbose)
    # Delete the first element of messages
    return result


def build_initial_messages(user_query="", user_name: str = "", history: list = [], root_directory="./working"):
    if len(history) > 0:
        history.append({
            "role": "user",
            "content": f"Another User Query\n```{user_query}\n```\n\n Current Time: {get_beautified_current_time()}"
        })
        return history
    else:
        messages = [
            {
                "role": "system",
                "content": sys_prompt.format(root_directory=root_directory)
            },
            {
                "role": "user",
                "content": init_prompt.format(user_name=user_name, user_query=user_query,
                                              curr_time_stamp=get_beautified_current_time())
            }
        ]
        return messages


def log_verbose(verbose, message):
    if verbose:
        logging.info(message)


def update_token_usage(token_usage, model, usage, component="solver"):
    token_usage.append({"model": model, "usage": usage, "component": component})


def handle_pycode_snippets(assistant_response, messages, code_interpreter, verbose):
    pycode_snippets = code_interpreter_parser(assistant_response)
    if not pycode_snippets:
        messages.append({"role": "user",
                         "content": continue_prompt
                         })
    else:
        execution_result = execute_and_collect_results(pycode_snippets, code_interpreter)
        log_verbose(verbose, f"\n\nPycode Snippets: {pycode_snippets}\n\n")
        messages.append({"role": "user", "content": "Execution Result:\n" + execution_result})


def execute_and_collect_results(pycode_snippets, code_interpreter):
    execution_result = "\n\n".join(str(execute_python_code(pycode, code_interpreter)) for pycode in pycode_snippets)
    return execution_result


async def handle_exceeded_interactions_async(messages, model, token_usage, verbose):
    # Send a warning message if the interaction limit is reached without a final result
    log_verbose(verbose,
                f"\n\nWARNING: MAXIMUM INTERACTION LIMIT REACHED\nTERMINATION INITIATED\nUser: {forced_task_completion_prompt}\n")
    messages.append({"role": "user", "content": forced_task_completion_prompt})

    # Make a final call to GPT to attempt to get a conclusive response
    completion = await openai_chat_async(model=model, messages=messages, temperature=0, max_tokens=4000)
    update_token_usage(token_usage, model, completion['usage'])
    assistant_response = completion['choices'][0]['message']['content']
    log_verbose(verbose, f"\n\nFinal response by GPT (as maximum interaction limit reached):\n{assistant_response}\n")
    messages.append({"role": "assistant", "content": assistant_response})

    res = parser(assistant_response)
    print("TERMINATED")
    if res['reply'] != "":
        return {
            "reply": res['reply'],
            "token_usage": token_usage,
            "messages": messages,
        }

    else:
        messages.append({
            "role": "user",
            "content": continue_prompt
        })
        # Make a final call to GPT to attempt to get a conclusive response
        completion = await openai_chat_async(model=model, messages=messages, temperature=0, max_tokens=4000)
        update_token_usage(token_usage, model, completion['usage'])
        assistant_response = completion['choices'][0]['message']['content']
        log_verbose(verbose,
                    f"\n\nFinal response by GPT (as maximum interaction limit reached):\n{assistant_response}\n")
        messages.append({"role": "assistant", "content": assistant_response})
        # If not, return an error indicating the interaction limit was reached without a conclusive result
        return {
            "reply": assistant_response,
            "token_usage": token_usage,
            "messages": messages,
        }


# # logging
# logging.basicConfig(level=logging.INFO)
# input = {
#     "model": "gpt-4-turbo",
#     "user_name": "Rohan",
#     "user_query": "Provide me the tree view of my filesys",
#     "verbose": True
# }
# res = asyncio.run(gennie(**input))
# print(res)
# print(parser(test))
