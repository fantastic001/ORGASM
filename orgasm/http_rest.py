
from typing import Callable, Optional
from orgasm import get_available_commands, get_command_specs, execute_command
from orgasm import attr, tag 

from flask import Flask, jsonify, request
import secrets, base64, hashlib
from datetime import timedelta, datetime
import hmac, datetime as dt


def issue_token(user_id: str, save_to_db, expiration_days = 90) -> str:
    print(f"Issuing token for user {user_id} with expiration {expiration_days} days")
    raw = secrets.token_bytes(32)                # cryptographically secure RNG
    token = f"v1.{base64.urlsafe_b64encode(raw).rstrip(b'=').decode()}"
    # Store only a hash, never the raw token:
    digest = hashlib.sha256(token.encode()).hexdigest()
    save_to_db(user_id,
               digest,
               datetime.now(),
               datetime.now() + timedelta(days=expiration_days)) 
    return token

def validate_token(token: str, db_lookup: Callable) -> Optional[str]:
    # Reject wrong version up-front
    if not token.startswith("v1."):
        return None

    digest = hashlib.sha256(token.encode()).hexdigest()
    user, digest, expiration = db_lookup(digest)

    if not user:
        # No such token
        return None
    if expiration < dt.datetime.now():
        # Token expired
        return None
    
    return user

# assumes we store tokens in json file 

def json_save_to_db(path: str):
    import json
    from pathlib import Path

    def save_to_db(user_id: str, digest: str, issued: datetime, expiration: datetime):
        data = {}
        if Path(path).exists():
            with open(path, 'r') as f:
                data = json.load(f)
        data[digest] = {
            "user_id": user_id,
            "issued": issued.isoformat(),
            "expiration": expiration.isoformat()
        }
        with open(path, 'w') as f:
            json.dump(data, f)

    return save_to_db

def json_db_lookup(path: str):
    import json
    from pathlib import Path

    def db_lookup(digest: str):
        if not Path(path).exists():
            return None, None, None
        with open(path, 'r') as f:
            data = json.load(f)
        if digest not in data:
            return None, None, None
        entry = data[digest]
        user_id = entry["user_id"]
        issued = datetime.fromisoformat(entry["issued"])
        expiration = datetime.fromisoformat(entry["expiration"])
        return user_id, digest, expiration

    return db_lookup



http_post = attr(http_method ="POST")
http_get = attr(http_method ="GET")
http_delete = attr(http_method ="DELETE")
http_put = attr(http_method ="PUT")
no_http = tag("no_http")

def http_auth(db_save, db_lookup, user_arg=None):
    """
    Decorator to protect endpoints with token-based authentication.
    The token is expected to be passed in the 'Authorization' header in the format
    Authorization: Bearer <token>
    """
    return attr(
        http_authorization=True,
        http_auth_db_save=db_save,
        http_auth_db_lookup=db_lookup,
        http_auth_pass_user_id=user_arg if user_arg else None
    )

def http_auth_json_file(path: str, user_arg=None):
    """
    Convenience function to create a decorator for token-based authentication
    using a JSON file as the database.
    """
    db_save = json_save_to_db(path)
    db_lookup = json_db_lookup(path)
    return http_auth(db_save, db_lookup, user_arg)



def serve_rest_api(classes, port=5000, host="127.0.0.1"):
    app = Flask(__name__)

    @app.route('/commands', methods=['GET'])
    def command_specs():
        specs = get_command_specs(classes)
        for spec in specs:
            if "no_http" in spec['tags']:
                continue
            for attr, value in spec['attrs'].items():
                if isinstance(value, Callable):
                    spec['attrs'][attr] = value.__name__
                elif isinstance(value, type):
                    spec['attrs'][attr] = value.__name__
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
        def command_endpoint(command=spec["method_name"], spec=spec):
            print(f"Executing command: {command}")
            if "http_authorization" in spec["attrs"]:
                # Check for authorization
                auth_header = request.headers.get('Authorization')
                if not auth_header or not auth_header.startswith('Bearer '):
                    return jsonify({"error": "Unauthorized"}), 401
                token = auth_header.split(' ')[1]
                user_id = validate_token(token, spec["attrs"]["http_auth_db_lookup"])
                if not user_id:
                    return jsonify({"error": "Invalid or expired token"}), 401
                
            if request.method in ["GET", "DELETE"]:
                A = request.args.to_dict()
            else:
                A = request.json or {}
            if "http_auth_pass_user_id" in spec["attrs"] and spec["attrs"]["http_auth_pass_user_id"]:
                    A[spec["attrs"]["http_auth_pass_user_id"]] = user_id    
            try:
                result = execute_command(classes, command, A)
                return jsonify(result)
            except Exception as e:
                return jsonify({"error": str(e)}), 400
        print(f"Adding endpoint: {spec['method_name']} with method {method}")
        app.add_url_rule(f'/{spec["method_name"]}', spec["method_name"], command_endpoint, methods=[method])

    app.run(port=port, host=host)