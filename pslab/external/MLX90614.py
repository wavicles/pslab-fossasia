from pslab.bus import I2CSlave

class MLX90614(I2CSlave):
    _ADDRESS = 0x5A
    _OBJADDR = 0x07
    _AMBADDR = 0x06
    NUMPLOTS = 1
    PLOTNAMES = ['Temp']
    name = 'PIR temperature'

    def __init__(self):
        super().__init__(self._ADDRESS)

        self.source = self._OBJADDR

        self.name = 'Passive IR temperature sensor'
        self.params = {'readReg': {'dataType': 'integer', 'min': 0, 'max': 0x20, 'prefix': 'Addr: '},
                       'select_source': ['object temperature', 'ambient temperature']}

        # try:
        #     print('switching baud to 100k')
        #     self.I2C.configI2C(100e3)
        # except Exception as e:
        #     print('FAILED TO CHANGE BAUD RATE', e.message)

    def select_source(self, source):
        if source == 'object temperature':
            self.source = self._OBJADDR
        elif source == 'ambient temperature':
            self.source = self._AMBADDR

    def readReg(self, addr):
        x = self.getVals(addr, 2)
        print(hex(addr), hex(x[0] | (x[1] << 8)))

    def getVals(self, addr, numbytes):
        vals = self.read(numbytes, addr)
        return vals

    def getRaw(self):
        vals = self.getVals(self.source, 3)
        if vals:
            if len(vals) == 3:
                return [((((vals[1] & 0x007f) << 8) + vals[0]) * 0.02) - 0.01 - 273.15]
            else:
                return False
        else:
            return False

    def getObjectTemperature(self):
        self.source = self._OBJADDR
        val = self.getRaw()
        if val:
            return val[0]
        else:
            return False

    def getAmbientTemperature(self):
        self.source = self._AMBADDR
        val = self.getRaw()
        if val:
            return val[0]
        else:
            return False
