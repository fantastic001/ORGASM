from typing import Callable
from orgasm import command_executor_main, get_classes, command_executor_rpc, get_command_specs
from orgasm.web import serve_web
from orgasm.http_rest import serve_rest_api
from json import dumps
# command_executor_main(get_classes("example_commands"), explicit_params=False)
serve_rest_api(get_classes("example_commands"), port=5000)
# serve_web(get_classes("example_commands"))
# command_executor_rpc(get_classes("example_commands"))


def serializer(x):
    if isinstance(x, type):
        return x.__name__
    elif isinstance(x, Callable):
        return x.__name__
    return str(x)
print(dumps(get_command_specs(get_classes("example_commands")), indent=2, default=serializer))
