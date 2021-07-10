"""Convenience module that creates instances of every instrument for you.

Every PSLab instrument can be imported and instantiated individually. However,
if you need to use several at once the ScienceLab class provides a convenient
collection.
"""
from typing import Iterable, List

import pslab.protocol as CP
from pslab.bus.i2c import I2CMaster
from pslab.bus.spi import SPIMaster
from pslab.instrument.logic_analyzer import LogicAnalyzer
from pslab.instrument.multimeter import Multimeter
from pslab.instrument.oscilloscope import Oscilloscope
from pslab.instrument.power_supply import PowerSupply
from pslab.instrument.waveform_generator import PWMGenerator, WaveformGenerator
from pslab.peripherals import NRF24L01
from pslab.serial_handler import SerialHandler


class ScienceLab(SerialHandler):
    """Aggregate interface for the PSLab's instruments.

    Attributes
    ----------
    logic_analyzer : pslab.LogicAnalyzer
    oscilloscope : pslab.Oscilloscope
    waveform_generator : pslab.WaveformGenerator
    pwm_generator : pslab.PWMGenerator
    multimeter : pslab.Multimeter
    power_supply : pslab.PowerSupply
    i2c : pslab.I2CMaster
    nrf : pslab.peripherals.NRF24L01
    """

    def __init__(
        self,
        port: str = None,
        baudrate: int = 1000000,
        timeout: float = 1.0,
    ):
        super().__init__(port, baudrate, timeout)
        self.logic_analyzer = LogicAnalyzer(device=self)
        self.oscilloscope = Oscilloscope(device=self)
        self.waveform_generator = WaveformGenerator(device=self)
        self.pwm_generator = PWMGenerator(device=self)
        self.multimeter = Multimeter(device=self)
        self.power_supply = PowerSupply(device=self)
        self.i2c = I2CMaster(device=self)
        self.spi = SPIMaster(device=self)
        self.nrf = NRF24L01(device=self)

        if "V6" in self.version:  # Set the built-in WS2812B to green :)
            self.rgb_led([0, 20, 0])

    @property
    def temperature(self):
        """float: Temperature of the MCU in degrees Celsius."""
        # TODO: Get rid of magic numbers.
        cs = 3
        V = self._get_ctmu_voltage(0b11110, cs, 0)

        if cs == 1:
            return (646 - V * 1000) / 1.92  # current source = 1
        elif cs == 2:
            return (701.5 - V * 1000) / 1.74  # current source = 2
        elif cs == 3:
            return (760 - V * 1000) / 1.56  # current source = 3

    def _get_ctmu_voltage(self, channel: int, current_range: int, tgen: bool = True):
        """Control the Charge Time Measurement Unit (CTMU).

        ctmu_voltage(5, 2) will activate a constant current source of 5.5 µA on
        CAP and then measure the voltage at the output.

        If a diode is used to connect CAP to ground, the forward voltage drop
        of the diode will be returned, e.g. 0.6 V for a 4148 diode.

        If a resistor is connected, Ohm's law will be followed within
        reasonable limits.

        Parameters
        ----------
        channel : int
            Pin number on which to generate a current and measure output
            voltage. Refer to the PIC24EP64GP204 datasheet for channel
            numbering.
        current_range : {0, 1, 2, 3}
            0 -> 550 µA
            1 -> 550 nA
            2 -> 5.5 µA
            3 -> 55 µA
        tgen : bool, optional
            Use Time Delay mode instead of Measurement mode. The default value
            is True.

        Returns
        -------
        voltage : float
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.GET_CTMU_VOLTAGE)
        self.send_byte((channel) | (current_range << 5) | (tgen << 7))
        raw_voltage = self.get_int() / 16  # 16*voltage across the current source
        self.get_ack()
        vmax = 3.3
        resolution = 12
        voltage = vmax * raw_voltage / (2 ** resolution - 1)
        return voltage

    def _start_ctmu(self, current_range: int, trim: int, tgen: int = 1):
        self.send_byte(CP.COMMON)
        self.send_byte(CP.START_CTMU)
        self.send_byte((current_range) | (tgen << 7))
        self.send_byte(trim)
        self.get_ack()

    def _stop_ctmu(self):
        self.send_byte(CP.COMMON)
        self.send_byte(CP.STOP_CTMU)
        self.get_ack()

    def reset(self):
        """Reset the device.

        Standalone mode will be enabled if an OLED is connected to the I2C
        port.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.RESTORE_STANDALONE)

    def rgb_led(self, colors: List, output: str = "RGB", order: str = "GRB"):
        """Set shade of a WS2812B RGB LED.

        Parameters
        ----------
        colors : list
            List of three values between 0-255, where each value is the
            intensity of red, green, and blue, respectively. When daisy
            chaining several LEDs, colors should be a list of three-value
            lists.
        output : {"RGB", "PGC", "SQ1"}, optional
            Pin on which to output the pulse train setting the LED color. The
            default value, "RGB", sets the color of the built-in WS2812B
            (PSLab v6 only).
        order : str, optional
            Color order of the connected LED as a three-letter string. The
            built-in LED has order "GRB", which is the default.

        Examples
        --------
        Set the built-in WS2812B to yellow.

        >>> import pslab
        >>> psl = pslab.ScienceLab()
        >>> psl.rgb_led([10, 10, 0])

        Set a chain of three RGB WS2812B connected to SQ1 to red, cyan, and
        magenta.

        >>> psl.rgb_led([[10,0,0],[0,10,10],[10,0,10]], output="SQ1", order="RGB")
        """
        if output == "RGB":
            pin = CP.SET_RGB1
        elif output == "PGC":
            pin = CP.SET_RGB2
        elif output == "SQ1":
            pin = CP.SET_RGB3
        else:
            raise ValueError(
                f"Invalid output: {output}. output must be 'RGB', 'PCG', or 'SQ1'."
            )

        if not isinstance(colors[0], Iterable):
            colors = [colors]

        if not all([len(color) == 3 for color in colors]):
            raise ValueError("Invalid color; each color list must have three values.")

        order = order.upper()

        if not sorted(order) == ["B", "G", "R"]:
            raise ValueError(
                f"Invalid order: {order}. order must contain 'R', 'G', and 'B'."
            )

        self.send_byte(CP.COMMON)
        self.send_byte(pin)
        self.send_byte(len(colors) * 3)

        for color in colors:
            self.send_byte(color[order.index("R")])
            self.send_byte(color[order.index("G")])
            self.send_byte(color[order.index("B")])

        self.get_ack()

    def _read_program_address(self, address: int):
        """Return the value stored at the specified address in program memory.

        Parameters
        ----------
        address : int
            Address to read from. Refer to PIC24EP64GP204 programming manual.

        Returns
        -------
        data : int
            16-bit wide value read from program memory.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.READ_PROGRAM_ADDRESS)
        self.send_int(address & 0xFFFF)
        self.send_int((address >> 16) & 0xFFFF)
        data = self.get_int()
        self.get_ack()
        return data

    def _device_id(self):
        a = self._read_program_address(0x800FF8)
        b = self._read_program_address(0x800FFA)
        c = self._read_program_address(0x800FFC)
        d = self._read_program_address(0x800FFE)
        val = d | (c << 16) | (b << 32) | (a << 48)
        return val

    def _read_data_address(self, address: int):
        """Return the value stored at the specified address in RAM.

        Parameters
        ----------
        address : int
            Address to read from. Refer to PIC24EP64GP204 programming manual.

        Returns
        -------
        data : int
            16-bit wide value read from RAM.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.READ_DATA_ADDRESS)
        self.send_int(address & 0xFFFF)
        data = self.get_int()
        self.get_ack()
        return data

    def _write_data_address(self, address: int, value: int):
        """Write a value to the specified address in RAM.

        Parameters
        ----------
        address : int
            Address to write to.  Refer to PIC24EP64GP204 programming manual.
        value : int
            Value to write to RAM.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.WRITE_DATA_ADDRESS)
        self.send_int(address & 0xFFFF)
        self.send_int(value)
        self.get_ack()

    def enable_uart_passthrough(self, baudrate: int, persist=False):
        """Relay all data received by the device to TXD/RXD.

        If a period > 0.5 seconds elapses between two transmit/receive events,
        the device resets and resumes normal mode. This timeout feature has
        been implemented in lieu of a hard reset option.

        Can be used to load programs into secondary microcontrollers with
        bootloaders such ATMEGA or ESP8266

        Parameters
        ----------
        baudrate : int
            Baudrate of the UART bus.
        persist : bool, optional
            If set to True, the device will stay in passthrough mode until the
            next power cycle. Otherwise(default scenario), the device will
            return to normal operation if no data is sent/received for a period
            greater than one second at a time.
        """
        self.send_byte(CP.PASSTHROUGHS)
        self.send_byte(CP.PASS_UART)
        self.send_byte(1 if persist else 0)
        self.send_int(int(round(((64e6 / baudrate) / 4) - 1)))

    def set_uart_baud(self, baudrate: int):
        """Set the baudrate of the UART bus.

        Parameters
        ----------
        baudrate : int
            Baudrate to set on the UART bus.
        """
        self.send_byte(CP.UART_2)
        self.send_byte(CP.SET_BAUD)
        self.send_int(int(round(((64e6 / baudrate) / 4) - 1)))
        self.get_ack()

    def write_uart(self, byte: int):
        """Write a single byte to the UART bus.

        Parameters
        ----------
        byte : int
            Byte value to write to the UART bus.
        """
        self.send_byte(CP.UART_2)
        self.send_byte(CP.SEND_BYTE)
        self.send_byte(byte)
        self.get_ack()

    def read_uart(self):
        """Read a single byte from the UART bus.

        Returns
        -------
        byte : int
            Byte value read from the UART bus."""
        self.send_byte(CP.UART_2)
        self.send_byte(CP.READ_BYTE)
        return self.get_byte()

    def read_uart_status(self):
        """Return available bytes in UART buffer.

        Returns
        -------
        status : int
        """
        self.send_byte(CP.UART_2)
        self.send_byte(CP.READ_UART2_STATUS)
        return self.get_byte()

    def read_log(self):
        """Read hardware debug log.

        Returns
        -------
        log : bytes
            Bytes read from the hardware debug log.
        """
        self.send_byte(CP.COMMON)
        self.send_byte(CP.READ_LOG)
        log = self.interface.readline().strip()
        self.get_ack()
        return log
