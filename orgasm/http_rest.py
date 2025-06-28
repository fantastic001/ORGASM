
import http
from orgasm import get_available_commands, get_command_specs, execute_command
from orgasm import attr, tag 

from flask import Flask, jsonify, request

http_post = attr(http_method ="POST")
http_get = attr(http_method ="GET")
http_delete = attr(http_method ="DELETE")
http_put = attr(http_method ="PUT")
no_http = tag("no_http")

def serve_rest_api(classes, port=5000):
    app = Flask(__name__)

    @app.route('/commands', methods=['GET'])
    def command_specs():
        specs = get_command_specs(classes)
        for spec in specs:
            if "no_http" in spec['tags']:
                continue
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

    for spec in get_command_specs(classes):
        if "no_http" in spec['tags']:
            print(f"Skipping command {spec['method_name']} due to 'no_http' tag")
            continue
        # create endpoint for particular command
        method = "GET" if len(spec["args"]) == 0 else "POST"  
        if "http_method" in spec["attrs"]:
            method = spec["attrs"]["http_method"].upper()
            if method not in ["GET", "POST", "PUT", "DELETE"]:
                raise ValueError(f"Invalid HTTP method {method} for command {spec['method_name']}")      
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