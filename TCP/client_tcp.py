import socket
import json
import os
import struct
import sys
import pathlib

HOST_NAME = 'localhost'
CONTROL_PORT = 2002
DATA_PORT = 2003
BUFFER_SIZE = 1024
FAIL_MESSAGE = "FAIL"
GOOD_MESSAGE = "Ready"
DIRECTORY_NOT_FOUND = "Directory not found"
FILE_NOT_FOUND = "File not found"

arguments = sys.argv
HOST_NAME = arguments[1]
CONTROL_PORT = int(arguments[2])
DATA_PORT = int(arguments[3])

client_control_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_control_conn.connect((HOST_NAME, CONTROL_PORT))

client_data_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_data_conn.connect((HOST_NAME, DATA_PORT))


print("control connection established")
print("data connection established")


def list_files(words):
    print("listing...")
    try:
        client_control_conn.send(json.dumps(words).encode())
    except Exception as e:
        print(e)
        return
    try:
        response = json.loads(client_data_conn.recv(BUFFER_SIZE).decode())
        if response == FAIL_MESSAGE:
            print(DIRECTORY_NOT_FOUND)
            return
        else:
            client_data_conn.send(json.dumps("start").encode())
        listing = []
        total_length = struct.unpack("i", client_data_conn.recv(4))[0]
        client_data_conn.send(json.dumps("1").encode())
        for i in range(total_length):
            file_name_size = struct.unpack("i", client_data_conn.recv(4))[0]
            response = client_data_conn.recv(file_name_size).decode()
            file_name = json.loads(response)
            print(file_name)
            client_data_conn.send(json.dumps("1").encode())
            # listing.append(response)
            # response = client_data_conn.recv(BUFFER_SIZE).decode()
        for line in listing:
            print(line)
    except Exception as e:
        print(e)
        return


def change_directory(words):
    print("Changing directory...")
    try:
        client_control_conn.send(json.dumps(words).encode())
    except Exception as e:
        print(e)
        return
    try:
        response = json.loads(client_data_conn.recv(BUFFER_SIZE).decode())
    except Exception as e:
        print(e)
        return
    if response == "200":
        print("Current directory: \n")
        print(words[1])
    else:
        print(DIRECTORY_NOT_FOUND)


def put_file(words):
    p = pathlib.Path(words[1])
    if not p.is_file():
        print(FILE_NOT_FOUND)
        return
    print("Putting file...")
    client_control_conn.send(json.dumps(words).encode())
    file = open(words[1], "rb")
    size = os.path.getsize(words[1])
    client_data_conn.send(struct.pack("i", size))
    client_data_conn.recv(BUFFER_SIZE)
    line = file.read(BUFFER_SIZE)
    size = 0
    while line:
        client_data_conn.send(line)
        size += BUFFER_SIZE
        line = file.read(BUFFER_SIZE)
        client_data_conn.recv(BUFFER_SIZE)
    file.close()


def get_file(words):
    print("Getting file...")
    client_control_conn.send(json.dumps(words).encode())
    response = json.loads(client_data_conn.recv(BUFFER_SIZE).decode())
    if response == FAIL_MESSAGE:
        print(FILE_NOT_FOUND)
        return
    else:
        client_data_conn.send(json.dumps("start").encode())
    dirs = words[1].split("/")
    filepath = os.path.join(os.getcwd(), dirs[len(dirs) - 1])
    file = open(filepath, 'wb')
    file_size = struct.unpack("i", client_data_conn.recv(4))[0]
    client_data_conn.send(json.dumps("1").encode())
    received_size = 0
    while received_size < file_size:
        line = client_data_conn.recv(BUFFER_SIZE)
        received_size += BUFFER_SIZE
        file.write(line)
        client_data_conn.send(json.dumps("1").encode())
    print("file received")
    file.close()


while True:
    try:
        prompt = input("\nEnter a command: ")
        if prompt[:4].upper() == "QUIT":
            client_control_conn.close()
            client_data_conn.close()
            quit()
        words = prompt.split(" ")
        if len(words) < 2:
            print('Invalid input')
        elif words[0].upper() == "LS":
            list_files(words)
        elif words[0].upper() == 'CD':
            change_directory(words)
        elif words[0].upper() == 'PUT':
            put_file(words)
        elif words[0].upper() == 'GET':
            get_file(words)
        else:
            print('Invalid input')
    except KeyboardInterrupt as e:
        quit()