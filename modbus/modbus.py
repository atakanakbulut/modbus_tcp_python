# Defination for modbus protocol tcp/ip client and data
# Implemented just for read holding registers address will start 40.000
# http://modbus.org/docs/PI_MBUS_300.pdf for more info

# includes consts
from . import modbusdefination as const

# standart packages
import struct
import socket
import random
import select

class modbus:

    def __init__(self, host=None, port=None, unit_id=None, timeout=None,
                 debug=None, auto_open=None, auto_close=None):

        self.__hostname = 'localhost'
        self.__port = const.MODBUS_DEFAULT_PORT
        self.__unit_id = 1
        self.__timeout = 30.0                # socket timeout
        self.__debug = False                 # debug trace on/off
        self.__auto_open = False             # auto TCP connect
        self.__auto_close = False            # auto TCP close
        self.__mode = const.MODBUS_DEFAULT_TCP_IP       # default is Modbus/TCP
        self.__sock = None                   # socket handle
        self.__hd_tr_id = 0                  # store transaction ID
        self.__last_error = const.MB_NO_ERR  # last error code
        self.__last_except = 0               # last expect code

        print("constructor called succesfull")


    def host(self, hostname=None):
        if (hostname is None) or (hostname == self.__hostname):
            return self.__hostname
        # when hostname change ensure old socket is close
        self.close()
        # IPv4 ?
        try:
            socket.inet_pton(socket.AF_INET, hostname)
            self.__hostname = hostname
            return self.__hostname
        except socket.error:
            pass

    def port(self, port=None):
        if (port is None) or (port == self.__port):
            return self.__port
        # when port change ensure old socket is close
        self.close()
        # valid port ?
        if 0 < int(port) < 65536:
            self.__port = int(port)
            return self.__port
        else:
            return None

    def open(self):
        if self.is_open():
            self.close()
        for res in socket.getaddrinfo(self.__hostname, self.__port,
                                      socket.AF_UNSPEC, socket.SOCK_STREAM):
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
        # check connect status
        if self.__sock is not None:
            return True
        else:
            self.__last_error = const.MB_CONNECT_ERR
            self.__debug_msg('connect error')
            return False

    def is_open(self):
        return self.__sock is not None

    def close(self):
        if self.__sock:
            self.__sock.close()
            self.__sock = None
            return True
        else:
            return None

    def read_holding_registers(self, reg_addr, reg_nb=1):
        # check params
        if not (0 <= int(reg_addr) <= 65535):
            self.__debug_msg('read_holding_registers(): reg_addr out of range')
            return None
        if not (1 <= int(reg_nb) <= 125):
            self.__debug_msg('read_holding_registers(): reg_nb out of range')
            return None
        if (int(reg_addr) + int(reg_nb)) > 65536:
            self.__debug_msg('read_holding_registers(): read after ad 65535')
            return None
        # build frame
        tx_buffer = self._mbus_frame(const.MODBUS_READ_HOLDING_REGISTERS, struct.pack('>HH', reg_addr, reg_nb))
        # send request
        s_send = self._send_mbus(tx_buffer)
        # check error
        if not s_send:
            return None
        # receive
        f_body = self._recv_mbus()
        # check error
        if not f_body:
            return None
        # check min frame body size
        if len(f_body) < 2:
            self.__last_error = const.MB_RECV_ERR
            self.__debug_msg('read_holding_registers(): rx frame under min size')
            self.close()
            return None
        # extract field "byte count"
        rx_byte_count = struct.unpack('B', f_body[0:1])[0]
        # frame with regs value
        f_regs = f_body[1:]
        # check rx_byte_count: buffer size must be consistent and have at least the requested number of registers
        if not ((rx_byte_count >= 2 * reg_nb) and
                (rx_byte_count == len(f_regs))):
            self.__last_error = const.MB_RECV_ERR
            self.__debug_msg('read_holding_registers(): rx byte count mismatch')
            self.close()
            return None
        # allocate a reg_nb size list
        registers = [None] * reg_nb
        # fill registers list with register items
        for i, item in enumerate(registers):
            registers[i] = struct.unpack('>H', f_regs[i * 2:i * 2 + 2])[0]
        # return registers list
        return registers

    def __debug_msg(self, msg):
        if self.__debug:
            print(msg)

    def _mbus_frame(self, fc, body):
        f_body = struct.pack('B', fc) + body
        # modbus/TCP
        if self.__mode == const.MODBUS_DEFAULT_TCP_IP:
            # build frame ModBus Application Protocol header (mbap)
            self.__hd_tr_id = random.randint(0, 65535)
            tx_hd_pr_id = 0
            tx_hd_length = len(f_body) + 1
            f_mbap = struct.pack('>HHHB', self.__hd_tr_id, tx_hd_pr_id,
                                 tx_hd_length, self.__unit_id)
            return f_mbap + f_body

    def _send_mbus(self, frame):
        if self.__auto_open and not self.is_open():
            self.open()
        # send request
        bytes_send = self._send(frame)
        if bytes_send:
            if self.__debug:
                self._pretty_dump('Tx', frame)
            return bytes_send
        else:
            return None

    def _recv_mbus(self):
        if self.__mode == const.MODBUS_DEFAULT_TCP_IP:
            # 7 bytes header (mbap)
            rx_buffer = self._recv_all(7)
            # check recv
            if not (rx_buffer and len(rx_buffer) == 7):
                self.__last_error = const.MB_RECV_ERR
                self.__debug_msg('_recv MBAP error')
                self.close()
                return None
            rx_frame = rx_buffer
            # decode header
            (rx_hd_tr_id, rx_hd_pr_id,
             rx_hd_length, rx_hd_unit_id) = struct.unpack('>HHHB', rx_frame)
            # check header
            if not ((rx_hd_tr_id == self.__hd_tr_id) and
                    (rx_hd_pr_id == 0) and
                    (rx_hd_length < 256) and
                    (rx_hd_unit_id == self.__unit_id)):
                self.__last_error = const.MB_RECV_ERR
                self.__debug_msg('MBAP format error')
                if self.__debug:
                    rx_frame += self._recv_all(rx_hd_length - 1)
                    self._pretty_dump('Rx', rx_frame)
                self.close()
                return None
            # end of frame
            rx_buffer = self._recv_all(rx_hd_length - 1)
            if not (rx_buffer and
                    (len(rx_buffer) == rx_hd_length - 1) and
                    (len(rx_buffer) >= 2)):
                self.__last_error = const.MB_RECV_ERR
                self.__debug_msg('_recv frame body error')
                self.close()
                return None
            rx_frame += rx_buffer
            # dump frame
            if self.__debug:
                self._pretty_dump('Rx', rx_frame)
            # body decode
            rx_bd_fc = struct.unpack('B', rx_buffer[0:1])[0]
            f_body = rx_buffer[1:]


    def _pretty_dump(self, label, data):
        # split data string items to a list of hex value
        dump = ['%02X' % c for c in bytearray(data)]
        # format for TCP or RTU
        if self.__mode == const.MODBUS_DEFAULT_TCP_IP:
            if len(dump) > 6:
                # [MBAP] ...
                dump[0] = '[' + dump[0]
                dump[6] += ']'
        print(label)
        s = ''
        for i in dump:
            s += i + ' '
        print(s)

    def _send(self, data):
        if self.__sock is None:
            self.__debug_msg('call _send on close socket')
            return None
        # send
        data_l = len(data)
        try:
            send_l = self.__sock.send(data)
            print("sent")
        except socket.error:
            send_l = None
        # handle send error
        if (send_l is None) or (send_l != data_l):
            self.__last_error = const.MB_SEND_ERR
            self.__debug_msg('_send error')
            self.close()
            return None
        else:
            return send_l

    def _recv_all(self, size):
        r_buffer = bytes()
        while len(r_buffer) < size:
            r_packet = self._recv(size - len(r_buffer))
            if not r_packet:
                return None
            r_buffer += r_packet
        return r_buffer

    def _recv(self, max_size):
        # wait for read
        if not self._can_read():
            self.close()
            return None
        # recv
        try:
            r_buffer = self.__sock.recv(max_size)
        except socket.error:
            r_buffer = None
        # handle recv error
        if not r_buffer:
            self.__last_error = const.MB_RECV_ERR
            self.__debug_msg('_recv error')
            self.close()
            return None
        return r_buffer

    def _can_read(self):
        if self.__sock is None:
            return None
        if select.select([self.__sock], [], [], self.__timeout)[0]:
            return True
        else:
            self.__last_error = const.MB_TIMEOUT_ERR
            self.__debug_msg('timeout error')
            self.close()
            return None