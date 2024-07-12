import struct
import socket
import random
import os
import math
import threading
import time
import binascii
import keyboard


# Globals for both sides
KEEPALIVE = False
CLIENTCONNECTED = True
SWITCH = False

# Global sizes
HEADER = 8
BUFFER_SIZE = 1500 - 28 - HEADER*2

# Globals for simulations
TIMEOUT = 5
ERROR_PROBABILITY = 5

# Globals for frame handling
filename = ""
rec_mesg = []


# # --- DOIMPLEMENTACIA ---#
# def caesar_cipher(message):
#     ceasar_message = ""
#     for character in message:
#         if character.isalpha():
#             # Offset podla toho ci to je velke alebo male pismeno
#             offset = ord('A') if character.isupper() else ord('a')
#             # modulo 26 ak by sme prechadzali na koneic abecedy
#             ceasar_message += chr((ord(character) - offset + 5) % 26 + offset)
#         else:
#             ceasar_message += character
#     return ceasar_message
# # --- DOIMPLEMENTACIA ---#


# | * o - + ~ ¤  => Threads <= ~ + - * o * | #
# Keep alive
def keepAlive(client, server):
    global KEEPALIVE
    global TIMEOUT
    global CLIENTCONNECTED
    global SWITCH

    timeleft = 5
    while KEEPALIVE:

        # Send Keep Alive message
        message = constructMessage("1", "4", 0, 0, "".encode())

        try:
            client.sendto(message, server)
            # Timeout to recieve ACK
            client.settimeout(TIMEOUT)

            ack_message = client.recvfrom(BUFFER_SIZE)
            message_type, flags, current_length, seq_number, checksum, data = decodeMessage(ack_message[0])

            # Check if incoming message is Keep Alive
            if message_type == 1 and flags == 4:
                print("Keep alive CLIENT")

            # Switch from server
            if message_type == 5 and flags == 4:
                KEEPALIVE = False
                SWITCH = True
                print("Press enter to confirm switch to SERVER...")

            # Waint until next Keep alive is sent
            time.sleep(timeleft)

        except socket.timeout:
            print(f"Server not responding. Warning: {timeleft - 4}")
            timeleft += 1

        except Exception as e:
            print("Error: ", e)
            CLIENTCONNECTED = False
            KEEPALIVE = False
            client.close()
            return

    # If there is no response 3 times turn of
    if timeleft >= 8:
        CLIENTCONNECTED = False
        KEEPALIVE = False
        return


# | * o - + ~ ¤  => Frame (de)composition Functions <= ~ + - * o * | #
def format_1st_byte(message_type, flags):
    # Add leading zeros to the message type and flags
    mesasge_type = message_type.rjust(4, '0')
    flags = flags.rjust(4, '0')

    # Combine the message type and flags into one byte
    first_byte = int((mesasge_type + flags), 2).to_bytes(1, 'big')

    return first_byte


def constructMessage(message_type, flags, num_of_fragments, seq_number, data, error=False):
    header = struct.pack("!c3sH", format_1st_byte(bin(int(message_type))[2:], bin(int(flags))[2:]), num_of_fragments.to_bytes(3, 'big'), seq_number)

    # Calculate the checksum
    data_crc = binascii.crc_hqx(header+data, 0)

    # Simulate a corrupted message
    if error:
        data_crc = data_crc + 1

    # Add crc to header
    header_with_crc = header + struct.pack("!H", data_crc)

    message = header_with_crc + data

    return message


def decodeMessage(message):
    type_and_flags, num_of_fragments, seq_number, checksum = struct.unpack("!c3sHH", message[:HEADER])
    # Type and Flags
    flags = int(type_and_flags[0] & 0b00001111)
    message_type = (int(type_and_flags[0] & 0b11110000)) >> 4

    # Frag size and Data
    num_of_fragments = int.from_bytes(num_of_fragments, "big")
    data = message[HEADER:]

    return message_type, flags, num_of_fragments, seq_number, checksum, data


# | * o - + ~ ¤  => Server Functions <= ~ + - * o * | #
# Turn on switch
def turn_Swap_on():
    global SWITCH
    SWITCH = True


