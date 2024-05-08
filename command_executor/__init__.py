import argparse
from pathlib import Path
import sys
from typing import Dict 
import inspect 
from command_executor.command_class_inspector import * 


def command_executor_main(classes):
    if not isinstance(classes, list):
        classes = [classes]
    parser = argparse.ArgumentParser()
    available_commands = []
    for cls in classes:
        available_commands += get_available_commands(cls)
    command_parsers = parser.add_subparsers(dest="command")

    commands: Dict[str, argparse.ArgumentParser] = {}
    for command in available_commands:
        commands[command] = command_parsers.add_parser(command)

        for cls in classes:
            if hasattr(cls, command):
                for arg in get_arguments(getattr(cls, command)):
                    commands[command].add_argument("--%s" % (arg.replace("_", "-")), 
                        required=True, 
                        action="store", 
                        type=get_arg_type(getattr(cls, command), arg),
                        help=get_arg_description(getattr(cls, command), arg)
                    )
                for arg, value in get_optional_arguments(getattr(cls, command)):
                    if get_arg_type(getattr(cls, command), arg) == bool:
                            commands[command].add_argument("--%s" % (arg.replace("_", "-")), 
                            default=value,
                            action="store_const",
                            const=True,
                            help=get_arg_description(getattr(cls, command), arg)
                        )
                    else:
                        commands[command].add_argument("--%s" % (arg.replace("_", "-")), 
                            default=value,
                            action="store",
                            type=get_arg_type(getattr(cls, command), arg),
                            help=get_arg_description(getattr(cls, command), arg)
                        )
    args, _ = parser.parse_known_args()
    for cls in classes:
        executor = cls()
        if hasattr(executor, args.command):
            m = getattr(executor, args.command)
            A = {}
            for arg in get_arguments(m):
                if arg != "self":
                    A[arg] = getattr(args, arg)
                # if arg is type PathLike then check if path exists
                if get_arg_type(m, arg) == Path:
                    if not Path(A[arg]).exists():
                        print("Path %s does not exist" % A[arg])
                        sys.exit(1)
            for arg, _ in get_optional_arguments(m):
                A[arg] = getattr(args, arg)
                # if arg is type PathLike then check if path exists
                if get_arg_type(m, arg) == Path:
                    if not Path(A[arg]).exists():
                        print("Path %s does not exist" % A[arg])
                        sys.exit(1)
                if hasattr(executor, "VALID_VALUES") and getattr(executor, "VALID_VALUES").get(command, {}).get(arg, None) is not None:
                    if A[arg] not in getattr(executor, "VALID_VALUES")[command][arg]:
                        print("Invalid value %s for argument %s" % (A[arg], arg))
                        print("Valid values are: %s" % ", ".join([ str(x) for x in getattr(executor, "VALID_VALUES")[command][arg]]))
                        sys.exit(1)
            result = m(**A)
            if isinstance(result, dict):
                # pretty print dict 
                for k,v in result.items():
                    print("%s: %s" % (k, v))
            elif result is not None:
                print(result)
            return
    print("This feature is not implemented yet")

def get_classes(module_name):
    module = __import__(module_name)
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