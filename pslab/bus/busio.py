"""Circuitpython's busio compatibility layer for pslab-python.

This module emulates the CircuitPython's busio API for devices or hosts running
CPython or MicroPython using pslab-python.
This helps to access many sensors using Adafruit's drivers via PSLab board.

Notes
-----
Documentation:
    https://circuitpython.readthedocs.io/en/6.3.x/shared-bindings/busio/index.html

Examples
--------
Get humidity from Si7021 temperature and humidity sensor using adafruit_si7021 module.

>>> import adafruit_si7021
>>> from pslab.bus import busio   # import board, busio
>>> i2c = busio.I2C()   # i2c = busio.I2C(board.SCL, board.SDA)
>>> sensor = adafruit_si7021.SI7021(i2c)
>>> print(sensor.relative_humidity)

Get gyro reading from BNO055 using adafruit_bno055, board(just a wrapper for busio).

>>> import adafruit_bno055
>>> from pslab.bus import busio   # import board
>>> i2c = busio.I2C()   # i2c = board.I2C()
>>> sensor = adafruit_bno055.BNO055_I2C(i2c)
>>> print(sensor.gyro)
"""

from typing import List, Union

from pslab.bus.i2c import _I2CPrimitive
from pslab.serial_handler import SerialHandler

__all__ = "I2C"
ReadableBuffer = Union[bytes, bytearray, memoryview]
WriteableBuffer = Union[bytearray, memoryview]


class I2C(_I2CPrimitive):
    """Busio I2C Class for CircuitPython Compatibility.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    frequency : float, optional
        Frequency of SCL in Hz.
    """

    def __init__(self, device: SerialHandler = None, frequency: int = 125e3):
        # 125 kHz is as low as the PSLab can go.
        super().__init__(device)
        self._init()
        self._configure(frequency)

    def deinit(self) -> None:
        """Just a dummy method."""
        pass

    def __enter__(self):
        """Just a dummy context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Call :meth:`deinit` on context exit."""
        self.deinit()

    def scan(self) -> List[int]:
        """Scan all I2C addresses between 0x08 and 0x77 inclusive.

        Returns
        -------
        addrs : list of int
            List of 7-bit addresses on which slave devices replied.
        """
        return self._scan(0x08, 0x77)

    def try_lock(self) -> bool:  # pylint: disable=no-self-use
        """Just a dummy method."""
        return True

    def unlock(self) -> None:
        """Just a dummy method."""
        pass

    def readfrom_into(
        self, address: int, buffer: WriteableBuffer, *, start: int = 0, end: int = None
    ) -> None:
        """Read from a device at specified address into a buffer.

        Parameters
        ----------
        address : int
            7-bit I2C device address.
        buffer : bytearray or memoryview
            buffer to write into.
        start : int
            Index to start writing at.
        end : int
            Index to write up to but not include. Defaults to length of `buffer`.
        """
        end = len(buffer) if end is None else end
        bytes_to_read = end - start
        self._start(address, 1)
        buffer[start:end] = self._read(bytes_to_read)
        self._stop()

    def writeto(
        self,
        address: int,
        buffer: ReadableBuffer,
        *,
        start: int = 0,
        end: int = None,
        stop: bool = True,
    ) -> None:
        """Write to a device at specified address from a buffer.

        Parameters
        ----------
        address : int
            7-bit I2C device address.
        buffer : bytes or bytearray or memoryview
            buffer containing the bytes to write.
        start : int
            Index to start writing from.
        end : int
            Index to read up to but not include. Defaults to length of `buffer`.
        stop : bool
            Enable to transmit a stop bit. Defaults to True.
        """
        end = len(buffer) if end is None else end

        if stop:
            self._write_bulk(address, buffer[start:end])
        else:
            self._start(address, 0)
            self._send(buffer[start:end])

    def writeto_then_readfrom(
        self,
        address: int,
        buffer_out: ReadableBuffer,
        buffer_in: WriteableBuffer,
        *,
        out_start: int = 0,
        out_end: int = None,
        in_start: int = 0,
        in_end: int = None,
    ):
        """Write to then read from a device at specified address.

        Parameters
        ----------
        address : int
            7-bit I2C device address.
        out_buffer : bytes or bytearray or memoryview
            buffer containing the bytes to write.
        in_buffer : bytearray or memoryview
            buffer to write into.
        out_start : int
            Index to start writing from.
        out_end : int
            Index to read up to but not include. Defaults to length of `out_buffer`.
        in_start : int
            Index to start writing at.
        in_end : int
            Index to write up to but not include. Defaults to length of `in_buffer`.
        """
        out_end = len(buffer_out) if out_end is None else out_end
        in_end = len(buffer_in) if in_end is None else in_end
        bytes_to_read = in_end - in_start
        self._start(address, 0)
        self._send(buffer_out[out_start:out_end])
        self._restart(address, 1)
        buffer_in[in_start:in_end] = self._read(bytes_to_read)
        self._stop()
