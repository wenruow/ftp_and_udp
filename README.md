##Welcome to FTP implemented by TCP/UDP
This is a ftp implemented by both TCP and UDP in python 3.8, using socket module. Any type of file can be transferred using this.
All modules used in this project are included in standard python library.

###Usage
To run the ftp server and client, run the following commands in your terminal.

To start the server:
```
$python server_tcp.py <control_port> <data_port>
```

To start the client:
```
$python client_tcp.py <server_address> <control_port> <data_port>
```
It's the same for UDP version. Just replace 'tcp' with 'udp'.
After successfully starting server and client, you can use the following commands:

```$ls <full_path_in_server>```

'LS' command will list all files and directories in the full path specified in the server side.

```
$get <full_path_of_file_in_server>
```
'GET' command will transfer file from server to client, where you run this command.

```$cd <full_path_in_server>```

'CD' command will change specific current directory in the server side.
This will be useful is you want to put file in client side to specific directory in server side.

```$put <full_path_of_file_in_client>```

'PUT' command basically puts client-side files to server-side.
If you want to put file, /full/path/your_file.ext to a directory, eg, /foo/bar, you can run the following commands:
```
$cd /foo/bar
$put /full/path/your_file.ext
```

If you type anything else in command, you will get `'invalid input'`.


###Explanation of Implementation
In a FTP application, there should be two connections between server and client-control connection and data connection.
Control connection will be used to pass commands. Data connection will handle all other communication between server and client.

####TCP
#####Connection
TCP implementation creates control and data connections both by TCP connection like the following.
```python
control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```
I would assume a ftp server needs to handle several clients, so for each of the clients, I'm creating a new thread.
```python
def on_new_client():

threading.Thread(target=on_new_client,
                         args=(control_conn, data_conn)
                         ).start()
```

#####Validation
I'm using pathlib to verify whether the file or directory specified in command is a valid one or not.
I was using os.path.isfile() and os.path.isDir() and it worked fine in my Macbook pro.
However, when I uploaded and deployed my application to a debian machine, something went wrong.
The debian machine has python 3.5.

What happened was os.path.isDir() could only check child directories of the current directory.
Let's take an example.

I have `home` as my home directory, and there are two sub-directories inside it, `New_York` and `Mass`.
In `New_York`, there's another sub-directory, `New_York/Albany`.
Assume I'm using os.path.isDir() to validate a directory. And I'm running the following commands in client side.
```
$cd /home/New_York
Current directory changes.
```
It's working fine.
Then I will run:
```
$cd /home/New_York/Albany
Current directory changes.
```
Still fine. It shows now i'm in `/home/New_York/Albany` directory.
Next if i run:
```
$cd /home/Mass
Directory not found
```
You see now I'm told /home/Mass is not found.

**Please note this is only happening in VM of my course. Mac doesn't have this issue.**

I resolved this issue by switch to `pathlib.Path`.

#####Data Transfer
In TCP implementation uses very reliable communication. Everytime server sends some data to the client, it must receive some response/ack to send the next chunk of data.
It's the same when running `put` command, client trie to send data to server.

As socket only sends and receives data in bytes, I'm using json to transfer str to byte & byte to str.

_Chunk and BUFFER_SIZE_

To be able to send/receive large set of data, we have to separate big file to small chunks.
Before starting to transfer data, the sender has to first send the overall number of chunks to the receiver, then the receiver can tell if it has the complete data by calculating received_size and total_size.

The reason we need a standard BUFFER_SIZE is hence obvious, we need to know the largest size of each chunk so that send and receiver can keep synchronized.


####UDP
#####Connection
The implementation in UDP would need help from TCP. The control connection will be a tcp connection but data connection will be a UDP one.

It is one of the biggest difference between two implementations that two connections will be always valid between server and client in TCP implementation.
However in UDP implementation, once receiving a new command, the application creates two new connections, and destroys them after finishing one command.

```python
        client_control_conn.close()
        client_data_conn.close()
```

#####Data Transfer
A stop-and-wait model is implemented here.

First, sender will compute the size of the file it has to send and then will transmit a "length" message to the receiver indicating the amount of data it should expect. The sender will then send the file (in multiple chunks if necessary) waiting for up to 1 second to receive an ACK for each message sent, before sending the next one. Similar to the receiver, the sender will retry sending a single message up to three times before giving up. If the sender did not receive an ACK after three attempts, it should display the error text on the sender console and exit.

The receiver should keep track of the number of bytes received. Once the receiver has received all expected data it should send a FIN packet to the sender.

If the file transfer fails, `os.unlink()` will remove the trash(incomplete file).

###References
Thanks to the following amazing projects and videos.
- [ftp-socket-server-python by Edward Renshaw](https://github.com/E-Renshaw/ftp-socket-server-python)
- [Sockets Tutorial with Python 3 part 1 - sending and receiving data](https://www.youtube.com/watch?v=Lbfe3-v7yE0&t=682s)


