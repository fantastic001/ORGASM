
#!/usr/bin/env python
from pathlib import Path
import re
import sqlite3
import sys
from typing import Iterable

from pygments.lexers.shell import BashLexer

from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, CompleteEvent
from prompt_toolkit.document import Document
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.styles import Style

from orgasm import get_command_specs, execute_command

class CommandCompleter(Completer):

    def __init__(
        self,
        spec
    ) -> None:
        self.spec = spec 

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> Iterable[Completion]:
        # Get list of words.
        spec = self.spec
        first_word_in_line = document.text.split()[0] if document.text else ""
        cursor_position = document.cursor_position
        chars_before_space = document.text_before_cursor.rfind(" ")
        chars_before_equals = document.text_before_cursor.rfind("=")
        current_word = ""
        quotes_num = document.text_before_cursor.count('"') + document.text_before_cursor.count("'")
        displacement_after_space = len(document.text_before_cursor) - chars_before_space - 1
        displacement_after_equals = len(document.text_before_cursor) - chars_before_equals - 1
        if chars_before_space != -1:
            # If there is a space before the cursor, we take the word after the last space.
            current_word = document.text_before_cursor[chars_before_space + 1:]
        else:
            # If there is no space, we take the whole text before the cursor.
            current_word = document.text_before_cursor
        if first_word_in_line == "" or cursor_position <= len(first_word_in_line):
            result =  [c["name"] for c in spec if first_word_in_line in c["name"]]
            return [Completion(text, start_position=-len(document.text_before_cursor)) for text in result]
        else:
            # Find the command spec that matches the first word.
            for command in spec:
                if command["name"] == first_word_in_line:
                    # collect all arguments already inputed
                    existing_args = [] 
                    for part in document.text.split():
                        if part.startswith(first_word_in_line):
                            continue
                        if "=" in part and re.match(r"^[a-zA-Z0-9_]+$", part.split("=")[0]):
                            # we only add the argument name, not the value
                            existing_args.append(part.split("=")[0])
                    # now check if we started inputing arguments
                    # this means our cursor is not at first word and 
                    # there is a space before the cursor
                    if (document.text_before_cursor.endswith(" ") or "=" not in current_word) and quotes_num % 2 == 0:
                        # we autocomplete available arguments 
                        result =  [arg["name"] for arg in command.get("args", []) if arg["name"].startswith(current_word)]
                        result = [text for text in result if text not in existing_args]
                        return [Completion(text+"=", start_position=-displacement_after_space) for text in result]
                    elif document.text_before_cursor.endswith("="):
                        # find the argument we are completing
                        arg_name = document.text_before_cursor.split()[-1][:-1]
                        for arg in command.get("args", []):
                            if arg["name"] == arg_name:
                                # if the argument has valid values, we complete them
                                if "valid_values" in arg and arg["valid_values"] is not None:
                                    if callable(arg["valid_values"]):
                                        valid_values = arg["valid_values"]()
                                    else:
                                        valid_values = arg["valid_values"]
                                    return [Completion(str(value), start_position=displacement_after_equals) for value in valid_values]
                                else:
                                    # check type of argument
                                    if arg.get("type") == bool:
                                        # if it's a boolean, we complete with true and false
                                        return [Completion("true"),
                                                Completion("false")]
                                    else:
                                        return [] 
        # If no command matches, return an empty list.
        return []

style = Style.from_dict(
    {
        "completion-menu.completion": "bg:#008888 #ffffff",
        "completion-menu.completion.current": "bg:#00aaaa #000000",
        "scrollbar.background": "bg:#88aaaa",
        "scrollbar.button": "bg:#222222",
    }
)


