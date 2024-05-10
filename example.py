from command_executor import command_executor_main, get_classes
from command_executor.web import serve_web
# command_executor_main(get_classes("example_commands"))
serve_web(get_classes("example_commands"))