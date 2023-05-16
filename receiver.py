"""
    Sample code for Receiver
    Python 3
    Usage: python3 receiver.py receiver_port sender_port FileReceived.txt flp rlp
    coding: utf-8

    Notes:
        Try to run the server first with the command:
            python3 receiver_template.py 9000 10000 FileReceived.txt 1 1
        Then run the sender:
            python3 sender_template.py 11000 9000 FileToReceived.txt 1000 1

    Author: Rui Li (Tutor for COMP3331/9331)
"""
# here are the libs you may find it useful:
import datetime, time  # to calculate the time delta of packet transmission
import logging, sys  # to write the log
import socket  # Core lib, to send packet via UDP socket
from threading import Thread  # (Optional)threading will make the timer easily implemented
import random  # for flp and rlp function

BUFFERSIZE = 1024


class Receiver:
    def __init__(self, receiver_port: int, sender_port: int, filename: str, flp: float, rlp: float) -> None:
        '''
        The server will be able to receive the file from the sender via UDP
        :param receiver_port: the UDP port number to be used by the receiver to receive PTP segments from the sender.
        :param sender_port: the UDP port number to be used by the sender to send PTP segments to the receiver.
        :param filename: the name of the text file into which the text sent by the sender should be stored
        :param flp: forward loss probability, which is the probability that any segment in the forward direction (Data, FIN, SYN) is lost.
        :param rlp: reverse loss probability, which is the probability of a segment in the reverse direction (i.e., ACKs) being lost.

        '''
        self.address = "127.0.0.1"  # change it to 0.0.0.0 or public ipv4 address if want to test it between different computers
        self.receiver_port = int(receiver_port)
        self.sender_port = int(sender_port)
        self.server_address = (self.address, self.receiver_port)
        random.seed()

        # init the UDP socket
        # define socket for the server side and bind address
        logging.debug(f"The sender is using the address {self.server_address} to receive message!")
        self.receiver_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.receiver_socket.bind(self.server_address)

        # Initialise seqno, this tracks which seqno we expect to see next
        self.seqno = 0

        self.initial_time = 0

        # Initialise flp, this is the chance of a packet being lost on its way to the receiver
        self.flp = 0.0
        self.set_flp(float(flp))

        # Initialise rlp, this is the chance of a packet being lost on its way to the sender
        self.rlp = 0.0
        self.set_rlp(float(rlp))

        # Initialise txtfile name that will be used to store received content
        self.filename = ''
        self.set_filename(filename)
        pass

    def set_initial_time(self):
        self.initial_time = time.time()

    def get_init_time(self):
        return self.initial_time

    def set_filename(self,filename):
        self.filename = filename

    def get_filename(self):
        return self.filename

    def set_flp(self,value):
        self.flp = value
    
    def get_flp(self):
        return self.flp

    def set_rlp(self,value):
        self.rlp = value

    def get_rlp(self):
        return self.rlp

    # False means packet never received, True opposite
    def forward_loss(self):
        flp = self.get_flp()
        if(random.random() < flp):
            return False

        return True

    def reverse_loss(self):
        rlp = self.get_rlp()
        if(random.random() < rlp):
            return False

        return True

    def writetofile(self, content: str):
        f = open(self.get_filename(), "a") # Opens file in append mode
        f.write(content)
        f.close()

    def bytes_to_int(self,byteval):
        return int.from_bytes(byteval,'big')

    def get_type(self,value):
        if (value == 0):
            return 'DATA'
        elif (value == 1):
            return 'ACK'
        elif (value == 2):
            return 'SYN'
        elif (value == 3):
            return 'FIN'
        elif (value == 4):
            return 'RESET'

    def set_seqno(self,value):
        if (value > 2**16 - 1):
            value -= 2**16 -1
        self.seqno = value
        pass

    def get_seqno(self):
        return self.seqno

    # Irrelevant so far
    def create_datapackets(self):
        pass

    def create_synpackets(self):
        pass

    def create_resetpackets(self):
        pass


    def type_to_int(self,packet_type):

        if (packet_type== 'DATA'):
            return 0
        elif (packet_type== 'ACK'):
            return 1
        elif (packet_type== 'SYN'):
            return 2
        elif (packet_type== 'FIN'):
            return 3
        elif (packet_type== 'RESET'):
            return 4

    def twoB_uint_conv(self,value):

        if (value > 2**16 - 1):
            value -= 2**16 - 1
        converted = value.to_bytes(2,'big',signed=False)
        return converted

    def create_ackpackets(self):
        '''
        ackPacket form {
            'type', 'ACK'
            'seqno', seqno{last packet} + {len(last_packet)} + 1
            'content_chunk', empty
            'sent_time', To be filled
        }
        '''
        type_uint = self.twoB_uint_conv(self.type_to_int('ACK'))
        seqno_uint = self.twoB_uint_conv(self.get_seqno()) 
        ackPacket = {
            'type' : type_uint,
            'seqno' : seqno_uint,
            'content_chunk' : '',
            'sent_time' : None
        }
        return ackPacket


    def create_packets(self,packet_type):

        packets = None

        if (packet_type == 'DATA'):
            packets = self.create_datapackets()
            pass
        elif (packet_type == 'ACK'):
            packets = self.create_ackpackets()
            pass
        elif (packet_type == 'SYN'):
            packets = self.create_synpackets()
            pass
        elif (packet_type == 'FIN'):
            pass
        elif (packet_type == 'RESET'):
            packets = self.create_resetpackets()
            pass
        else:
            pass

        return packets

    def run(self) -> None:
        '''
        This function contain the main logic of the receiver
        '''
        while True:
            # try to receive any incoming message from the sender
            incoming_message, sender_address = self.receiver_socket.recvfrom(BUFFERSIZE)

            packet_received = self.forward_loss()

            typeval = self.get_type(self.bytes_to_int(incoming_message[0:2]))

            packetno = self.bytes_to_int(incoming_message[2:4])
            
            content = incoming_message[4:]
            content_len = len(content)
            if (typeval == 'SYN' and self.get_init_time() == 0):
                self.set_initial_time()

            if (typeval == 'RESET'):
                print('resetting')
                break
                
            if (packet_received):
                
                logging.info(f"rcv\ttime\t{typeval}\t{packetno}\t{content_len}")

                packet_sent = self.reverse_loss()
                if (packet_sent):

                    if (typeval == 'SYN' or typeval == 'FIN'):
                        self.set_seqno(packetno + 1)
                    elif (typeval == 'DATA'):
                        self.writetofile(content.decode('utf-8'))
                        self.set_seqno(packetno + len(content))

                    # reply "ACK" once receive any message from sender
                    reply_packet = self.create_packets('ACK')
                    reply_message = reply_packet['type'] + reply_packet['seqno']
                    logging.info(f"snd\t{(time.time() - self.get_init_time())*1000:.2f}\tACK\t{self.get_seqno()}\t0")
                    self.receiver_socket.sendto(reply_message,
                                                sender_address)

                    if (typeval == 'FIN'):
                        logging.info(f"end\t{(time.time() - self.get_init_time())*1000:.2f}\tACK\t{self.get_seqno()}\t0")
                        break
                else:
                    logging.info(f"drp ack\t{(time.time() - self.get_init_time())*1000:.2f}\t{packetno}\t{content_len}")
            else:
                logging.info(f"drp rcv\t{(time.time() - self.get_init_time())*1000:.2f}\t{typeval}\t{packetno}\t{content_len}")


if __name__ == '__main__':
    # logging is useful for the log part: https://docs.python.org/3/library/logging.html
    logging.basicConfig(
        # filename="Receiver_log.txt",
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S')

    logger = logging.getLogger()

    file_handler = logging.FileHandler('receiverlogs')
    file_handler.setLevel(logging.DEBUG)
    
    logger.addHandler(file_handler)

    if len(sys.argv) != 6:
        print(
            "\n===== Error usage, python3 receiver.py receiver_port sender_port FileReceived.txt flp rlp ======\n")
        exit(0)

    receiver = Receiver(*sys.argv[1:])
    receiver.run()
