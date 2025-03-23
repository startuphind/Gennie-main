import ast
import io
import os
import sys
import signal
import subprocess
import matplotlib.pyplot as plt
import pandas as pd
from contextlib import redirect_stdout
from functools import wraps
from IPython.core.interactiveshell import InteractiveShell

ALLOWED_LIBRARIES = {"numpy", "math", "sympy", "time", "itertools", "random", "json", "matplotlib", "pandas"}


def timeout_decorator(timeout=5):
    def decorator(func):
        def handler(signum, frame):
            raise TimeoutError("Code execution timed out")

        @wraps(func)
        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, handler)
            signal.alarm(timeout)
            try:
                result = func(*args, **kwargs)
            except TimeoutError as e:
                return {"status": "error", "error": "Code execution timed out"}
            finally:
                signal.alarm(0)
            return result

        return wrapper

    return decorator


class CodeInterpreter:
    ALLOWED_LIBRARIES = {"numpy", "math", "sympy", "time", "itertools", "random", "json", "matplotlib", "pandas"}
    ARTIFACTS_DIR = './artifacts'

    def __init__(self):
        self.shell = InteractiveShell()
        if not os.path.exists(self.ARTIFACTS_DIR):
            os.makedirs(self.ARTIFACTS_DIR)

    def reset(self):
        self.shell.reset()

    def _extract_imported_libraries(self, code):
        tree = ast.parse(code)
        return {node.names[0].name for node in ast.walk(tree) if isinstance(node, ast.Import)}

    def _is_allowed_libraries(self, libraries):
        return libraries.issubset(self.ALLOWED_LIBRARIES)

    def _modify_code_to_print_last_expression(self, code):
        tree = ast.parse(code)
        last_node = tree.body[-1] if tree.body else None

        if isinstance(last_node, ast.Expr):  # Check if the last node is an expression
            # Specifically check if the expression is a function call
            if isinstance(last_node.value, ast.Call):
                # If it's a function call, return the code unchanged
                return code
            else:
                # If it's not a function call, wrap the last expression in a print statement
                modified_code = ast.unparse(tree.body[:-1]) + f'\nprint({ast.unparse(last_node.value)})'
                return modified_code
        return code  # Return the original code if the last statement is not a simple expression

    def _install_package(self, package_name):
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package_name])
            print(f"Successfully installed {package_name}")
        except subprocess.CalledProcessError as e:
            print(f"Error installing {package_name}: {e}")

    def _handle_magic_commands(self, code):
        lines = code.split('\n')
        remaining_lines = []
        for line in lines:
            if line.startswith('!pip install'):
                package_name = line.split(' ')[-1]
                self._install_package(package_name)
            else:
                remaining_lines.append(line)
        return '\n'.join(remaining_lines)

    def _save_artifact(self, artifact, name):
        path = os.path.join(self.ARTIFACTS_DIR, name)

        if isinstance(artifact, plt.Figure):
            artifact.savefig(path)
            plt.close(artifact)
        elif isinstance(artifact, pd.DataFrame):
            artifact.to_csv(path, index=False)
        else:
            with open(path, 'w') as f:
                f.write(str(artifact))

        return path

    # @timeout_decorator(timeout=5)
    def execute(self, code):
        code = self._handle_magic_commands(code)  # Process magic commands first

        try:
            ast.parse(code)
        except SyntaxError as e:
            return {"status": "error", "error": f"Syntax error in provided code: {e}"}

        libraries_in_code = self._extract_imported_libraries(code)
        # if not self._is_allowed_libraries(libraries_in_code):
        #     return {"status": "error", "error": "Use of disallowed libraries"}

        modified_code = self._modify_code_to_print_last_expression(code)

        # Capture the output
        old_stdout = sys.stdout
        redirected_output = sys.stdout = io.StringIO()

        try:
            self.shell.run_cell(modified_code, store_history=True)
            # After capturing the output in the `execute` method:
            output = redirected_output.getvalue()
            if "TimeoutError" in output:
                return {"status": "error", "error": "Code execution timed out"}

        except TimeoutError as e:
            return {"status": "error", "error": "Code execution timed out"}
        except Exception as e:
            output = f"Error: {str(e)}"
        finally:
            sys.stdout = old_stdout

        artifacts = []
        for fig_num in plt.get_fignums():
            fig = plt.figure(fig_num)
            artifact_path = self._save_artifact(fig, f"artifact_{fig_num}.png")
            artifacts.append(artifact_path)

        result = {
            "status": "success",
            "result": output.strip(),
            "artifacts": artifacts
        }

        return result

# Example usage
# code_interpreter = CodeInterpreter()
# code = """
# !pip install matplotlib pandas
# import matplotlib.pyplot as plt
# import pandas as pd
# plt.plot([1, 2, 3], [4, 5, 6])
# plt.title('Sample Plot')
# df = pd.DataFrame({'A': [1, 2, 3], 'B': [4, 5, 6]})
# df
# """
# result = code_interpreter.execute(code)
# if result['status'] == 'success':
#     print(result['result'])
#     print("Artifacts:", result['artifacts'])