def startServer():
    global KEEPALIVE
    global TIMEOUT

    # Port
    print("Enter port or press enter to use a random port.")
    port = input("PORT: ")
    if port == "":
        port = 65001
    else:
        port = int(port)

    # Server socket
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server.bind((socket.gethostbyname(socket.gethostname()), port))
    print(f"Server is running on {socket.gethostbyname(socket.gethostname())}:{port}\n")

    while True:
        try:
            # TIMEOUT*2 seconds to connect
            server.settimeout(TIMEOUT*12)

            # Init message from client Type "1", Flags "0"
            message, client_address = server.recvfrom(BUFFER_SIZE)
            message_type, flags, current_length, seq_number, checksum, data = decodeMessage(message)

            if message_type == 1 and flags == 0:
                # ACK for Client
                message = constructMessage("1", "0", 0, 0, "".encode())
                server.sendto(message, client_address)

                print(f"{client_address} connected to the server.")
                # Go to server running ->
                runningServer(server, client_address)

        # If client does not connect in TIMEOUT*12 seconds
        except socket.timeout:
            print("Timeout. Exiting...")
            return

        # If client disconnects
        except ConnectionResetError:
            print("Connection failed. Exiting...")
            return

        except Exception as e:
            print("Error: ", e)
            return


def runningServer(server, client):
    global KEEPALIVE
    global HEADER
    global TIMEOUT
    global BUFFER_SIZE
    global SWITCH

    SERVER = True

    # Downloads folder
    directory = "server_downloads"
    os.makedirs(directory, exist_ok=True)

    downloads_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), directory)

    # Start a while loop to listen for messages
    while SERVER:
        # Recieve message
        try:
            server.settimeout(TIMEOUT*12)
            keyboard.add_hotkey('ctrl+s', turn_Swap_on)
            OK = True
            message, client = server.recvfrom(BUFFER_SIZE)
            # Unpack the message and get the data
            message_type, flags, num_of_fragments, seq, checksum, dat = decodeMessage(message)

            # Pack the header without the checksum
            header = struct.pack("!c3sH", format_1st_byte(bin(int(message_type))[2:], bin(int(flags))[2:]), num_of_fragments.to_bytes(3, 'big'), seq)

            # Checksum
            calculated_crc = binascii.crc_hqx(header + dat, 0)
            received_crc = checksum

            if received_crc != calculated_crc:
                if flags == 1:
                    ack = 1
                else:
                    ack = 0
                print("Checksums do not match")
                # Resend the message with an empty data field
                new_message = constructMessage(message_type, "3", 0, ack, "".encode())
                server.sendto(new_message, client)
                OK = False

            # Handle the message based on the message_type
            # Text
            if message_type == 2 and OK:
                handle_text_message(message, server, client)
            # File
            elif message_type == 3 and OK:
                handle_file_message(message, server, client, downloads_dir)
            # Disconnect
            elif message_type == 4:
                message = constructMessage("4", "2", 0, 0, "".encode())
                server.sendto(message, client)
                print(f'{client}: has left the server.')
                return
            # Keep alive
            elif message_type == 1 and flags == 4:
                if SWITCH:
                    message = constructMessage("5", "4", 0, 0, "".encode())
                    server.sendto(message, client)
                    SWITCH = False
                    print("Switching to CLIENT...")
                else:
                    message = constructMessage("1", "4", 0, 0, "".encode())
                    server.sendto(message, client)
                    print("Keep alive SERVER")
            # Switch
            elif message_type == 5 and flags == 0:
                message = constructMessage("5", "2", 0, 0, "".encode())
                server.sendto(message, client)
                KEEPALIVE = False
                SWITCH = False
                runningClient(server, client)
                return
            # Reconnect
            elif message_type == 1 and flags == 0:
                print(f"{client}: Client reconnected")
                message = constructMessage("1", "0", 0, 0, "".encode())
                server.sendto(message, client)
            else:
                if OK:
                    print("Invalid message type")

        # If client does not respond in TIMEOUT*12 seconds
        except socket.timeout:
            print("Client not responding. Exiting...")
            time.sleep(2)
            SERVER = False
        # If client disconnects
        except ConnectionResetError:
            print("Client disconnected. Exiting...")
            return
        except Exception as e:
            print("Error: ", e)
            return


