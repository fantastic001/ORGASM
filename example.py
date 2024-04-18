from command_executor import command_executor_main
from pathlib import Path

class Commands:
    def test(self):
        return "This is test" 
    def test_path(self, path: Path):
        return path.name

command_executor_main(Commands)
