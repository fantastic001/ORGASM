import http
from pathlib import Path
from orgasm import attr, tag 

from orgasm.http_rest import http_get, json_save_to_db, no_http
from orgasm.http_rest import http_auth_json_file, issue_token


COMMAND_CLASSES = ["Commands", "Commands2", "Commands3"]

class Commands:
    VALID_VALUES = {
        "test_status": {
            "status": lambda: [0, 1, 2, 3, 4, 5],
            "status2": [1,2]
        }
    }

    @attr(myattr=5)
    @tag("haha")
    @no_http
    def test(self):
        return "This is test" 
    
    def show_list(self):
        return ["item1", "item2", "item3"]
    def show_table(self):
        return [{"col1": "value1", "col2": "value2"}, {"col1": "value3", "col2": "value4"}]
    @http_get
    def test_path(self, path: Path, *, full_path: bool=False):
        if full_path:
            return path.resolve()
        else:
            return path.name
    
    @tag("status")
    def test_status(self, *, status: int=0, status2: int=1):
        return status


class Commands2:
    TOKENS_PATH = "tokens.json"

    @http_auth_json_file(TOKENS_PATH, user_arg="user")
    @http_get
    def test2(self, user: str):
        return "This is test2 for user: " + user
    
    def generate_token(self, user_id: str):
        return issue_token(user_id, json_save_to_db(self.TOKENS_PATH))
    



class Commands3:
    def test3(self):
        return "This is test3"
    
    def sum(self, a: int, b: int, *, c: int=0):
        return a + b + c
    
    def mul(self, a_1: int, a_2: int, *, k1: int=1, k2: int=1):
        return a_1 * a_2 * k1 * k2
        
    @tag("test4")
    def test4(self):
        return "This is test4"
    
    def test5(self):
        return self.test4() + " and " + self.test3()