# | * o - + ~ ¤  => Client Functions <= ~ + - * o * | #
def startClient():
    global BUFFER_SIZE
    global KEEPALIVE
    global CLIENTCONNECTED
    global TIMEOUT

    print(f"Your IP address is: {socket.gethostbyname(socket.gethostname())}")
    print("\nIP and PORT are required to connect to the server.")

    # Socket
    client = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    # IP and port
    ipaddress = input("Enter the IP address of the server: ")
    port = int(input("Enter the port of the server: "))

    # Server socket
    server = (ipaddress, port)
    CLIENTCONNECTED = True

    # Send init message to server
    while CLIENTCONNECTED:
        try:
            message = constructMessage("1", "0", 0, 0, "".encode())
            client.sendto(message, server)

            # Timeout to recieve ACK
            client.settimeout(TIMEOUT)

            # Receive acknowledgment from the server
            ack_message = client.recvfrom(BUFFER_SIZE)

            # Unpack the message
            message_type, flags, _, _, _, _ = decodeMessage(ack_message[0])

            # If the message is an ACK, set CLIENTCONNECTED to True and print a message
            if message_type == 1 and flags == 0:
                CLIENTCONNECTED = True
                KEEPALIVE = True
                print("Connecting to server...")
                print(f"Connected to {server}.")

            # Start running client
            runningClient(client, server)

        # If server does not respond in TIMEOUT seconds
        except socket.timeout:
            print(f"{server}: Not responding...")
            time.sleep(2)
            CLIENTCONNECTED = False
            KEEPALIVE = False
            return

        except ConnectionResetError:
            print("Server disconnected. Exiting...")
            CLIENTCONNECTED = False
            KEEPALIVE = False
            client.close()
            return

        except Exception as e:
            print("Error: ", e)
            return


def runningClient(client, server):
    global CLIENTCONNECTED
    global KEEPALIVE
    global BUFFER_SIZE
    global SWITCH

    # Keep alive thread
    KEEPALIVE = True
    t = threading.Thread(target=keepAlive, args=(client, server), daemon=True)
    t.start()

    # Start a while loop to listen for messages
    while CLIENTCONNECTED:
        try:
            KEEPALIVE = True
            # Display menu
            if SWITCH:
                choice = ""
            else:
                choice = input(
                    "\nChoose an option:\t1. Send text\t2. Send file\t3. Disconnect\t4. Switch\nEnter your choice: \n")

            # Get the fragment size
            if choice == "1" or choice == "2" or choice == "3" or choice == "4":
                KEEPALIVE = False
                if choice == "1" or choice == "2":
                    frag_size = input(f"Enter fragment size (32 - 1448): ")
                KEEPALIVE = True

            # Text message
            while choice == "1":
                KEEPALIVE = False
                message = input("Enter your text message: ")

                # If the message is "!back", go back to the menu
                if message == "!back":
                    KEEPALIVE = True
                    break
                KEEPALIVE = True

                # # --- DOIMPLEMENTACIA --- #
                # message = caesar_cipher(message)
                #
                # message = "___" + message + "___"
                # # --- DOIMPLEMENTACIA --- #

                # Send the message
                length = len(message)
                no_of_fragments = math.ceil(length / int(frag_size))
                send_data(client, server, 1, message.encode(), int(frag_size), no_of_fragments, "2")

            # File message
            if choice == "2":
                KEEPALIVE = False
                file_path = input("Enter the path of the file to send: ")
                KEEPALIVE = True

                # Check if the file exists
                if os.path.isfile(file_path):
                    with open(file_path, "rb") as file:
                        file_name = os.path.basename(file_path)
                        file_data = file.read()

                    # Send the file data to function send_file_fragments
                    no_of_fragments = math.ceil(len(file_data) / int(frag_size))
                    seq_number = 0
                    if seq_number == 0:
                        message = constructMessage("3", "1", no_of_fragments, seq_number, file_name.encode())
                        client.sendto(message, server)
                        seq_number += 1

                    send_data(client, server, seq_number, file_data, int(frag_size), no_of_fragments, "3")
                else:
                    print("File not found. Try again.")

            # Disconnect
            if choice == "3":
                # Send type 4 message
                message = constructMessage("4", "0", 0, 0, "".encode())
                client.sendto(message, server)

                # Recieve ACK
                ack_message = client.recvfrom(BUFFER_SIZE)
                message_type, flags, current_length, seq_number, checksum, data = decodeMessage(ack_message[0])

                # Turn off Keep Alive
                if message_type == 4 and flags == 2:
                    print("Disconnecting...")
                    CLIENTCONNECTED = False
                    KEEPALIVE = False

            # Switch
            elif choice == "4" or SWITCH:
                # Send switch message
                message = constructMessage("5", "0", 0, 0, "".encode())
                client.sendto(message, server)

                # Receive acknowledgment from the server
                ack = client.recvfrom(BUFFER_SIZE)
                message_type, flags, _, _, _, _ = decodeMessage(ack[0])

                # If the message is an ACK, set CLIENTCONNECTED to False and print a message, kill the keep alive thread and start running server
                if message_type == 5 and flags == 2:
                    print("Switching to SERVER")
                    # Kill keep alive thread
                    SWITCH = False
                    KEEPALIVE = False
                    t.join()
                    runningServer(client, server)
                    return

            else:
                KEEPALIVE = True
                print()

        except socket.timeout:
            print("Server not responding. Exiting...")
            KEEPALIVE = False
            return

        except ConnectionResetError:
            print("Server disconnected. Exiting...")
            CLIENTCONNECTED = False
            KEEPALIVE = False
            client.close()
            return

        except Exception as e:
            print("Error: ", e)
            return


