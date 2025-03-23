import re

from code_interpreter.code_interpreter import CodeInterpreter


def pycode_parser(input_string):
    # Find list of all python code snippets
    pycode_snippets = re.findall('```python(.*?)```', input_string, re.DOTALL)

    # Return the list of python code snippets
    return pycode_snippets


def code_interpreter_parser(input_string):
    # Find list of all python code snippets
    pycode_snippets = re.findall('```code_interpreter(.*?)```', input_string, re.DOTALL)

    # Return the list of python code snippets
    return pycode_snippets


def execute_python_code(pycode: str, code_interpreter=None) -> str:
    """
    To execute Python code in a restricted environment[only sympy, numpy, and math modules are allowed] and return standard output. If other tools are unsuitable or fail, manually write and run Python code in this environment."

    Parameters:
    pycode (str): Python code to execute

    Returns:
    str: Standard output of the code
    """
    if code_interpreter is None:
        code_interpreter = CodeInterpreter()
    result = code_interpreter.execute(pycode)
    if result['status'] == "error":
        result['result'] = "Error:\n" + result['error'] + "\nThink and Conquer."
    return result['result'][:500]

# code4 = """
# import time
# time.sleep(10)
# """
#
# code5 = """
# import itertools
# import random
#
# # Define constraints functions
# def does_follow_constraints(a, b, c) -> bool:
#     # Ensure a is not zero to avoid division by zero
#     if a == 0:
#         return False
#     # Calculate d to check if it's an integer
#     d = (c + b) / a
#     if not d.is_integer():
#         return False
#     return True
#
# def generate_valid_tuples(range_dict, num_unique_tuples):
#     valid_tuples = []
#     while len(valid_tuples) < num_unique_tuples:
#         a = random.choice(range_dict['a'])
#         b = random.choice(range_dict['b'])
#         c = random.choice(range_dict['c'])
#         if does_follow_constraints(a, b, c) and (a, b, c) not in valid_tuples:
#             valid_tuples.append((a, b, c))
#     return valid_tuples
#
# def range_recommenders():
#     # Recommend ranges for a, b, and c to ensure at least 1000 unique questions
#     # These ranges are chosen to ensure a wide variety of outputs while keeping the calculations simple
#     range_dict = {
#         "a": list(range(1, 21)),  # Avoid zero and keep a manageable range
#         "b": list(range(-20, 21)),  # Allow for negative and positive shifts
#         "c": list(range(-20, 21))  # Similar reasoning as for b
#     }
#     return range_dict
#
# # Test Code
# range_dict = range_recommenders()
# print("Recommended Ranges:", range_dict)
#
# # Generate 10 valid tuples as a sample
# valid_tuples = generate_valid_tuples(range_dict, 10)
# print("Sample Valid Tuples:", valid_tuples)
# """

# result5 = execute_python_code(code4)
# print(f"Result:\n {result5}")
