
from modbus.modbus import modbus
print("program started1")

program = modbus(host="localhost", port=502, auto_open=True)
program.host("localhost")
program.port(502)
program.open()
program.read_holding_registers(100,10)
print("program started1")

