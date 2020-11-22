import socket
import sys
import json
import struct
import os
import pathlib

BUFFER_SIZE = 1024
HOST_NAME = 'localhost'
CONTROL_PORT = 2002
DATA_PORT = 2003
FAIL_MESSAGE = "FAIL"
DIRECTORY_NOT_FOUND = "Directory not found"
FILE_NOT_FOUND = "File not found"
FIN_MESSAGE = "FIN"
TRANSMISSION_FAIL = 'Result transmission failed. Terminating.'

arguments = sys.argv
HOST_NAME = arguments[1]
CONTROL_PORT = int(arguments[2])
DATA_PORT = int(arguments[3])


def list_files(words):
    # udp for data
    client_data_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # tcp for control
    client_control_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_control_conn.connect((HOST_NAME, CONTROL_PORT))
    client_control_conn.send(json.dumps(words).encode())

    # should receive server ready here
    client_control_conn.recv(BUFFER_SIZE)

    client_data_conn.sendto(json.dumps("ready").encode(), (HOST_NAME, DATA_PORT))
    response, server_addr = client_data_conn.recvfrom(BUFFER_SIZE)
    response = json.loads(response.decode())
    if response == FAIL_MESSAGE:
        print(DIRECTORY_NOT_FOUND)
        client_control_conn.close()
        client_data_conn.close()
        return
    # else:
    #     client_control_conn.send(json.dumps("start").encode())
    length = struct.unpack("i", client_data_conn.recv(4))[0]
    listing = []
    for i in range(length):
        chunk, addr = client_data_conn.recvfrom(BUFFER_SIZE)
        chunk = json.loads(chunk.decode())
        listing.append(chunk)
        client_data_conn.sendto(json.dumps("ack").encode(), (HOST_NAME, DATA_PORT))

    # send the FIN message
    client_data_conn.sendto(struct.pack("i", len(listing)), (HOST_NAME, DATA_PORT))
    for chunk in listing:
        print(chunk)
    client_control_conn.close()
    client_data_conn.close()


def change_directory(words):
    # udp for data
    client_data_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # tcp for control
    client_control_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_control_conn.connect((HOST_NAME, CONTROL_PORT))
    client_control_conn.send(json.dumps(words).encode())

    # should receive 'server ready' here
    client_control_conn.recv(BUFFER_SIZE)

    client_data_conn.sendto(json.dumps("ready").encode(), (HOST_NAME, DATA_PORT))
    response, server_addr = client_data_conn.recvfrom(BUFFER_SIZE)
    response = json.loads(response.decode())
    if response == FAIL_MESSAGE:
        print(DIRECTORY_NOT_FOUND)
        client_control_conn.close()
        client_data_conn.close()
        return
    else:
        print("Successfully change the directory at the server side")
        print("New direcotry:" + words[1])
        fin = struct.unpack("i", client_data_conn.recv(4))[0]
    client_control_conn.close()
    client_data_conn.close()


def get_file(words):
    # udp for data
    client_data_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_control_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_control_conn.connect((HOST_NAME, CONTROL_PORT))
    client_control_conn.send(json.dumps(words).encode())

    # should receive 'server ready here'
    client_control_conn.recv(BUFFER_SIZE)

    client_data_conn.sendto(json.dumps("ready").encode(), (HOST_NAME, DATA_PORT))
    response, server_addr = client_data_conn.recvfrom(BUFFER_SIZE)
    response = json.loads(response.decode())
    if response == FAIL_MESSAGE:
        print(FILE_NOT_FOUND)
        client_control_conn.close()
        client_data_conn.close()
        return
    dirs = words[1].split("/")
    filepath = os.path.join(os.getcwd(), dirs[len(dirs) - 1])
    file = open(filepath, 'wb')
    file_size = struct.unpack("i", client_data_conn.recv(4))[0]
    received_size = 0
    try:
        while received_size < file_size:
            client_data_conn.settimeout(10)
            line, addr = client_data_conn.recvfrom(BUFFER_SIZE)
            received_size += BUFFER_SIZE
            file.write(line)
            client_data_conn.sendto(json.dumps("ack").encode(), (HOST_NAME, DATA_PORT))
    except socket.timeout as e:
        print("Failed to send data to server. Terminating.")
        os.unlink(file.name)
    # send the FIN message
    client_data_conn.sendto(json.dumps("fin").encode(), (HOST_NAME, DATA_PORT))
    print("file received")
    print(file.name)
    client_control_conn.close()
    client_data_conn.close()
    file.close()


def put_file(words):
    p = pathlib.Path(words[1])
    if p.is_file():
        print("Sending file...")
    else:
        print(FILE_NOT_FOUND)
        return
    # udp for data
    client_data_conn = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_control_conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_control_conn.connect((HOST_NAME, CONTROL_PORT))
    client_control_conn.send(json.dumps(words).encode())

    client_control_conn.recv(BUFFER_SIZE)

    client_data_conn.sendto(json.dumps("ready").encode(), (HOST_NAME, DATA_PORT))
    file = open(words[1], "rb")
    size_of_file = os.path.getsize(words[1])
    client_data_conn.sendto(struct.pack("i", size_of_file), (HOST_NAME, DATA_PORT))
    line = file.read(BUFFER_SIZE)
    size = 0
    file_sent = False
    count = 0
    while not file_sent and count < 3:
        try:
            while line:
                client_data_conn.sendto(line, (HOST_NAME, DATA_PORT))
                client_data_conn.settimeout(1)
                size += BUFFER_SIZE
                line = file.read(BUFFER_SIZE)
                client_data_conn.recv(BUFFER_SIZE)
            file_sent = True
            message, addr = client_data_conn.recvfrom(BUFFER_SIZE)
            if json.loads(message.decode()) != 'fin':
                print('something wrong, data missing')
            else:
                print('File sent to client')
        except socket.timeout as e:
            count += 1
    if count == 3:
        print(TRANSMISSION_FAIL)
    client_control_conn.close()
    client_data_conn.close()
    file.close()
    return


while True:
    try:
        prompt = input("\nEnter a command: ")
        words = prompt.split(" ")
        if len(words) < 2:
            print('Invalid input')
        elif words[0].upper() == "LS":
            list_files(words)
        elif words[0].upper() == 'CD':
            change_directory(words)
        elif words[0].upper() == 'GET':
            get_file(words)
        elif words[0].upper() == 'PUT':
            put_file(words)
        elif words[0].upper() == 'QUIT':
            quit()
        else:
            print('Invalid input')
    except KeyboardInterrupt as e:
        print(e)
        quit()
