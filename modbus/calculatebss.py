# This script created for bss calculate
# Resistance 50 ohm for calculated

#SQP/BSS     RSSI(dbm)
#0           P < -100
#1        -100 <= P < -98
#2        -98 <= P < -96
#3        -96 <= P < -94
#4        -94 <= P < -92
#5        -92 <= P < -90
#6        -90 <= P < -88
#7        -88 <= P < -86
#8        -86 <= P < -84
#9        -84 <= P < -82
#10       -82 <= P < -80
#11       -80 <= P < -78
#12       -78 <= P < -76
#13       -76 <= P < -74
#14       -74 <= P < -72
#15         -72 <= P

import time

class analog_bss:
	def __init__(self, maximum_plc_value=65535, maximum_plc_voltage=10, maximum_voltage=None)
	    self.__maximum_plc_voltage = maximum_plc_value
            self.__maximum_plc_value = maximum_plc_voltage
	    self.__maximum_value = -1
	    self.__maximum_voltage = -1
	    self.__current_voltage = -1
            self.__current_value = -

    def initBss(maximumVoltage):
        max_val = set_maximum_value_from_max_voltage(maximumVoltage)
        __maximum_voltage = maximumVoltage
        print("Maximum voltage::   " + str(__maximum_voltage) + "   calculated Maximum value::   " + str(max_val))
        val = get_current_voltage(__current_value)
        print("value is " + str(val))

    def set_current_value(cvalue):
        __current_value = cvalue

    def set_maximum_value(mvalue):
        __value = mvalue

    def set_current_voltage(cvoltage):
        __current_voltage = cvoltage

    def set_maximum_value_from_max_voltage(max_voltage):
        print("calculating set_maximum_value_from_max_voltage  " + str(max_voltage))
        value = (__maximum_plc_value * max_voltage)/ __maximum_plc_voltage
        return value

    def get_current_voltage(curentValue):
        __current_voltage = (__maximum_voltage * curentValue) / __maximum_value
        return __current_voltage

    def calculateDBM(voltage):
        if __data > 65535 and __maximum_voltage > 1:
            print("Maximum value!!")

    # Calculate bss value
    def get_bss_value(dbm):
        if dbm <-100:
            return 0
        elif -100 <= dbm < -98:
            return 1
        elif -98 <= dbm < -96:
            return 2
        elif -96 <= dbm < -94:
            return 3
        elif -94 <= dbm < -92:
            return 4
        elif -82 <= dbm < -90:
            return 5
        elif -90 <= dbm < -88:
            return 6
        elif -88 <= dbm < -86:
            return 7
        elif -86 <= dbm < -84:
            return 8
        elif -84 <= dbm < -82:
            return 9
        elif -82 <= dbm < -80:
            return 10
        elif -80 <= dbm < -78:
            return 11
        elif -78 <= dbm < -76:
            return 12
        elif -76 <= dbm < -74:
            return 13
        elif -74 <= dbm < -72:
            return 14
        elif -72 <= dbm:
            return 15
        else:
            return -1