# | * o - + ~ ¤  => Handling Frames <= ~ + - * o * | #
def handle_text_message(message, server, client_address):
    global rec_mesg

    # Unpack the message
    message_type, flags, num_of_fragments, seq_number, checksum, data = decodeMessage(message)

    # Buffer to store the data fragments
    if seq_number not in [item[0] for item in rec_mesg]:
        rec_mesg.append((seq_number, data))

    # If the message is fully received, print the message and send an ack to the client
    if seq_number <= num_of_fragments:
        # If the message was smaller than the fragment size, don't use fragment ack message
        if num_of_fragments != 1:
            ack_message = f"Fragment {seq_number} received. {(num_of_fragments - seq_number)} fragments remaining. Size {len(data)}B"
            print(ack_message)

        # If the message is fully received, print the message and send an ack to the client
        if seq_number == num_of_fragments:
            # Reconstruction of the message
            rec_mesg.sort(key=lambda seq_num: seq_num[0])
            decoded = b"".join([item[1] for item in rec_mesg])
            decoded = decoded.decode()
            print(f"{client_address}: {decoded}, Size {len(decoded)}B")

            # Send ack with flags 7 - message fully received
            message = constructMessage("2", "7", (num_of_fragments - seq_number), seq_number, "".encode())
            server.sendto(message, client_address)
            # Reset the rec_mesg variable
            rec_mesg = []

        else:
            # Send ack with flags 2 - fragment received
            message = constructMessage("2", "2", (num_of_fragments - seq_number), seq_number, "".encode())
            server.sendto(message, client_address)
        return


def handle_file_message(message, server, client_address, downloads_dir):
    global filename

    # Unpack the message
    message_type, flags, num_of_frags, seq_number, checksum, data = decodeMessage(message)

    # If the sequence number is 0, the data is the filename
    if seq_number == 0 and flags == 1:
        filename = data.decode()

    # decoded is data from the file after it was handled
    decoded = handle_file_fragments(seq_number, data, client_address, server, num_of_frags)

    if decoded is not None:
        # If the file already exists, add a number to the end of the filename
        filename = filename
        directory = downloads_dir

        # Check if the file already exists
        if filename in os.listdir(directory):
            filename = f"copy_{filename}"

        file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), directory, filename)

        # Write the file data to the file
        with open(file_path, "wb") as file:
            file.write(decoded)

        print(f'{client_address} sent a file. Data length: {len(decoded)}B')
        print(f'The file has been saved at: {file_path}')
    return


