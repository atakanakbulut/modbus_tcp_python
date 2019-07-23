
from modbus.modbus import modbus
import time
import datetime

SERVER_HOST = "10.1.15.49"
SERVER_PORT = 502

c = ModbusClient()
c.set_plc_address(SERVER_HOST)
c.set_plc_port(SERVER_PORT)

while True:
    if not c.plc_port_is_open():
        if not c.plc_port_open():
            print("unable to connect to "+SERVER_HOST+":"+str(SERVER_PORT))
    if c.plc_port_is_open():
        regs = c.modbus_read_holding_registers(100, 48)
        if regs:
            print("Received data #  "+str(regs))
    time.sleep(1)


