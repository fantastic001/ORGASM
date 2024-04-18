from command_executor import command_executor_main
from pathlib import Path

class Commands:
    VALID_VALUES = {
        "test_status": {
            "status": [0,1,2]
        }
    }

    def test(self):
        return "This is test" 
    def test_path(self, path: Path):
        return path.name
    
    def test_status(self, *, status: int=0):
        return status

command_executor_main(Commands)