def handle_file_fragments(seq_number, data, client_address, server, num_frags):
    global rec_mesg

    # Check if the fragment is already in the list
    if seq_number not in [item[0] for item in rec_mesg]:
        # If sequence number is not 0, add the data to the buffer
        if seq_number != 0:
            rec_mesg.append((seq_number, data))

    # If the file is fully received, return the decoded data
    if seq_number == num_frags:
        print(f"Fragment {seq_number} received. {num_frags - seq_number} fragments remaining. Size {len(data)}B")
        message = constructMessage("3", "7", num_frags, seq_number, "".encode())
        server.sendto(message, client_address)

        # Reconstruction of the file
        rec_mesg.sort(key=lambda seq_num: seq_num[0])
        msg = b"".join([item[1] for item in rec_mesg])
        rec_mesg = []
        return msg

    # If sequence number is more or equal to 1, send an ack to the client and print the message
    if seq_number >= 1:
        print(f"Fragment {seq_number} received. {num_frags - seq_number} fragments remaining. Size {len(data)}B")

        message = constructMessage("3", "2", num_frags, seq_number, "".encode())
        server.sendto(message, client_address)


# | * o - + ~ ¤  => Sending Frames <= ~ + - * o * | #
def send_data(client, server, seq_number, data, fragment_size, no_of_fragments, message_type):
    total_length = len(data)
    X = total_length

    # Split the data into fragments
    fragments = []
    while total_length > 0:
        current_fragment_size = min(fragment_size, total_length)
        current_fragment = data[:current_fragment_size]
        fragments.append(current_fragment)
        data = data[current_fragment_size:]
        total_length -= current_fragment_size

    total_length = X
    while total_length > 0:
        current_fragment_size = min(fragment_size, total_length)

        # Error simulation
        error = 1 if random.randint(1, 100) <= ERROR_PROBABILITY else 0

        # Construct the message
        if seq_number == 1:
            message = constructMessage(message_type, "1", no_of_fragments, seq_number, fragments[seq_number - 1], error)
        elif seq_number == no_of_fragments:
            message = constructMessage(message_type, "5", no_of_fragments, seq_number, fragments[seq_number - 1])
        else:
            message = constructMessage(message_type, "0", no_of_fragments, seq_number, fragments[seq_number - 1], error)

        client.sendto(message, server)

        # Receive acknowledgment from the server for the current fragment
        ack_message = client.recvfrom(BUFFER_SIZE)
        message_type, flags, _, ack, _, _ = decodeMessage(ack_message[0])

        # Check flags - 7 received, 2 Ack, 3 NegAck
        if message_type == int(message_type) and flags == 7:
            print(f"Fragment {ack} received. {no_of_fragments - ack} fragments remaining. Size {current_fragment_size}B")
            # If file - print absolute path
            print(f"Message received. Size {X}" if message_type == 2 else f"File received. Size {X} Path: {os.path.abspath(filename)}")
            break
        elif message_type == int(message_type) and flags == 2:
            print(f"Fragment {ack} received. {no_of_fragments - ack} fragments remaining. Size {current_fragment_size}B")
            # Move to the next fragment
            total_length -= current_fragment_size
            seq_number += 1
        # If the message is corrupted, resend the current fragment
        elif message_type == int(message_type) and flags == 3:
            while message_type == int(message_type) and flags == 3:
                print("Fragment corrupted")
                # Based on ack, resend the current fragment
                if ack == 1:
                    fl = "1"
                else:
                    fl = "0"
                message = constructMessage(message_type, fl, no_of_fragments, seq_number, fragments[seq_number - 1], error)
                client.sendto(message, server)

                # Receive acknowledgment from the server for the current fragment
                ack = client.recvfrom(BUFFER_SIZE)
                message_type, flags, _, ack, _, _ = decodeMessage(ack[0])
                error = 1 if random.randint(1, 100) <= ERROR_PROBABILITY else 0

            # Check flags 2 Ack, 3 NegAck
            if message_type == int(message_type) and flags == 2:
                print(f"Fragment {ack} received. {no_of_fragments - ack} fragments remaining. Size {current_fragment_size}B")
                # Move to the next fragment
                total_length -= current_fragment_size
                seq_number += 1
        elif message_type != int(message_type):
            print("Invalid message type")


# | * o - + ~ ¤  => Main <= ~ + - * o * | #
def main():
    # Menu
    while True:
        print("1. Server | 2. Client | 3. Exit")
        choice = input("Enter your choice: ")

        if choice == "1":
            startServer()
        elif choice == "2":
            startClient()
        elif choice == "3":
            print("Exiting...")
            return 0
        else:
            print("Invalid choice. Try again.")


if __name__ == "__main__":
    main()
