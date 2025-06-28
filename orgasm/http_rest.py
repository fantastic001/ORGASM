
from orgasm import get_available_commands, get_command_specs, execute_command

from flask import Flask, jsonify, request

def serve_rest_api(classes, port=5000):
    app = Flask(__name__)

    @app.route('/commands', methods=['GET'])
    def command_specs():
        specs = get_command_specs(classes)
        for spec in specs:
            for arg in spec['args']:
                if 'type' in arg:
                    if isinstance(arg['type'], tuple):
                        arg['type'] = arg['type'][0].__name__
                    else:
                        arg['type'] = arg['type'].__name__
                if 'help' in arg:
                    if isinstance(arg['help'], tuple):
                        arg['help'] = arg['help'][1]
        return jsonify(specs)

    @app.route('/execute/<command>', methods=['POST'])
    def _execute_command(command):
        if command not in get_available_commands(classes):
            return jsonify({"error": "Command not found"}), 404
        
        A = request.json or {}
        try:
            result = execute_command(classes, command, **A)
            return jsonify(result)
        except Exception as e:
            return jsonify({"error": str(e)}), 400

    for spec in get_command_specs(classes):
        # create endpoint for particular command
        method = "GET" if len(spec["args"]) == 0 else "POST"        
        def command_endpoint(command=spec["method_name"]):
            print(f"Executing command: {command}")
            if request.method in ["GET", "DELETE"]:
                A = request.args.to_dict()
            else:
                A = request.json or {}
            try:
                result = execute_command(classes, command, A)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        print(f"Adding endpoint: {spec['method_name']} with method {method}")
        app.add_url_rule(f'/{spec["method_name"]}', spec["method_name"], command_endpoint, methods=[method])

    app.run(port=port)