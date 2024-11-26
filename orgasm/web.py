
from orgasm import execute_command, get_command_specs
from pathlib import Path

# Flask application serving the web interface
def serve_web(classes, command_view_templates: dict = None, index_template=None, command_result_templates=None):
    """
    classes: list of classes with command methods
    command_view_templates: 
        dict with template files for web interface. Keys represent respective commands. 
        Values are paths to template files.
        If command is not in the dict, default template will be used.
    index_template: path to index template file. If None, default template will be used.
    command_result_templates: dict with template files for command results. Keys represent respective commands.

    """
    from flask import Flask, render_template, request, jsonify, redirect, url_for, render_template_string

    app = Flask(__name__)

    @app.route('/')
    def index():
        commands = get_command_specs(classes)
        html = render_template_string('''
        <html>
            <head>
                <title>Command Executor</title>
            </head>
            <body>
                <h1>Command Executor</h1>
                <a href="/command_specs">Command Specs</a>
                <p>Available commands:</p>                      
                <ul>
                    {% for command in commands %}
                        <li><a href="/command/{{ command["name"] }}">{{ command["name"] }}</a></li>
                    {% endfor %}
                </ul>
            </body>
        </html>
        ''', commands=commands) if index_template is None else render_template(index_template, commands=commands)
        return html

    @app.route('/command', methods=['POST', 'GET'])
    def command():
        command = request.form['command'] if "command" not in request.args else request.args['command']
        params = {} 
        specs = get_command_specs(classes)
        command = next((c for c in specs if c['name'] == command), None)
        if command is None:
            return 'Command not found', 404
        print("Command: ", command['name'])
        print("Args: ", command['args'])
        print("Request form: ", request.form)
        if request.method == 'GET' and len(command['args']) > 0:
            return redirect(url_for('command_view', command=command['name']))
        for arg in command['args']:
            if arg['name'] in request.form and request.form[arg['name']] not in [None, ""]:
                params[arg['name']] = arg['type'](request.form[arg['name']])
            if arg["type"] == Path:
                from random import choice
                from string import ascii_lowercase, digits
                def random_string(n):
                    return ''.join(choice(ascii_lowercase + digits) for _ in range(n))
                # copy file to temporary directory in request form 
                file = request.files[arg['name']]
                local_file_path = f"/tmp/{file.filename}." + random_string(8)
                file.save(local_file_path)
                params[arg['name']] = Path(local_file_path)
        print("Params: ", params)
        result = execute_command(classes, command["name"], params)
        return render_template_string('''
        <html>
            <head>
                <title>Command Executor</title>
            </head>
            <body>
                <h1>Command Executor</h1>
                <p>{{ result }}</p>
            </body>
        </html>
        ''', result=result) if (
                command_result_templates is None or 
                command['name'] not in command_result_templates 
            ) else render_template(command_result_templates[command['name']], result=result)
    

    @app.route('/command_specs')
    def command_specs():
        specs = get_command_specs(classes)
        # custom serialization for type objects which converts them into string 
        def serialize(obj):
            if isinstance(obj, type):
                return obj.__name__
            if isinstance(obj, dict):
                return {k: serialize(v) for k, v in obj.items()}
            if isinstance(obj, list):
                return [serialize(v) for v in obj]
            return obj
        # create deep copy of specs dict which will transform every item tusing serialize func
        specs_serialized = serialize(specs)
        return jsonify(specs_serialized)

    @app.route('/command/<command>')
    def command_view(command):
        commands = get_command_specs(classes)
        command = next((c for c in commands if c['name'] == command), None)
        type_input_mapping = {
            int: 'number',
            str: 'text',
            bool: 'checkbox',
            float: 'number',
            Path: 'file'
        }
        if command is None:
            return 'Command not found', 404
        if len(command['args']) == 0:
            return redirect(url_for('command', command=command['name']))
        html = render_template_string('''
        <html>
            <head>
                <title>Command Executor</title>
            </head>
            <body>
                <h1>{{ command["name"] }}</h1>
                <p>{{ command["description"] }}</p>
                <form enctype="multipart/form-data" action="{{ url_for('command') }}" method="post">
                    <input type="hidden" name="command" value="{{ command["name"] }}">
                    {% for param in command["args"] %}
                        <label for="{{ param["name"] }}">{{ param["name"] }}</label>
                        {% if param["valid_values"] %}
                                      
                            <select name="{{ param["name"] }}">
                                {% for value in param["valid_values"] %}
                                    <option value="{{ value }}">{{ value }}</option>
                                {% endfor %}
                            </select>
                        {% else %}
                        <input type="{{ type_input_mapping[param["type"]] }}" name="{{ param["name"] }}">
                        {% endif %}
                    {% endfor %}
                    <input type="submit" value="Execute">
                </form>
            </body>
        </html>
        ''', 
            command=command, 
            type_input_mapping=type_input_mapping,
        ) if (
            command_view_templates is None or 
            command['name'] not in command_view_templates 
        ) else render_template(command_view_templates[command['name']], command=command, type_input_mapping=type_input_mapping)
        return html

    app.run(port=8080, debug=True)