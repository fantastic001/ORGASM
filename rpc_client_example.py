from xmlrpc import client

client = client.ServerProxy('http://localhost:8000')

print(client.execute("test_path", {"path": "/etc/hosts", "full_path": True}))