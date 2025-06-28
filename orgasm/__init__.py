import argparse
from pathlib import Path
import sys
import traceback
from typing import Dict 
import inspect 
from orgasm.command_class_inspector import * 
from xmlrpc.server import SimpleXMLRPCServer
from xmlrpc.server import SimpleXMLRPCRequestHandler
from socketserver import ThreadingMixIn
import xmlrpc.client
try:
    import argcomplete
except ImportError:
    argcomplete = None


class SuperFunction:
    def __init__(self, func, tags = None, attrs = None):
        self.func = func
        self.tags = tags if tags is not None else []
        self.attrs = attrs if attrs is not None else {}
    
    def __call__(self, *args, **kwargs):
        return self.func(*args, **kwargs)
    
    def __getitem__(self, item):
        if item in self.attrs:
            return self.attrs[item]
        raise KeyError("Attribute %s not found" % item)
    
    def __setitem__(self, key, value):
        self.attrs[key] = value
    
    def __iter__(self):
        return iter(self.tags)
    
def is_super_function(obj):
    """
    Check if the object is a SuperFunction.
    :param obj: object to check
    :return: True if the object is a SuperFunction, False otherwise
    """
    return isinstance(obj, SuperFunction)

def attr(**kwargs):
    """
    Decorator to add an attribute to a function.
    :param key: attribute key
    :param value: attribute value
    :return: decorated function
    """
    def decorator(func):
        if not is_super_function(func):
            func = SuperFunction(func)
        for key, value in kwargs.items():
            func[key] = value
        return func
    return decorator

def tag(*tags):
    """
    Decorator to add tags to a function.
    :param tags: tags to add
    :return: decorated function
    """
    def decorator(func):
        if not is_super_function(func):
            func = SuperFunction(func)
        for tag in tags:
            func.tags.append(tag)
        return func
    return decorator



def get_command_specs(classes):
    spec = []
    available_commands = []
    for cls in classes:
        available_commands += get_available_commands(cls)
    for command in available_commands:
        for cls in classes:
            if hasattr(cls, command):
                f = getattr(cls, command)
                if is_super_function(f):
                    f = f.func
                args = [] 
                for arg in get_arguments(f):
                    args.append({
                        "name": arg,
                        "required": True,
                        "type": get_arg_type(f, arg),
                        "help": get_arg_description(f, arg),
                    })
                    if hasattr(cls, "VALID_VALUES") and getattr(cls, "VALID_VALUES").get(command, {}).get(arg, None) is not None:
                        args[-1]["valid_values"] = getattr(cls, "VALID_VALUES")[command][arg]
                    else:
                        args[-1]["valid_values"] = None
                for arg, value in get_optional_arguments(f):
                    args.append({
                        "name": arg,
                        "required": False,
                        "type": get_arg_type(f, arg),
                        "help": get_arg_description(f, arg),
                        "default": value
                    })
                    if hasattr(cls, "VALID_VALUES") and getattr(cls, "VALID_VALUES").get(command, {}).get(arg, None) is not None:
                        args[-1]["valid_values"] = getattr(cls, "VALID_VALUES")[command][arg]
                    else:
                        args[-1]["valid_values"] = None
                spec.append({
                    "name": command,
                    "args": args,
                    "method_name": command,
                    "attrs": getattr(cls, command).attrs if  is_super_function(getattr(cls, command)) else {},
                    "tags": getattr(cls, command).tags if is_super_function(getattr(cls, command)) else []
                })
    return spec

def execute_command(classes, command: str, params):
    spec = get_command_specs(classes)
    command = [x for x in spec if x["name"] == command]
    if len(command) == 0:
        raise ValueError("Command %s not found" % command)
    command = command[0]
    for cls in classes:
        executor = cls()
        if hasattr(executor, command["method_name"]):
            m = getattr(executor, command["method_name"])
            A = {}
            for arg in command["args"]:
                if arg != "self":
                    if arg["name"] in params:
                        A[arg["name"]] = params[arg["name"]]
                    else:
                        if "default" in arg:
                            A[arg["name"]] = arg["default"]
                        else:
                            raise ValueError("Argument %s is required" % arg)
                # if arg is type PathLike then check if path exists
                if arg["type"] == Path:
                    if not Path(A[arg["name"]]).exists():
                        raise ValueError("Path %s does not exist" % A[arg])
                if not isinstance(A[arg["name"]], arg["type"]):
                    try:
                        if arg["type"] == bytes and isinstance(A[arg["name"]], xmlrpc.client.Binary):
                            A[arg["name"]] = A[arg["name"]].data
                        else:
                            A[arg["name"]] = arg["type"](A[arg["name"]])
                    except:
                        traceback.print_exc()
                        raise ValueError("Invalid value for argument %s" % arg["name"])
                if arg["valid_values"] is not None:
                    if A[arg["name"]] not in arg["valid_values"]:
                        raise ValueError("Invalid value %s for argument %s" % (A[arg], arg))
            if is_super_function(m):
                return m(executor, **A)
            else:
                return m(**A)
    raise ValueError("Command %s not found" % command)

