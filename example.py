from orgasm import command_executor_main, get_classes, command_executor_rpc, get_command_specs
from orgasm.web import serve_web
from orgasm.http_rest import serve_rest_api
from json import dumps
# command_executor_main(get_classes("example_commands"), explicit_params=False)
serve_rest_api(get_classes("example_commands"), port=5000)
# serve_web(get_classes("example_commands"))
# command_executor_rpc(get_classes("example_commands"))

serializer = lambda x: x if not isinstance(x, type) else x.__name__
print(dumps(get_command_specs(get_classes("example_commands")), indent=2, default=serializer))