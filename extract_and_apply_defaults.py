import ast
import argparse
import textwrap
import os
import sys
import importlib
import inspect
import libcst as cst
from libcst import Param

defaults: set[str] = set()

# LibCST transformation that adds a default value to a given parameter in a given file
class ParameterDefaultAdder(cst.CSTTransformer):
    def __init__(self, func_or_method: str, param_name: str, default_str: str):
        self.param_name = param_name
        self.default = cst.parse_expression(default_str)
        if '.' in func_or_method:
            self.class_name, self.func_name = func_or_method.split('.')
        else:
            self.class_name = None
            self.func_name = func_or_method
        self.inside_target_class = self.class_name is None  # True for top-level functions

    def visit_ClassDef(self, node: cst.ClassDef) -> None:
        if self.class_name and node.name.value == self.class_name:
            self.inside_target_class = True
        elif not self.class_name:
            self.inside_target_class = False

    def leave_ClassDef(self, original_node: cst.ClassDef, updated_node: cst.ClassDef) -> cst.ClassDef:
        if self.class_name and updated_node.name.value == self.class_name:
            self.inside_target_class = False
        elif not self.class_name:
            self.inside_target_class = True
        
        return updated_node

    def leave_FunctionDef(
        self, original_node: cst.FunctionDef, updated_node: cst.FunctionDef
    ) -> cst.FunctionDef:
        if not self.inside_target_class:
            return updated_node
        if original_node.name.value != self.func_name:
            return updated_node
        new_params: list[Param] = []
        for param in updated_node.params.params:
            if param.name.value == self.param_name and param.default:
                new_param = param.with_changes(default=self.default)
                new_params.append(new_param)
            else:
                new_params.append(param)
        return updated_node.with_changes(
            params=updated_node.params.with_changes(params=new_params)
        )


# This function applies a type annotation to a parameter
def add_default_to_parameter(filename: str, function: str, parameter: str, annotation: str) -> None:
    with open(filename, "r") as f:
        code = f.read()
    module = cst.parse_module(code)
    transformer = ParameterDefaultAdder(function, parameter, annotation)
    modified_module = module.visit(transformer)
    with open(filename, "w") as f:
        f.write(modified_module.code)


def get_source(mod: str, func: str) -> str | None:
    try:
        module = importlib.import_module(mod)
        if '.' in func:
            cls_name, method_name = func.split('.', 1)
            cls = getattr(module, cls_name, None)
            if cls is None:
                return None
            obj = getattr(cls, method_name, None)
        else:
            obj = getattr(module, func, None)
        if obj is None:
            return None
        return textwrap.dedent(inspect.getsource(obj))
    except Exception as e:
        print(e)
        return None


def get_module_path(root: str, file_path: str) -> str:
    rel_path = os.path.relpath(file_path, root)
    no_ext = os.path.splitext(rel_path)[0]
    return no_ext.replace(os.path.sep, '.')


# Get any parameters from the stub that have a default of `...`
def get_ellipsis_params(func_def: ast.FunctionDef) -> list[str]:
    args = func_def.args
    num_defaults = len(args.defaults)
    ellipsis_params: list[str] = []

    # Defaults align to the last N positional args
    for arg, default in zip(args.args[-num_defaults:], args.defaults):
        if isinstance(default, ast.Constant) and default.value is Ellipsis:
            ellipsis_params.append(arg.arg)

    # Similarly check kwonlyargs
    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        if isinstance(default, ast.Constant) and default.value is Ellipsis:
            ellipsis_params.append(kwarg.arg)

    return ellipsis_params


def get_param_default_from_source(source: str ,func_def: ast.FunctionDef, name: str) -> str | None:
    args = func_def.args
    num_defaults = len(args.defaults)
    # Defaults align to the last N positional args
    for arg, default in zip(args.args[-num_defaults:], args.defaults):
        if arg.arg == name:
            if isinstance(default, ast.Constant):
                return ast.get_source_segment(source, default)
            if (
                isinstance(default, ast.UnaryOp)
                and isinstance(default.op, ast.USub)
                and isinstance(default.operand, ast.Constant)
            ):
                # Handle case when default is negative number, e.g. `axis=-1`.
                return f'-{ast.get_source_segment(source, default.operand)}'
            return None
    # Similarly check kwonlyargs
    for kwarg, default in zip(args.kwonlyargs, args.kw_defaults):
        if kwarg.arg == name:
            if isinstance(default, ast.Constant):
                return ast.get_source_segment(source, default)
            return None
    return None


def extract_param_default(source: str, param: str) -> str | None:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            return get_param_default_from_source(source, node, param)
    return None


# For any parameters in the stub with default `...`, try to guess the type from the docstring
def process_function(module: str, class_name: str | None, func_node: ast.FunctionDef, pkg_name: str, root: str) -> None:
    if func_node.name.startswith('__') and func_node.name.endswith('__'):
        return
    func_name = f"{class_name}.{func_node.name}" if class_name else func_node.name
    source = get_source(f"{pkg_name}.{module}", func_name)
    if source is None:
        return
    global defaults
    for arg in get_ellipsis_params(func_node):
        if arg in {'self', 'cls'}:
            continue
        arg_default = extract_param_default(source, arg)
        if arg_default is None:
            continue
        path = root + "/" + module.replace(".", "/") + ".pyi"
        add_default_to_parameter(path, func_name, arg, arg_default)
        defaults.add(arg_default)


def process_file(root: str, file_path: str, pkg_name: str) -> None:
    module = get_module_path(root, file_path)
    with open(file_path, "r", encoding="utf-8") as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return
    for node in tree.body:
        if isinstance(node, ast.FunctionDef):
            process_function(module, None, node, pkg_name, root)
        elif isinstance(node, ast.ClassDef):
            for item in node.body:
                if isinstance(item, ast.FunctionDef):
                    process_function(module, node.name, item, pkg_name, root)


def walk_directory(root: str, pkg_name: str) -> None:
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(".pyi"):
                process_file(root, os.path.join(dirpath, filename), pkg_name)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stubs", help="Stubs root directory")
    parser.add_argument("package", help="Runtime package")
    args = parser.parse_args()
    walk_directory(args.stubs, args.package)