def command_executor_main(classes, explicit_params=True):
    """
    Command line interface for executing commands in classes.
    :param classes: list of classes to execute commands from
    :param explicit_params: if True, all parameters must be specified in the command line which are required for the command. If False, then only values for these parameters which are not default values must be specified.

    Example:
    if we have class with method `def foo(self, a: int, *, b: str = "default", c: str = "default")` then:
    if explicit_params = True, then we must specify all parameters in the command line:
        app foo --a 1 
    if explicit_params = False, then we can specify only the parameters which are not default values:
        app foo 1 
    """
    if not isinstance(classes, list):
        classes = [classes]
    parser = argparse.ArgumentParser()
    command_parsers = parser.add_subparsers(dest="command")
    spec = get_command_specs(classes)
    commands: Dict[str, argparse.ArgumentParser] = {}
    for command in spec:
        commands[command["name"]] = command_parsers.add_parser(command["name"])
        short_options = set()
        for arg in command["args"]:
            parser_params = {}
            if arg["type"] != bool:
                if not explicit_params and arg["required"]:
                    commands[command["name"]].add_argument("%s" % arg["name"],
                        type=arg["type"],
                        help=arg["help"],
                        choices=arg["valid_values"],
                        default=arg.get("default", None),
                        action="store" 
                    )
                else:
                    short = ""
                    if arg["name"][0] not in short_options:
                        short = "-%s " % arg["name"][0]
                        short_options.add(arg["name"][0])
                    if short != "":
                        commands[command["name"]].add_argument(short, "--%s" % arg["name"].replace("_", "-"),
                            required=arg["required"], 
                            type=arg["type"],
                            help=arg["help"],
                            choices=arg["valid_values"],
                            default=arg.get("default", None),
                            action="store" 
                        )
                    else:
                        commands[command["name"]].add_argument("--%s" % arg["name"].replace("_", "-"),
                            required=arg["required"], 
                            type=arg["type"],
                            help=arg["help"],
                            choices=arg["valid_values"],
                            default=arg.get("default", None),
                            action="store" 
                        )
            else:
                short = ""
                if arg["name"][0] not in short_options:
                    short = "-%s " % arg["name"][0]
                    short_options.add(arg["name"][0])
                if short != "":
                    commands[command["name"]].add_argument(short, "--%s" % arg["name"].replace("_", "-"),
                        required=arg["required"], 
                        help=arg["help"],
                        action="store_true" 
                    )
                else:
                    commands[command["name"]].add_argument("--%s" % arg["name"].replace("_", "-"),
                        required=arg["required"], 
                        help=arg["help"],
                        action="store_true" 
                    )    
    if argcomplete is not None:
        argcomplete.autocomplete(parser)
    args, _ = parser.parse_known_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)
    params = {}
    command = [x for x in spec if x["name"] == args.command]
    if len(command) == 0:
        raise ValueError("Command %s not found" % args.command)
    command = command[0]
    for arg in command["args"]:
        if arg["name"] in vars(args):
            params[arg["name"]] = getattr(args, arg["name"])
    try:
        result = execute_command(classes, args.command, params)
        if isinstance(result, str):
            print(result)
        elif isinstance(result, dict):
            for k, v in result.items():
                print("%s: %s" % (k, v))
        elif isinstance(result, list):
            for item in result:
                print(item)
        else:
            print(result)
    except Exception as e:
        # print("Error: %s" % e)
        # sys.exit(1)
        raise e

def get_classes(module_name):
    import importlib
    module = importlib.import_module(module_name)
    names = dir(module)
    if hasattr(module, "COMMAND_CLASSES"):
        names = getattr(module, "COMMAND_CLASSES")
    classes = {}
    for name in names:
        obj = getattr(module, name)
        if inspect.isclass(obj):
            classes[name] = obj
    result = list(classes.values())
    return result

def command_executor_rpc(classes, port: int = 8000):
    if not isinstance(classes, list):
        classes = [classes]
    class RequestHandler(SimpleXMLRPCRequestHandler):
        rpc_paths = ('/RPC2',)

    # Create a class that combines ThreadingMixIn and SimpleXMLRPCServer
    class ThreadedXMLRPCServer(ThreadingMixIn, SimpleXMLRPCServer):
        pass
    server = ThreadedXMLRPCServer(("0.0.0.0", port), requestHandler=RequestHandler)
    class Dispatcher:
        def __init__(self, classes):
            self.classes = classes
        def execute(self, command, params):
            # do it as separate thread 
            print("Executing %s with params %s" % (command , params))
            result = None
            try:
                result = execute_command(self.classes, command, params)
            except Exception as e:
                print("Error: %s" % e)
                print(traceback.format_exc())
                raise e 
            print("Result: %s" % result)
            if isinstance(result, Path):
                return str(result)
            else:
                return result
    server.register_instance(Dispatcher(classes))
    server.serve_forever()