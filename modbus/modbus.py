# Defination for modbus protocol tcp/ip client and data
# Implemented just for read holding registers address will start 40.000
# http://modbus.org/docs/PI_MBUS_300.pdf for more info

# includes consts
from . import modbusdefination as const

# standart packages
import re
import socket
import select
import struct
import random
import datetime

THIS_FILE = "__modbus.py__"

class modbus:
    def __init__(self, host=None, port=None, unit_id=None, timeout=None,
                 debug=None, auto_open=None):
        # object vars
        self.__hostname = 'target'
        self.__port = const.MODBUS_DEFAULT_PORT
        self.__unit_id = 1
        self.__timeout = 3.0                # socket timeout
        self.__debug = False                 # debug trace on/off
        self.__auto_open = True             # auto TCP connect
        self.__mode = const.MODBUS_TCP       # default is Modbus/TCP
        self.__sock = None                   # socket handle
        self.__transaction_id = 0                  # store transaction ID
        if host:
            if not self.host(host):
                raise ValueError("modbus host's error")
        if port:
            if not self.port(port):
                raise ValueError("modbus port's error")

    # set plc ip adress for tcp mode
    def set_plc_address(self, hostname=None):
        if (hostname is None) or (hostname == self.__hostname):
            return self.__hostname
        self.plc_close_port()
        try:
            socket.inet_pton(socket.AF_INET, hostname)
            self.__hostname = hostname
            return self.__hostname
        except socket.error:
            pass

    # set plc port default port is 502
    def set_plc_port(self, port=None):
        if (port is None) or (port == self.__port):
            return self.__port
        self.plc_close_port()

        if 0 < int(port) < 65536:
            self.__port = int(port)
            return self.__port
        else:
            return None

    # open tcp socket to target plc
    def plc_port_open(self):                                                          # for tcp/ip connection
        for res in socket.getaddrinfo(self.__hostname, self.__port, socket.AF_UNSPEC, socket.SOCK_STREAM):
            af, sock_type, proto, canon_name, sa = res
            try:
                self.__sock = socket.socket(af, sock_type, proto)
            except socket.error:
                self.__sock = None
                continue
            try:
                self.__sock.settimeout(self.__timeout)
                self.__sock.connect(sa)
            except socket.error:
                self.__sock.close()
                self.__sock = None
                continue
            break

        if self.__sock is not None:
            return True
        else:
            self.__debug_msg('modbus connection error')
            return False

    # boolean check tcp port is avaible
    def plc_port_is_open(self):
        return self.__sock is not None

    # close using port
    def plc_close_port(self):
        if self.__sock:
            self.__sock.close()
            self.__sock = None
            return True
        else:
            return None

    # check plc data is avaible over bus
    def plc_data_readable(self):
        if self.__sock is None:
            return None
        if select.select([self.__sock], [], [], self.__timeout)[0]:
            return True
        else:
            self.__debug_msg('modbus timeout !!')
            self.plc_close_port()
            return None

    # data send from bus
    def plc_data_send(self, data):
        # check link
        if self.__sock is None:
            self.__debug_msg('modbus socket is not avaible closing socket')
            return None
        # send
        data_l = len(data)
        try:
            send_l = self.__sock.send(data)
        except socket.error:
            send_l = None

        # handle send error
        if (send_l is None) or (send_l != data_l):
            self.__debug_msg('modbus send error')
            self.plc_close_port()
            return None
        else:
            return send_l

    # receive data from bus
    def receive_data(self, max_size):
        # wait for read
        if not self.plc_data_readable():
            self.plc_close_port()
            return None
        # recv
        try:
            r_buffer = self.__sock.recv(max_size)
        except socket.error:
            r_buffer = None
        # handle recv error
        if not r_buffer:
            self.plc_close_port()
            return None
        return r_buffer

    # receive all buffer read
    def receive_all(self, size):
        r_buffer = bytes()
        while len(r_buffer) < size:
            r_packet = self.receive_data(size - len(r_buffer))
            if not r_packet:
                return None
            r_buffer += r_packet
        return r_buffer

    # sending main bus
    def send_main_bus(self, frame):
        if self.__auto_open and not self.plc_port_is_open():
            self.plc_port_open()
        bytes_send = self.plc_data_send(frame)
        if bytes_send:
            if self.__debug:
                self._pretty_dump('Tx', frame)
            return bytes_send
        else:
            return None

    # receive main bus
    def receive_main_bus(self):
        # check modbus tcp/rtu maybe can add serial connection later ?
        if self.__mode == const.MODBUS_TCP:
            rx_buffer = self.receive_all(7)
            if not (rx_buffer and len(rx_buffer) == 7):
                self.plc_close_port()
                return None
            rx_frame = rx_buffer
            (rx_hd_tr_id, rx_hd_pr_id, rx_hd_length, rx_hd_unit_id) = struct.unpack('>HHHB', rx_frame)

            # Check incoming MBAP header
            if not ((rx_hd_tr_id == self.__transaction_id) and
                    (rx_hd_pr_id == 0) and
                    (rx_hd_length < 256) and
                    (rx_hd_unit_id == self.__unit_id)):
                self.__debug_msg('MBAP header format error')
                if self.__debug:
                    rx_frame += self.receive_all(rx_hd_length - 1)
                    self._pretty_dump('Rx', rx_frame)
                self.plc_close_port()
                return None

            rx_buffer = self.receive_all(rx_hd_length - 1)
            if not (rx_buffer and
                    (len(rx_buffer) == rx_hd_length - 1) and (len(rx_buffer) >= 2)):
                self.__debug_msg('receive  frame body error')
                self.plc_close_port()
                return None
            rx_frame += rx_buffer
            if self.__debug:
                self._pretty_dump('Rx', rx_frame)
            # unpack struct
            rx_bd_fc = struct.unpack('B', rx_buffer[0:1])[0]
            f_body = rx_buffer[1:]

        # Exception handler
        if rx_bd_fc > 0x80:
            exp_code = struct.unpack('B', f_body[0:1])[0]
            self.__debug_msg('except (code ' + str(exp_code) + ')')
            return None
        else:
            return f_body

    # generate modbus package
    def generate_modbus_package(self, fc, body):
        f_body = struct.pack('B', fc) + body
        if self.__mode == const.MODBUS_TCP:
            # set transaction id
            self.__transaction_id = random.randint(0, 65535)
            tx_hd_pr_id = 0
            tx_hd_length = len(f_body) + 1
            f_mbap = struct.pack('>HHHB', self.__transaction_id, tx_hd_pr_id,
                                 tx_hd_length, self.__unit_id)
            return f_mbap + f_body

    def modbus_read_holding_registers(self, reg_addr, reg_nb=1):

        # Check errors
        if not (0 <= int(reg_addr) <= 65535):
            self.__debug_msg('read_holding_registers(): reg_addr out of range')
            return None
        if not (1 <= int(reg_nb) <= 125):
            self.__debug_msg('read_holding_registers(): reg_nb out of range')
            return None
        if (int(reg_addr) + int(reg_nb)) > 65536:
            self.__debug_msg('read_holding_registers(): read after ad 65535')
            return None

        # creating package
        tx_buffer = self.generate_modbus_package(const.MODBUS_READ_HOLDING_REGISTERS, struct.pack('>HH', reg_addr, reg_nb))

        # send request
        s_send = self.send_main_bus(tx_buffer)

        if not s_send:
            print("modbus error when sending data !! ")
            return None

        # Receive packages
        f_body = self.receive_main_bus()

        if not f_body:
            return None

        if len(f_body) < 2:
            self.__debug_msg('modbus package size under over standats when reading holding registers closing port!!')
            self.plc_close_port()
            return None

        rx_byte_count = struct.unpack('B', f_body[0:1])[0]
        # frame with regs value
        f_regs = f_body[1:]
        # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
        if not ((rx_byte_count >= 2 * reg_nb) and
                (rx_byte_count == len(f_regs))):
            self.__debug_msg('modbus rx byte count mismatch when reading holding registers!!')
            self.plc_close_port()
            return None

        # allocate a reg_nb size list
        registers = [None] * reg_nb

        # fill registers with all item
        for i, item in enumerate(registers):
            registers[i] = struct.unpack('>H', f_regs[i * 2:i * 2 + 2])[0]

        # return registers list
        return registers