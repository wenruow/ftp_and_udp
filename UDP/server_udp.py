import socket
import sys
import json
import os
import struct
import pathlib

print("\nWelcome to UDP server from ICSI 416\n")

HOST_NAME = 'localhost'
CONTROL_PORT = 2002
DATA_PORT = 2003
FAIL_MESSAGE = "FAIL"
GOOD_MESSAGE = "Ready"
TRANSMISSION_FAIL = 'Result transmission failed. Terminating.'
BUFFER_SIZE = 1024

arguments = sys.argv
CONTROL_PORT = int(arguments[1])
DATA_PORT = int(arguments[2])

# The implementation in UDP would need help from TCP.
# The control connection will be a tcp connection but data connection will be a UDP one.
#
# It is one of the biggest difference between two implementations
# that two connections will be always valid between server and client in TCP implementation.
# However in UDP implementation, once receiving a new command,
# the application creates two new connections, and destroys them after finishing one command.

# TCP for control
control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
control_socket.bind((HOST_NAME, CONTROL_PORT))
control_socket.listen(5)

current_directory = os.curdir


def get_list(command, control_conn, client_data_addr):
    print('start getting list...')
    p = pathlib.Path(command[1])
    if p.is_dir():
        data_socket.sendto(json.dumps(GOOD_MESSAGE).encode(), client_data_addr)
    else:
        data_socket.sendto(json.dumps(FAIL_MESSAGE).encode(), client_data_addr)
        control_conn.close()
        data_socket.close()
        return
    listing = os.listdir(command[1])
    data_socket.sendto(struct.pack("i", len(listing)),client_data_addr)
    count = 0
    list_sent = False
    while not list_sent and count < 3:
        try:
            for chunk in listing:
                data_socket.sendto(json.dumps(chunk).encode(), client_data_addr)
                data_socket.settimeout(1)
                ack, client_data_addr = data_socket.recvfrom(1024)
            list_sent = True
            length = struct.unpack("i", data_socket.recv(4))[0]
            if len(listing) != length:
                print('something wrong, data missing')
        except socket.timeout as e:
            count += 1
    if count == 3:
        print('get list' + TRANSMISSION_FAIL)
    control_conn.close()
    data_socket.close()
    return


def change_directory(command, control_conn, client_data_addr):
    p = pathlib.Path(command[1])
    if p.is_dir():
        data_socket.sendto(json.dumps(GOOD_MESSAGE).encode(), client_data_addr)
    else:
        data_socket.sendto(json.dumps(FAIL_MESSAGE).encode(), client_data_addr)
        data_socket.close()
        control_conn.close()
        return
    current_directory = command[1]
    data_socket.sendto(struct.pack("i", 1), client_data_addr)
    control_conn.close()
    data_socket.close()
    print("Current directory: " + current_directory)
    return current_directory


def get_file(command, control_conn, client_data_addr):
    p = pathlib.Path(command[1])
    if p.is_file():
        data_socket.sendto(json.dumps(GOOD_MESSAGE).encode(), client_data_addr)
    else:
        data_socket.sendto(json.dumps(FAIL_MESSAGE).encode(), client_data_addr)
        control_conn.close()
        data_socket.close()
        return
    file = open(command[1], "rb")
    size_of_file = os.path.getsize(command[1])
    data_socket.sendto(struct.pack("i", size_of_file), client_data_addr)
    line = file.read(BUFFER_SIZE)
    size = 0
    file_sent = False
    count = 0
    while not file_sent and count < 3:
        try:
            while line:
                data_socket.sendto(line, client_data_addr)
                data_socket.settimeout(1)
                size += BUFFER_SIZE
                line = file.read(BUFFER_SIZE)
                data_socket.recv(BUFFER_SIZE)
            file_sent = True
            message, addr = data_socket.recvfrom(BUFFER_SIZE)
            if json.loads(message.decode()) != 'fin':
                print('something wrong, data missing')
            else:
                print('File sent to client')
        except socket.timeout as e:
            count += 1
    if count == 3:
        print('get file ' + TRANSMISSION_FAIL)
    control_conn.close()
    data_socket.close()
    file.close()
    return


def put_file(command, control_conn, client_data_addr):
    dirs = command[1].split("/")
    filepath = os.path.join(current_directory, dirs[len(dirs) - 1])
    file = open(filepath, 'wb')
    size_of_file = struct.unpack("i", data_socket.recv(4))[0]
    received_size = 0
    try:
        while received_size < size_of_file:
            data_socket.settimeout(10)
            line, addr = data_socket.recvfrom(BUFFER_SIZE)
            received_size += BUFFER_SIZE
            file.write(line)
            if received_size < size_of_file:
                data_socket.sendto(json.dumps("ack").encode(), client_data_addr)
    except socket.timeout as e:
        print("Did Not Receive valid data from Client. Terminating.")
        os.unlink(file.name)
        control_conn.close()
        data_socket.close()
        file.close()
        return
    # send the FIN message
    data_socket.sendto(json.dumps("fin").encode(), client_data_addr)
    print("file received")
    print(file.name)
    data_socket.close()
    control_conn.close()
    file.close()


while True:
    try:
        control_conn, client_control_addr = control_socket.accept()
        print(str(client_control_addr)[0] + ' connected')
        data_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        data_socket.bind(('', DATA_PORT))
        command = json.loads(control_conn.recv(1024).decode())
        print(command)
        control_conn.send(json.dumps("server ready").encode())
        ready_message, client_data_addr = data_socket.recvfrom(1024)
        print(ready_message)
        if command[0].upper() == "LS":
            get_list(command, control_conn, client_data_addr)
        elif command[0].upper() == "CD":
            current_directory = change_directory(command, control_conn, client_data_addr)
        elif command[0].upper() == 'GET':
            get_file(command, control_conn, client_data_addr)
        elif command[0].upper() == 'PUT':
            put_file(command, control_conn, client_data_addr)
    except KeyboardInterrupt as e:
        print(e)
        data_socket.close()
        control_socket.close()
        quit()
    # data_socket.sendto(json.dumps("received").encode(),client_data_addr)
