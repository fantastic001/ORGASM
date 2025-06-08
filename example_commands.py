from pathlib import Path

COMMAND_CLASSES = ["Commands", "Commands2", "Commands3"]

class Commands:
    VALID_VALUES = {
        "test_status": {
            "status": [0,1,2]
        }
    }

    def test(self):
        return "This is test" 
    def test_path(self, path: Path, *, full_path: bool=False):
        if full_path:
            return path.resolve()
        else:
            return path.name
    
    def test_status(self, *, status: int=0):
        return status


class Commands2:
    def test2(self):
        return "This is test2"


class Commands3:
    def test3(self):
        return "This is test3"
    
    def sum(self, a: int, b: int, *, c: int=0):
        return a + b + c
    
    def mul(self, a_1: int, a_2: int, *, k1: int=1, k2: int=1):
        return a_1 * a_2 * k1 * k2