def launch_repl(classes):
    specs = get_command_specs(classes)
    session = PromptSession(
        lexer=PygmentsLexer(BashLexer), completer=CommandCompleter(specs), style=style
    )

    while True:
        try:
            text = session.prompt("> ")
            if text.strip() == "":
                continue  # Skip empty input
            # Split the input into command and arguments
            # format is:
            # command arg1=value1 arg2=value2 ...
            # We assume the first word is the command and the rest are arguments
            # values can be quoted with single or double quotes and can contain spaces
            parts = text.split()
            command = parts[0]
            # if we have this: arg="value with spaces" we need to handle it correctly
            args = [] 
            quoted_part_start = None
            for i, part in enumerate(parts[1:]):
                if part.split("=")[-1].startswith('"'):
                    if quoted_part_start is None:
                        quoted_part_start = i + 1
                    # if we are in a quoted part, we continue to the next part
                if part.endswith('"') and quoted_part_start is not None:
                    # if it ends with a quote, we can add it to args
                    args.append(" ".join(parts[quoted_part_start:i + 2]))
                    quoted_part_start = None
                elif quoted_part_start is None:
                    # if we are not in a quoted part, we can add the part as is
                    args.append(part)
                
            command = command.strip()
            args = [arg.strip() for arg in args if arg.strip()]
            if command not in [c["name"] for c in specs]:
                print(f"Unknown command: {command}")
                continue  # Skip unknown commands
            command_spec = next(c for c in specs if c["name"] == command)
            # Prepare arguments for execution
            kwargs = {}
            for arg in args:
                if "=" in arg:
                    key, value = arg.split("=", 1)
                    kwargs[key] = value
                else:
                    print(f"Invalid argument format: {arg}")
                    continue
            for arg in command_spec.get("args", []):
                if arg["name"] not in kwargs and "default" in arg:
                    kwargs[arg["name"]] = arg["default"]
                    continue  # If the argument is not provided, use the default value
                if arg["name"] not in kwargs:
                    print(f"Missing required argument: {arg['name']}")
                    continue
                # cast the argument to the specified type if it exists
                if "type" in arg:
                    if arg["type"] == bool:
                        kwargs[arg["name"]] = kwargs[arg["name"]].lower() in ["true", "1", "yes"]
                    elif arg["type"] == int:
                        try:
                            kwargs[arg["name"]] = int(kwargs[arg["name"]])
                        except ValueError:
                            print(f"Invalid integer value for {arg['name']}: {kwargs[arg['name']]}")
                            continue
                    elif arg["type"] == float:
                        try:
                            kwargs[arg["name"]] = float(kwargs[arg["name"]])
                        except ValueError:
                            print(f"Invalid float value for {arg['name']}: {kwargs[arg['name']]}")
                            continue
                    elif arg["type"] == str:
                        if kwargs[arg["name"]].startswith('"') and kwargs[arg["name"]].endswith('"'):
                            kwargs[arg["name"]] = kwargs[arg["name"]][1:-1]
                        elif kwargs[arg["name"]].startswith("'") and kwargs[arg["name"]].endswith("'"):
                            kwargs[arg["name"]] = kwargs[arg["name"]][1:-1]
                        else:
                            # If it's not quoted, we assume it's a string but don't change it
                            pass
                    elif arg["type"] == Path:
                        if kwargs[arg["name"]].startswith('"') and kwargs[arg["name"]].endswith('"'):
                            kwargs[arg["name"]] = Path(kwargs[arg["name"]][1:-1])
                        elif kwargs[arg["name"]].startswith("'") and kwargs[arg["name"]].endswith("'"):
                            kwargs[arg["name"]] = Path(kwargs[arg["name"]][1:-1])
                        else:
                            kwargs[arg["name"]] = Path(kwargs[arg["name"]])
                    else:
                        kwargs[arg["name"]] = arg["type"](kwargs[arg["name"]])
            # Execute the command
            try:
                result = execute_command(classes, command, kwargs)
                if result is not None:
                    print(result)
            except Exception as e:
                print(str(e))
        except KeyboardInterrupt:
            continue  # Control-C pressed. Try again.
        except EOFError:
            break  # Control-D pressed.



