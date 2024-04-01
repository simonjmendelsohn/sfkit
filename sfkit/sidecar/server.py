import json
import os
import select
import socket
import subprocess
from threading import Thread

from sfkit.sidecar.utils import get_sock_path


def handle_client(client: socket.socket):
    try:
        while True:
            data = client.recv(1024)
            if not data:
                break
            try:
                request = json.loads(data.decode("utf-8"))
            except json.JSONDecodeError:
                client.sendall("Invalid JSON format".encode("utf-8"))
                continue

            study_id = request.get("study_id", "")
            data_path = os.path.realpath(request.get("data_path", ""))
            
            if not data_path.startswith(constants.SAFE_DATA_PATH):
                client.sendall("Invalid data_path".encode("utf-8"))
                client.close()
                return

            client.sendall("Received request".encode("utf-8"))

            command = ["sfkit", "all"]
            if study_id:
                command.extend(["--study_id", study_id])
            command.extend(["--data_path", data_path])

            try:
                with subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    env=dict(os.environ, PYTHONUNBUFFERED="1"),
                    text=True,
                    bufsize=1,
                ) as process:
                    while True:
                        line = process.stdout.readline().strip()
                        if line:
                            client.sendall(line.encode("utf-8"))
                            print(line)
                        elif process.poll() is not None:
                            break
            except Exception as e:
                client.sendall(f"Error executing command: {str(e)}".encode("utf-8"))
    except Exception as e:
        client.sendall(f"Unexpected error: {str(e)}".encode("utf-8"))
    finally:
        client.close()


def server_command():
    sock_path = get_sock_path()
    if os.path.exists(sock_path):
        os.remove(sock_path)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(sock_path)
    server.listen(1)

    while True:
        client, _ = server.accept()
        handle_client(client)
