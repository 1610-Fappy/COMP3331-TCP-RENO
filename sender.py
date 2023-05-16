"""
    Sample code for Sender (multi-threading)
    Python 3
    Usage: python3 sender.py receiver_port sender_port FileToSend.txt max_recv_win rto
    coding: utf-8

    Notes:
        Try to run the server first with the command:
            python3 receiver_template.py 9000 10000 FileReceived.txt 1 1
        Then run the sender:
            python3 sender_template.py 11000 9000 FileToReceived.txt 1000 1

    Author: Rui Li (Tutor for COMP3331/9331)
"""
import traceback
# here are the libs you may find it useful:
import datetime, time  # to calculate the time delta of packet transmission
import logging, sys  # to write the log
import socket  # Core lib, to send packet via UDP socket
from threading import Thread  # (Optional)threading will make the timer easily implemented
from random import randint # Import function to create random starting seqno between 0 and  2^16 - 1

BUFFERSIZE = 1024


class Sender:
    def __init__(self, sender_port: int, receiver_port: int, filename: str, max_win: int, rot: int) -> None:
        '''
        The Sender will be able to connect the Receiver via UDP
        :param sender_port: the UDP port number to be used by the sender to send PTP segments to the receiver
        :param receiver_port: the UDP port number on which receiver is expecting to receive PTP segments from the sender
        :param filename: the name of the text file that must be transferred from sender to receiver using your reliable transport protocol.
        :param max_win: the maximum window size in bytes for the sender window.
        :param rot: the value of the retransmission timer in milliseconds. This should be an unsigned integer.
        '''
        self.sender_port = int(sender_port)
        self.receiver_port = int(receiver_port)
        self.sender_address = ("127.0.0.1", self.sender_port)
        self.receiver_address = ("127.0.0.1", self.receiver_port)

        # init the UDP socket
        logging.debug(f"The sender is using the address {self.sender_address}")
        self.sender_socket = socket.socket(family=socket.AF_INET, type=socket.SOCK_DGRAM)
        self.sender_socket.bind(self.sender_address)
        self.sender_socket.settimeout(2)

        #  (Optional) start the listening sub-thread first
        self._is_active = True  # for the multi-threading
        listen_thread = Thread(target=self.listen)
        listen_thread.start()


        # todo add codes here
        # Initialise list of unacked packets
        self.unack = []
        self.nextunack = []
        self.was_unackprev = False
        # Initialise initial time to 0
        self.initial_time = 0
        # Initialise flag to signal that we are transmitting data
        self.transmitting = False
        # Initialise which seq packet the receiver has received
        self.ack = -1
        # Initialise filename of file to be read
        self.filename = ''
        self.set_filename(filename)
        # Initialise max_win value as value given
        self.max_win = 0
        self.set_max_win(int(max_win))
        # Initialise chunk size to be transmitted as 1000 bytes or as max_win if max_win less than 1000 bytes
        self.chunk_size = 1000
        self.set_chunk_size()
        # Initialise state to 'CLOSED'
        self.state = 'SYN_SENT'
        # Initialise seqno as random_value
        self.seqno = 0
        self.set_seqno()
        # Store first seq value in varialbe
        self.initialseq = 0
        self.set_initialseq()
        # Initialise list of data to be sent
        self.list_data = []
        self.set_list_data()
        # Initialise amount of retransmits already
        self.retransmit = 1
        # Initialise rto value
        self.rto = 2
        self.set_rto(float(rot))
        # Initialise variable that will be used to check if all packets acked
        self.all_acked = False
        # Initialise timer varialbe
        self.timer = time.time()
        # Initialise list of sent packets
        self.sent_packets = []
        # Initialise list associated next packets
        self.next_packets = []
        # Initialise variable to understand how many packets we can send in window
        self.amount_cansend = 0
        self.set_amountcansend()
        # Initialise variable that will store if we are resending packet or not
        self.resend = False
        # Initialise list of received packets
        self.rcv = []


        self.wait_last = False
        timer_thread = Thread(target=self.timer_loop)
        timer_thread.start()

        pass

    # Setter and Getter Methods

    def append_unackets(self,value):
        self.unack.append(value)

    def get_unack(self):
        return self.unack

    def remove_unack(self,value):
        self.unack.remove(value)

    def append_nextunack(self,value):
        self.nextunack.append(value)

    def get_nextunack(self):
        return self.nextunack

    def set_waitlast(self,value):
        self.wait_last = value

    def get_waitlast(self):
        return self.wait_last

    def append_rcv(self,value):
        self.rcv.append(value)
    
    def reset_rcv(self):
        self.rcv = []

    def get_rcv(self):
        return self.rcv

    def remove_rcv(self):
        rcv_list = self.get_rcv()
        sent_list = self.get_sentpackets()
        next_list = self.get_nextpacket()
        for i in next_list:
            if (i in rcv_list):
                indexval = next_list.index(i)
                self.pop_lastpacket(indexval)
                self.pop_nextpacket(indexval)


    def set_initialseq(self):
        self.initialseq = self.get_seqno()

    def get_initialseq(self):
        return self.initialseq

    def set_resend(self,value):
        self.resend = value

    def get_resend(self):
        return self.resend

    def set_amountcansend(self):
        self.amount_cansend = self.get_max_win()/1000.0

    def get_amountcansend(self):
        return self.amount_cansend

    def append_nextpacket(self,packet):
        self.next_packets.append(packet)
    
    def pop_nextpacket(self,index):
        self.next_packets.pop(index)

    def get_nextpacket(self):
        return self.next_packets

    def append_sentpackets(self,packet):
        self.sent_packets.append(packet)
    
    def pop_lastpacket(self,index):
        self.sent_packets.pop(index)

    def get_sentpackets(self):
        return self.sent_packets

    def set_timer(self):
        self.timer = time.time()

    def reset_timer(self):
        self.timer = time.time()

    def get_timer(self):
        return self.timer

    def set_allacked(self,value):
        self.all_acked = value

    def get_allacked(self):
        return self.all_acked

    def set_rto(self,value):
        self.rto = value
    
    def get_rto(self):
        return self.rto

    def set_initial_time(self,value):
        self.initial_time = value

    def get_initial_time(self):
        return self.initial_time

    def set_ack(self,value):
        if (value > 2**16 - 1):
            value -= 2**16 - 1
        self.ack = value

    def get_ack(self):
        return self.ack

    def set_seqno(self):
        self.seqno = randint(0,2**16 - 1)

    def update_seqno(self,new_val):
        if (new_val > 2**16 - 1):
            new_val -= 2**16 - 1

        self.seqno = new_val

    def get_seqno(self):
        return self.seqno

    def set_max_win(self,max_win):
        self.max_win = max_win

    def get_max_win(self):
        return self.max_win

    def set_chunk_size(self):
        max_win = self.get_max_win()
        if (max_win < 1000):
            self.chunk_size = max_win
        else:
            self.chunk_size = 1000

    def get_chunk_size(self):
        return self.chunk_size

    def set_state(self,state):
        '''
        Possible states:
            CLOSED
            SYN_SENT
            ESTABLISHED
            CLOSING
            FIN_WAIT
        '''
        self.state = state

    def get_state(self):
        return self.state

    def set_filename(self,filename):
        self.filename = filename

    def get_filename(self):
        return self.filename

    def set_list_data(self):
        self.list_data = self.create_list_datapackets()

    def update_list_data(self,new_list):
        self.list_data = new_list

    def get_list_data(self):
        return self.list_data

    def get_packet(self):
        
        data_packets = self.get_list_data()
        if (not self.get_resend()):
            current_seqno = self.get_seqno()
        else:
            if (self.was_unackprev):
                current_seqno = self.get_unack()[0]
            else:
                current_seqno = self.get_sentpackets()[0]
        for packet in data_packets:
            seqno = packet['seqno']
            if (seqno == current_seqno):
                return packet
        
        return None

    def get_lastseq(self):
        last_packet = self.get_list_data()[-1]

        last_seqval = last_packet['seqno'] + len(last_packet['content_chunk'])

        return last_seqval

    def set_retransmit(self,value):
        self.retransmit = value

    def get_retransmit(self):
        return self.retransmit


    # Methods used to create different packets that we need to send

    def get_nextseq(self,value):
        if (value > 2**16 - 1):
            return (value - (2**16 - 1))

        return value

    def update_start(self,start_time):
        new_list = []
        data_packet = self.get_packet()
        data_packet['sent_time'] = start_time

    def create_list_datapackets(self):
        '''
        DataPacket form {
            'type', 'DATA'
            'seqno', prev_seqno + prev_size
            'content_chunk', data being transmitted
            'sent_time', To be filled
        }
        '''
        file_data = self.read_file(self.get_filename())
        content_chunks = self.split_content(file_data)
        type_uint = self.twoB_uint_conv(self.type_to_int('DATA'))
        
        seqno = self.get_seqno() +1

        datapackets = []

        for i,value in enumerate(content_chunks):
            datapackets.append({
                'type' : type_uint,
                'seqno' : seqno,
                'content_chunk' : value.encode('utf-8'),
                'sent_time' : None
            })
            self.append_unackets(seqno)
            self.append_nextunack(seqno + len(value.encode('utf-8')))
            seqno +=  len(value.encode('utf-8'))
            if (seqno > 2**16 -1):
                seqno -= 2**16 -1

        return datapackets

    def create_datapackets(self):
        data_packet = self.get_packet()
        encoded_packet = data_packet.copy()
        encoded_packet['seqno'] = self.twoB_uint_conv(encoded_packet['seqno'])

        return encoded_packet

    def create_synpackets(self):
        '''
        synPacket form {
            'type', 'SYN'
            'seqno', Initial seqno of first packet
            'content_chunk', empty
            'sent_time', To be filled
        }
        '''
        type_uint = self.twoB_uint_conv(self.type_to_int('SYN'))
        init_seqno_uint = self.twoB_uint_conv(self.get_initialseq()) 
        syn_packet = {
            'type' : type_uint,
            'seqno' : init_seqno_uint,
            'content_chunk' : '',
            'sent_time' : None
        }
        
        self.set_synpackets(syn_packet)

        return syn_packet

    def set_synpackets(self,value):
        self.synpacket = value

    def get_synpackets(self):
        return self.synpacket

    def create_resetpackets(self):
        '''
        synPacket form {
            'type', 'RESET'
            'seqno', set to 0
            'content_chunk', empty
            'sent_time', To be filled
        }
        '''
        type_uint = self.twoB_uint_conv(self.type_to_int('RESET'))
        seqno_uint = self.twoB_uint_conv(0) 
        res_packet = {
            'type' : type_uint,
            'seqno' : seqno_uint,
            'content_chunk' : '',
            'sent_time' : None
        }

        return res_packet

    def create_finpackets(self):
        '''
        finpacket form {
            'type', 'FIN'
            'seqno', set to 0
            'content_chunk', empty
            'sent_time', To be filled
        }
        '''
        type_uint = self.twoB_uint_conv(self.type_to_int('FIN'))
        seqno_uint = self.twoB_uint_conv(self.get_lastseq() + 1) 
        fin_packet = {
            'type' : type_uint,
            'seqno' : seqno_uint,
            'content_chunk' : '',
            'sent_time' : None
        }

        return fin_packet


    # Irrelevant so far for sender
    def create_ackpackets(self):
        pass

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


    def bytes_to_int(self,byteval):
        return int.from_bytes(byteval,'big')

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
            packets = self.create_finpackets()
            pass
        elif (packet_type == 'RESET'):
            packets = self.create_resetpackets()
            pass
        else:
            pass

        return packets

    def read_file(self,textfile):
        f = open(textfile, "r")
        content = f.read()
        f.close()

        return content

    def split_content(self,content):

        num_bytes = self.get_chunk_size()
        split_data = []

        for i in range (0,len(content),num_bytes):
            split_data.append(content[i:i+num_bytes])

        return split_data



    def ptp_open(self):
        # todo add/modify codes here

        # Sets our state to SYN_SENT
        self.set_state('SYN_SENT')
        

        pass

    def transmit_data(self,message):
        
        self.sender_socket.sendto(message,self.receiver_address)
        

    def ptp_send(self):

        ack_no = self.get_ack()
        state = self.get_state()
        initial_time = self.get_initial_time()
        if (state == 'RESET'):
            
            # Create data packet that we will send off
            data_packet = self.create_packets('RESET')

            self.set_resend(False)

            # Extract and concatenate our encoded data to be sent off as bytes
            message = data_packet['type'] + data_packet['seqno']
            
            # Get seq num of packet that we have sent to receiver
            seqno_sent = self.bytes_to_int(data_packet['seqno'])

            self.set_timer()

            # Find packet time reference to initial syn packet
            time_since_init = self.get_timer() - initial_time

            # Logging that we are sending the packet 
            logging.info(f"snd\t{time_since_init*1000:.2f}\tRESET\t{seqno_sent}\t{0}")

            # Transmitting the packet
            self.transmit_data(message)

            self.ptp_close()


        elif (state == 'SYN_SENT'):
            # create SYN packet dictionary
            syn_packet = self.create_packets('SYN')

            # Get seq num of packet that we have sent to receiver
            seqno_sent = self.bytes_to_int(syn_packet['seqno'])
            
            if (seqno_sent not in self.get_sentpackets() and len(self.get_sentpackets()) < self.get_amountcansend()):
                self.append_sentpackets(seqno_sent)
                next_seq = self.get_nextseq(seqno_sent + 1)
                self.append_nextpacket(next_seq)

            if (not self.get_resend()):

                # Update which seqno we are currently expecting to send to receiver
                self.update_seqno(seqno_sent + 1)
            
            self.set_resend(False)


            # Extract what we need to send in our syn packet
            message = syn_packet['type'] + syn_packet['seqno']
                    
            if (ack_no == self.get_sentpackets()[0]):

                # Store send time of  packet
                self.set_timer()

            time_since_init = time.time() - initial_time

            if (initial_time == 0):

                # sets initial time as time that syn packet is sent
                self.set_timer()
                initial_time = self.get_timer()

                # set our initial time variable as time syn packet sent
                self.set_initial_time(initial_time)

                # Set initial syn packet as time 0
                time_since_init = initial_time - initial_time

            # Logging
            logging.info(f"snd\t{time_since_init*1000:.2f}\tSYN\t{self.get_initialseq()}\t{0}")

            # Sending our syn packet
            self.transmit_data(message)

        elif (self.get_allacked() and (state == 'CLOSING' or state == 'FIN_WAIT')):
            # set state to waiting for fin
            self.set_state('FIN_WAIT')
            # Create FIN Packet
            fin_packet = self.create_packets('FIN')

            # Get seq num of packet that we have sent to receiver
            seqno_sent = self.bytes_to_int(fin_packet['seqno'])

            if (seqno_sent not in self.get_sentpackets() and len(self.get_sentpackets()) < self.get_amountcansend()):
                self.append_sentpackets(seqno_sent)
                next_seq = self.get_nextseq(seqno_sent + 1)
                self.append_nextpacket(next_seq)

            if (not self.get_resend()):

                # Update which seqno we are currently expecting to send to receiver
                self.update_seqno(seqno_sent + 1)

            self.set_resend(False)


            # Extract what we need from packet dictionary
            message = fin_packet['type'] + fin_packet['seqno']

            if (ack_no == self.get_sentpackets()[0]):

                # Store send time of  packet
                self.set_timer()
            time_since_init = time.time() - initial_time

            # Logging
            logging.info(f"snd\t{time_since_init*1000:.2f}\tFIN\t{seqno_sent}\t{0}")

            # Sending our FIN packet
            self.transmit_data(message)

        elif (not self.get_waitlast() and self.get_seqno() != self.get_lastseq() and len(self.get_unack()) != 0):
            # Create data packet that we will send off
            data_packet = self.create_packets('DATA')

            # Get seq num of packet that we have sent to receiver
            seqno_sent = self.bytes_to_int(data_packet['seqno'])
            
            next_seq = self.get_nextseq(seqno_sent + len(data_packet['content_chunk']))

            if (len(self.get_sentpackets()) < self.get_amountcansend() or self.get_resend()):

                # Condition checks if packet being sent already in our sent packet list
                if (seqno_sent not in self.get_sentpackets()):
                    self.append_sentpackets(seqno_sent)
                    self.append_nextpacket(next_seq)
                    

                # Condition checks whether if we are not resending, then updates expected packet to send as next packet avail
                if(len(self.get_unack()) == 0):
                    next_seq = self.get_lastseq()
                    self.set_allacked(True)
                    pass
                elif (self.was_unackprev and seqno_sent < self.get_unack()[0]):
                    next_seq = self.get_unack()
                    self.update_seqno(next_seq)
                elif (not self.get_resend()):
                        self.was_unackprev = False
                        # Update which seqno we are currently expecting to send to receiver
                        self.update_seqno(seqno_sent + len(data_packet['content_chunk']))
                elif(len(self.get_unack()) == 1 and self.get_resend()):
                    next_seq = self.get_unack()[0]
                    self.update_seqno(next_seq)
                    self.was_unackprev = True
                elif(len(self.get_unack()) > 1):
                    next_seq = self.get_unack()[1]
                    self.update_seqno(next_seq)
                    self.was_unackprev = True


                # After evaluating above condition set resend to false
                self.set_resend(False)

                # Extract and concatenate our encoded data to be sent off as bytes
                message = data_packet['type'] + data_packet['seqno'] + data_packet['content_chunk']
                

                # If our current acknowledged packet is equal to our oldest sent packet, reset timer for new packet
                if (ack_no == self.get_sentpackets()[0]):

                    # Store send time of  packet
                    self.set_timer()


                # Find packet time reference to initial syn packet
                time_since_init = time.time() - initial_time

                # Logging that we are sending the packet 
                logging.info(f"snd\t{time_since_init*1000:.2f}\tDATA\t{seqno_sent}\t{len(data_packet['content_chunk'])}")
                
                if (not self.get_allacked()):
                    # Transmitting the packet
                    self.transmit_data(message)
                
                # Accounting for fin packet needing to be sent instead of data packet
                if (next_seq != self.get_lastseq() ):
                    self.ptp_send()
                elif (self.get_allacked()):
                    self.set_waitlast(True)
        pass

    def ptp_close(self):
        # todo add codes here
        self._is_active = False  # close the sub-thread
        self.set_state('CLOSED')
        exit(1)
        pass

    def timer_loop(self):

        # Initialise timer value
        timer_value = self.get_timer()
        
        # Get rto time and store in variable
        rto = self.get_rto()

        # Variable to check if all packets are acked
        all_acked = self.get_allacked()

        # Get sequence number meaning we reached last packet
        last_seqval = self.get_lastseq()

        # Get amount of times retransmitted
        retransmit = self.get_retransmit()
        while (not all_acked):
            # Get current time
            ctime = time.time()

            # Variable to check if all packets are acked
            all_acked = self.get_allacked()

            # Get sender state
            state = self.get_state()

            # Get timer value
            timer_value = self.get_timer()

            # Get last acked packet seqno
            ack_no = self.get_ack()

            # Get amount of times retransmitted
            retransmit = self.get_retransmit()
            if (state == 'SYN_SENT'):
                pass
            elif (state == 'FIN_WAIT'):
                pass
            elif (len(self.get_unack()) == 0):
                self.set_allacked(True)
                break

            if (state == 'RESET' or ack_no == (last_seqval + 1)):
                self.sender_socket.shutdown(socket.SHUT_RDWR)
                self.ptp_close()
                break

            elif ((time.time() - timer_value)*1000 > rto and retransmit > 3):
                self.set_state('RESET')
                self.ptp_send()
            # Check if time since packet sent is within timeout range
            elif ((time.time() - timer_value)*1000 > rto and not self.get_resend()):
                print('resending')
                if (self.get_seqno() == self.get_lastseq()):
                    self.update_seqno(self.get_unack()[0])
                self.reset_timer()
                self.set_resend(True)
                self.set_retransmit(retransmit + 1)
                self.ptp_send()

    def listen(self):
        '''(Multithread is used)listen the response from receiver'''
        logging.debug("Sub-thread for listening is running")
        while self._is_active:
            # todo add socket
            try:
                # Receiving packet
                incoming_message, _ = self.sender_socket.recvfrom(BUFFERSIZE)
                
                # Extracting packet type
                typeval = self.get_type(self.bytes_to_int(incoming_message[0:2]))
                
                # Extracting seq num from packet
                packetno = self.bytes_to_int(incoming_message[2:4])

                # Extracting data length
                content_len = len(incoming_message[4:])

                # Get state to determine what to do with packet
                sender_state = self.get_state()
                
                # Get receive time of packet and put it in relation to first syn packet
                rcv_time = time.time()
                time_since_init = rcv_time - self.get_initial_time()
                

                # update ack_no to represent latest ack'd packet
                self.set_ack(packetno)

                # Log data of packets received
                logging.info(f"rcv\t{time_since_init*1000:.2f}\t{typeval}\t{packetno}\t{content_len}")
                
                sentnextpack = self.get_nextpacket()
                sentpackets = self.get_sentpackets()

                # Retrieve last seqval to know when to stop transmitting data
                last_seqval = self.get_lastseq()
                if (packetno == last_seqval and (self.get_nextpacket()[0] == last_seqval or self.get_nextpacket()[0] == last_seqval + 1 or len(self.get_unack()) == 0)):
                    self.set_allacked(True)
                    self.set_state('CLOSING')
                    #SEND VALUES
                    self.reset_timer()
                    self.set_retransmit(1)


                    # Calling on our sending function
                    self.ptp_send()
                elif (packetno == last_seqval):
                    #SEND VALUES
                    pass
                elif (sender_state == 'FIN_WAIT'):
                    self.set_state('CLOSED')
                    self.ptp_close()
                # Condition to move from SYN_SENT STATE TO ESTABLISHED STATE
                elif (sender_state == 'SYN_SENT'):
                    # Update our state to be ESTABLISHED
                    self.set_state('ESTABLISHED')

                    self.append_rcv(packetno)
                    if (packetno == sentnextpack[0]):
                        self.reset_timer()
                        self.remove_rcv()

                    self.set_retransmit(1)

                    # Calling on our sending function
                    self.ptp_send()

                else:
                    #print(self.get_sentpackets(),self.get_nextpacket())
                    
                    index = self.get_nextunack().index(packetno)
                    self.get_unack().pop(index)
                    self.get_nextunack().pop(index)

                    self.append_rcv(packetno)
                    if (packetno == sentnextpack[0]):
                        self.reset_timer()
                        self.remove_rcv()

                    self.set_retransmit(1)
                    self.ptp_send()


                pass
            except socket.timeout as err:
                print('timeout',self.get_ack())
                self.ptp_close()

            except Exception as e:
                traceback.print_exc()
                print(e)
                pass

    def run(self):
        '''
        This function contain the main logic of the receiver
        '''
        # todo add/modify codes here
        self.ptp_open()
        self.ptp_send()


if __name__ == '__main__':
    # logging is useful for the log part: https://docs.python.org/3/library/logging.html
    logging.basicConfig(
        # filename="Sender_log.txt",
        stream=sys.stderr,
        level=logging.DEBUG,
        format='%(asctime)s,%(msecs)03d %(levelname)-8s %(message)s',
        datefmt='%Y-%m-%d:%H:%M:%S')

    logger = logging.getLogger()

    file_handler = logging.FileHandler('senderlogs')
    file_handler.setLevel(logging.DEBUG)
    
    logger.addHandler(file_handler)

    if len(sys.argv) != 6:
        print(
            "\n===== Error usage, python3 sender.py sender_port receiver_port FileReceived.txt max_win rot ======\n")
        exit(0)

    sender = Sender(*sys.argv[1:])
    sender.run()
