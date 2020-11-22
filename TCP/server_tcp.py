# References:
# https://github.com/E-Renshaw/ftp-socket-server-python
# I copied the way to use BUFFER from Renshaw
# https://www.youtube.com/watch?v=Lbfe3-v7yE0&t=682s
# I learned how to create socket and build connections from this video.
import socket
import os
import json
import threading
import struct
import sys
import pathlib

print("\nWelcome to FTP server from ICSI 416\n")
HOST_NAME = 'localhost'
CONTROL_PORT = 2002
DATA_PORT = 2003
BUFFER_SIZE = 1024
FAIL_MESSAGE = "FAIL"
GOOD_MESSAGE = "Ready"

arguments = sys.argv
CONTROL_PORT = int(arguments[1])
DATA_PORT = int(arguments[2])

# As socket only sends and receives data in bytes,
# I'm using json to transfer str to byte & byte to str.
# And using struct to transfer numbers to byte


def put_file(data, data_conn, current_dir):
    print("Server receiving file...", data[1])
    dirs = data[1].split("/")
    filepath = os.path.join(current_dir, dirs[len(dirs) - 1])
    file = open(filepath, 'wb')
    file_size = struct.unpack("i", data_conn.recv(4))[0]
    data_conn.send(json.dumps("1").encode())
    received_size = 0
    while received_size < file_size:
        line = data_conn.recv(BUFFER_SIZE)
        file.write(line)
        received_size += BUFFER_SIZE
        data_conn.send(json.dumps("1").encode())
    print("File received")
    file.close()


# In TCP implementation uses very reliable communication. Everytime server sends some data to the client,
# it must receive some response/ack to send the next chunk of data.
# It's the same when running `put` command, client trie to send data to server.
# receive large set of data, we have to separate big file to small chunks.
# Before starting to transfer data, the sender has to first send the overall
# number of chunks to the receiver, then the receiver can tell if
# it has the complete data by calculating received_size and total_size.
# The reason we need a standard BUFFER_SIZE is hence obvious,
# we need to know the largest size of each chunk so that send and receiver can keep synchronized.
def get_file(data, data_conn):
    # I'm using pathlib to verify whether the file or directory
    # specified in command is a valid one or not.
    p = pathlib.Path(data[1])
    if p.is_file():
        data_conn.send(json.dumps(GOOD_MESSAGE).encode())
    else:
        data_conn.send(json.dumps(FAIL_MESSAGE).encode())
        return
    data_conn.recv(BUFFER_SIZE)
    print("Server sending file...", data[1])
    file = open(data[1], "rb")
    size_of_file = os.path.getsize(data[1])
    data_conn.send(struct.pack("i", size_of_file))
    data_conn.recv(BUFFER_SIZE)
    line = file.read(BUFFER_SIZE)
    size = 0
    while line:
        data_conn.send(line)
        size += BUFFER_SIZE
        line = file.read(BUFFER_SIZE)
        data_conn.recv(BUFFER_SIZE)
    print('Done sending files...')
    file.close()


def get_list(data, data_conn):
    p = pathlib.Path(data[1])
    if p.is_dir():
        data_conn.send(json.dumps(GOOD_MESSAGE).encode())
    else:
        data_conn.send(json.dumps(FAIL_MESSAGE).encode())
        return
    data_conn.recv(BUFFER_SIZE)
    listing = os.listdir(data[1])
    data_conn.send(struct.pack("i", len(listing)))
    data_conn.recv(BUFFER_SIZE)
    for chunk in listing:
        data_conn.send(struct.pack("i", sys.getsizeof(chunk)))
        data_conn.send(json.dumps(chunk).encode())
        data_conn.recv(BUFFER_SIZE)


def change_directory(data, data_conn):
    p = pathlib.Path(data[1])
    # os.path doesn't work well in a debian machine
    # if os.path.isdir(data[1]):
    if p.is_dir():
        current_dir = data[1];
        print("Current directory: ")
        print(current_dir)
        data_conn.send(json.dumps("200").encode())
        return current_dir
    else:
        data_conn.send(json.dumps("400").encode())


# new thread for each client
def on_new_client(control_conn, data_conn):
    current_dir = os.getcwd()
    while True:
        command = control_conn.recv(BUFFER_SIZE)
        decoded_command = command.decode()
        data = json.loads(decoded_command)
        if data[0].upper() == "LS":
            get_list(data, data_conn)
        if data[0].upper() == "CD":
            current_dir = change_directory(data, data_conn)
        if data[0].upper() == 'PUT':
            put_file(data, data_conn,  current_dir)
        if data[0].upper() == 'GET':
            get_file(data, data_conn)

########
# In a FTP application, there should be two connections between server
# and client-control connection and data connection.
# Control connection will be used to pass commands.
# Data connection will handle all other communication between server and client.
########


# TCP implementation creates control and data connections both by TCP connection


control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
control_socket.bind((HOST_NAME, CONTROL_PORT))
control_socket.listen(5)

data_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
data_socket.bind((HOST_NAME, DATA_PORT))
data_socket.listen(5)


# I would assume a ftp server needs to handle several clients,
# so for each of the clients,
# I'm creating a new thread.
while True:
    try:
        control_conn, address = control_socket.accept()
        print("Control connection has been established!")
        data_conn, data_address = data_socket.accept()
        print("Data connection from has been established!")
        threading.Thread(target=on_new_client,
                         args=(control_conn, data_conn)
                         ).start()
    except KeyboardInterrupt as e:
        quit()