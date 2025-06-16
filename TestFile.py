import subprocess
import time
import os

server_dir = "E:\HongKong\Final Project\\backend\server"
client_dir = "E:\HongKong\Final Project\\backend\client"

server_command = "python server.py"
client_command = "python client.py"

client_name = ["Alice", "Brodey", "Bob", "Charlie", "Eve", "Frank", "Grace", "Ash"]

def run_server():
    print("Starting server...")
    os.chdir(server_dir)
    subprocess.Popen(server_command)

def run_client(num_clients):
    print("Starting 8 clients...")
    for i in range(num_clients):
        print("Client is connected...")
        os.chdir(client_dir)
        client_process = subprocess.Popen(client_command, stdin=subprocess.PIPE, text=True)
        client_process.stdin.write(client_name + "\n")
        client_process.stdin.flush()
        time.sleep(1)

if __name__ == '__main__':
    run_server()
    time.sleep(2)
    run_client(8)
    print("All clients connected...")