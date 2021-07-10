"""Control the PSLab's SPI bus and devices connected on the bus.

Examples
--------
Set SPI bus speed to 200 kbit/s:

>>> from pslab.bus.spi import SPIMaster, SPISlave
>>> bus = SPIMaster()
>>> bus.set_parameters(primary_prescaler=0, secondary_prescaler=3) # 64e6/(64*5)

Set SPI bus to mode 3 (1,1):

>>> bus.set_parameters(0, 3, CKE=0, CKP=1)

Transfer a random byte over SPI:

>>> slave = SPISlave()
>>> slave.transfer8(0x55)
0
"""

import sys
from typing import List, Tuple

import pslab.protocol as CP
from pslab.serial_handler import SerialHandler

__all__ = (
    "SPIMaster",
    "SPISlave",
)
# Default values, refer pslab-firmware.
_PPRE = 0
_SPRE = 2
# SPI mode 0 (0,0)
_CKP = 0  # Clock Polarity 0
_CKE = 1  # Clock Phase 0 | Clock Edge 1
_SMP = 1


class classmethod_(classmethod):
    """Support chaining classmethod and property."""

    def __init__(self, f):
        self.f = f
        super().__init__(f)

    def __get__(self, obj, cls=None):
        # classmethod() to support chained decorators; new in python 3.9.
        if sys.version_info < (3, 9) and isinstance(self.f, property):
            return self.f.__get__(cls)
        else:
            return super().__get__(obj, cls)


class _SPIPrimitive:
    """SPI primitive commands.

    Handles all the SPI subcommands coded in pslab-firmware.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    """

    _TRANSFER_COMMANDS_MAP = {
        8: CP.SEND_SPI8,
        16: CP.SEND_SPI16,
    }  # PSLab only supports 8 and 16 bits.
    _PPRE_MAP = [64, 16, 4, 1]
    _SPRE_MAP = [8, 7, 6, 5, 4, 3, 2, 1]

    _primary_prescaler = _PPRE
    _secondary_prescaler = _SPRE
    _clock_polarity = _CKP  # Clock Polarity bit.
    _clock_edge = _CKE  # Clock Edge Select bit (inverse of Clock Phase bit).
    _smp = _SMP  # Data Input Sample Phase bit.

    def __init__(self, device: SerialHandler = None):
        self._device = device if device is not None else SerialHandler()

    @classmethod_
    @property
    def _frequency(cls) -> float:
        ppre = cls._PPRE_MAP[cls._primary_prescaler]
        spre = cls._SPRE_MAP[cls._secondary_prescaler]

        return CP.CLOCK_RATE / (ppre * spre)

    @classmethod_
    @property
    def _clock_phase(cls) -> int:
        return (cls._clock_edge ^ 1) & 1

    @staticmethod
    def _save_config(
        primary_prescaler: int,
        secondary_prescaler: int,
        CKE: int,
        CKP: int,
        SMP: int,
    ):
        """Save the SPI parameters.

        See Also
        --------
        _set_parameters : To set SPI parameters.
        """
        _SPIPrimitive._primary_prescaler = primary_prescaler
        _SPIPrimitive._secondary_prescaler = secondary_prescaler
        _SPIPrimitive._clock_edge = CKE
        _SPIPrimitive._clock_polarity = CKP
        _SPIPrimitive._smp = SMP

    def _set_parameters(
        self,
        primary_prescaler: int,
        secondary_prescaler: int,
        CKE: int,
        CKP: int,
        SMP: int,
    ):
        """Set SPI parameters.

        It is a primitive SPI method, prefered to use :meth:`SPIMaster.set_parameters`.

        Parameters
        ----------
        primary_prescaler : {0, 1, 2, 3}
            Primary Prescaler for system clock :const:`CP.CLOCK_RATE`Hz.
            (0,1,2,3) -> (64:1,16:1,4:1,1:1).
        secondary_prescaler : {0, 1, 2, 3, 4, 5, 6, 7}
            Secondary prescaler (0,1,..7) -> (8:1,7:1,..1:1).
        CKE : {0, 1}
            SPIx Clock Edge Select bit. Serial output data changes on transition
            {0: from Idle clock state to active clock state,
             1: from active clock state to Idle clock state}.
        CKP : {0, 1}
            Clock Polarity Select bit.
            Idle state for clock is a {0: low, 1: high} level.
        SMP : {0, 1}
            Input data is sampled at the {0: end, 1: middle} of data output time.

        Raises
        ------
        ValueError
            If any one of arguments is not in its shown range.
        """
        error_message = []
        if primary_prescaler not in range(0, 4):
            error_message.append("Primary Prescaler must be in 2-bits.")
        if secondary_prescaler not in range(0, 8):
            error_message.append("Secondary Prescale must be in 3-bits.")
        if CKE not in (0, 1):
            error_message.append("Clock Edge Select must be a bit.")
        if CKP not in (0, 1):
            error_message.append("Clock Polarity must be a bit.")
        if SMP not in (0, 1):
            error_message.append("SMP must be a bit.")
        if error_message:
            raise ValueError("\n".join(error_message))

        self._device.send_byte(CP.SPI_HEADER)
        self._device.send_byte(CP.SET_SPI_PARAMETERS)
        # 0Bhgfedcba - > <g>: modebit CKP,<f>: modebit CKE, <ed>:primary prescaler,
        #                <cba>:secondary prescaler
        self._device.send_byte(
            secondary_prescaler
            | (primary_prescaler << 3)
            | (CKE << 5)
            | (CKP << 6)
            | (SMP << 7)
        )
        self._device.get_ack()
        self._save_config(primary_prescaler, secondary_prescaler, CKE, CKP, SMP)

    @classmethod
    def _get_parameters(cls) -> Tuple[int]:
        """Get SPI parameters.

        Returns
        -------
        primary_prescaler : {0, 1, 2, 3}
            Primary Prescaler for system clock :const:`CP.CLOCK_RATE`Hz.
            (0,1,2,3) -> (64:1,16:1,4:1,1:1).
        secondary_prescaler : {0, 1, 2, 3, 4, 5, 6, 7}
            Secondary prescaler (0,1,..7) -> (8:1,7:1,..1:1).
        CKE : {0, 1}
            SPIx Clock Edge Select bit. Serial output data changes on transition
            {0: from Idle clock state to active clock state,
             1: from active clock state to Idle clock state}.
        CKP : {0, 1}
            Clock Polarity Select bit.
            Idle state for clock is a {0: low, 1: high} level.
        SMP : {0, 1}
            Input data is sampled at the {0: end, 1: middle} of data output time.
        """
        return (
            cls._primary_prescaler,
            cls._secondary_prescaler,
            cls._clock_edge,
            cls._clock_polarity,
            cls._smp,
        )

    def _start(self):
        """Select SPI channel to enable.

        Basically sets the relevant chip select pin to LOW.

        External ChipSelect pins:
            version < 5 : {6, 7} # RC5, RC4 (dropped support)
            version == 5 : {} (don't have any external CS pins)
            version == 6 : {7} # RC4
        """
        self._device.send_byte(CP.SPI_HEADER)
        self._device.send_byte(CP.START_SPI)
        self._device.send_byte(7)  # SPI.CS v6
        # No ACK because `RESPONSE == DO_NOT_BOTHER` in firmware.

    def _stop(self):
        """Select SPI channel to disable.

        Sets the relevant chip select pin to HIGH.
        """
        self._device.send_byte(CP.SPI_HEADER)
        self._device.send_byte(CP.STOP_SPI)
        self._device.send_byte(7)  # SPI.CS v6

    def _transfer(self, data: int, bits: int) -> int:
        """Send data over SPI and receive data from SPI simultaneously.

        Relevent SPI channel need to be enabled first.

        It is a primitive SPI method, prefered to use :meth:`SPISlave.transfer8`
        and :meth:`SPISlave.transfer16`.

        Parameters
        ----------
        data : int
            Data to transmit.
        bits : int
            The number of bits per word.

        Returns
        -------
        data_in : int
            Data returned by slave device.

        Raises
        ------
        ValueError
            If given bits per word not supported by PSLab board.
        """
        command = self._TRANSFER_COMMANDS_MAP.get(bits)

        if not command:
            raise ValueError(
                f"PSLab only supports {set(self._TRANSFER_COMMANDS_MAP.keys())}"
                + " bits per word."
            )

        self._device.send_byte(CP.SPI_HEADER)
        self._device.send_byte(command)
        self._device.send_byte(data)
        data_in = self._device.get_byte()
        self._device.get_ack()

        return data_in

    def _transfer_bulk(self, data: List[int], bits: int) -> List[int]:
        """Transfer data array over SPI.

        Relevent SPI channel need to be enabled first.

        It is a primitive SPI method, prefered to use :meth:`SPISlave.transfer8_bulk`
        and :meth:`SPISlave.transfer16_bulk`.

        Parameters
        ----------
        data : list of int
            List of data to transmit.
        bits : int
            The number of bits per word.

        Returns
        -------
        data_in : list of int
            List of data returned by slave device.

        Raises
        ------
        ValueError
            If given bits per word not supported by PSLab board.
        """
        data_in = []

        for a in data:
            data_in.append(self._transfer(a, bits))

        return data_in

    def _read(self, bits: int) -> int:
        """Read data while transmit zero.

        Relevent SPI channel need to be enabled first.

        It is a primitive SPI method, prefered to use :meth:`SPISlave.read8`
        and :meth:`SPISlave.read16`.

        Parameters
        ----------
        bits : int
            The number of bits per word.

        Returns
        -------
        int
            Data returned by slave device.

        Raises
        ------
        ValueError
            If given bits per word not supported by PSLab board.
        """
        return self._transfer(0, bits)

    def _read_bulk(self, data_to_read: int, bits: int) -> List[int]:
        """Read data array while transmitting zeros.

        Relevent SPI channel need to be enabled first.

        It is a primitive SPI method, prefered to use :meth:`SPISlave.read8_bulk`
        and :meth:`SPISlave.read16_bulk`.

        Parameters
        ----------
        data_to_read : int
            Number of data to read from slave device.
        bits : int
            The number of bits per word.

        Returns
        -------
        list of int
            List of data returned by slave device.

        Raises
        ------
        ValueError
            If given bits per word not supported by PSLab board.
        """
        return self._transfer_bulk([0] * data_to_read, bits)

    def _write(self, data: int, bits: int):
        """Send data over SPI.

        Relevent SPI channel need to be enabled first.

        It is a primitive SPI method, prefered to use :meth:`SPISlave.write8`
        and :meth:`SPISlave.write16`.

        Parameters
        ----------
        data : int
            Data to transmit.
        bits : int
            The number of bits per word.

        Raises
        ------
        ValueError
            If given bits per word not supported by PSLab board.
        """
        self._transfer(data, bits)

    def _write_bulk(self, data: List[int], bits: int):
        """Send data array over SPI.

        Relevent SPI channel need to be enabled first.

        It is a primitive SPI method, prefered to use :meth:`SPISlave.write8_bulk`
        and :meth:`SPISlave.write16_bulk`.

        Parameters
        ----------
        data : list of int
            List of data to transmit.
        bits : int
            The number of bits per word.

        Raises
        ------
        ValueError
            If given bits per word not supported by PSLab board.
        """
        self._transfer_bulk(data, bits)


class SPIMaster(_SPIPrimitive):
    """SPI bus controller.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    """

    def __init__(self, device: SerialHandler = None):
        super().__init__(device)
        # Reset config
        self.set_parameters()

    def set_parameters(
        self,
        primary_prescaler: int = _PPRE,
        secondary_prescaler: int = _SPRE,
        CKE: int = _CKE,
        CKP: int = _CKP,
        SMP: int = _SMP,
    ):
        """Set SPI parameters.

        Parameters
        ----------
        primary_prescaler : {0, 1, 2, 3}
            Primary Prescaler for system clock :const:`CP.CLOCK_RATE`Hz.
            (0,1,2,3) -> (64:1,16:1,4:1,1:1).
        secondary_prescaler : {0, 1, 2, 3, 4, 5, 6, 7}
            Secondary prescaler (0,1,..7) -> (8:1,7:1,..1:1).
        CKE : {0, 1}
            SPIx Clock Edge Select bit. Serial output data changes on transition
            {0: from Idle clock state to active clock state,
             1: from active clock state to Idle clock state}.
        CKP : {0, 1}
            Clock Polarity Select bit.
            Idle state for clock is a {0: low, 1: high} level.
        SMP : {0, 1}
            Input data is sampled at the {0: end, 1: middle} of data output time.

        Raises
        ------
        ValueError
            If any one of arguments is not in its shown range.
        """
        self._set_parameters(primary_prescaler, secondary_prescaler, CKE, CKP, SMP)

    @classmethod
    def get_parameters(cls) -> Tuple[int]:
        """Get SPI parameters.

        Returns
        -------
        primary_prescaler : {0, 1, 2, 3}
            Primary Prescaler for system clock :const:`CP.CLOCK_RATE`Hz.
            (0,1,2,3) -> (64:1,16:1,4:1,1:1).
        secondary_prescaler : {0, 1, 2, 3, 4, 5, 6, 7}
            Secondary prescaler (0,1,..7) -> (8:1,7:1,..1:1).
        CKE : {0, 1}
            SPIx Clock Edge Select bit. Serial output data changes on transition
            {0: from Idle clock state to active clock state,
             1: from active clock state to Idle clock state}.
        CKP : {0, 1}
            Clock Polarity Select bit.
            Idle state for clock is a {0: low, 1: high} level.
        SMP : {0, 1}
            Input data is sampled at the {0: end, 1: middle} of data output time.
        """
        return cls._get_parameters()


class SPISlave(_SPIPrimitive):
    """SPI slave device.

    Parameters
    ----------
    device : :class:`SerialHandler`, optional
        Serial connection to PSLab device. If not provided, a new one will be
        created.
    """

    def __init__(self, device: SerialHandler = None):
        super().__init__(device)

    def transfer8(self, data: int) -> int:
        """Send 8-bit data over SPI and receive 8-bit data from SPI simultaneously.

        Parameters
        ----------
        data : int
            Data to transmit.

        Returns
        -------
        data_in : int
            Data returned by slave device.
        """
        self._start()
        data_in = self._transfer(data, 8)
        self._stop()

        return data_in

    def transfer16(self, data: int) -> int:
        """Send 16-bit data over SPI and receive 16-bit data from SPI simultaneously.

        Parameters
        ----------
        data : int
            Data to transmit.

        Returns
        -------
        data_in : int
            Data returned by slave device.
        """
        self._start()
        data_in = self._transfer(data, 16)
        self._stop()

        return data_in

    def transfer8_bulk(self, data: List[int]) -> List[int]:
        """Transfer 8-bit data array over SPI.

        Parameters
        ----------
        data : list of int
            List of 8-bit data to transmit.

        Returns
        -------
        data_in : list of int
            List of 8-bit data returned by slave device.
        """
        self._start()
        data_in = self._transfer_bulk(data, 8)
        self._stop()

        return data_in

    def transfer16_bulk(self, data: List[int]) -> List[int]:
        """Transfer 16-bit data array over SPI.

        Parameters
        ----------
        data : list of int
            List of 16-bit data to transmit.

        Returns
        -------
        data_in : list of int
            List of 16-bit data returned by slave device.
        """
        self._start()
        data_in = self._transfer_bulk(data, 16)
        self._stop()

        return data_in

    def read8(self) -> int:
        """Read 8-bit data while transmit zero.

        Returns
        -------
        int
            Data returned by slave device.
        """
        self._start()
        data_in = self._read(8)
        self._stop()

        return data_in

    def read16(self) -> int:
        """Read 16-bit data while transmit zero.

        Returns
        -------
        int
            Data returned by slave device.
        """
        self._start()
        data_in = self._read(16)
        self._stop()

        return data_in

    def read8_bulk(self, data_to_read: int) -> List[int]:
        """Read 8-bit data array while transmitting zeros.

        Parameters
        ----------
        data_to_read : int
            Number of 8-bit data to read from slave device.

        Returns
        -------
        list of int
            List of 8-bit data returned by slave device.
        """
        self._start()
        data_in = self._read_bulk(data_to_read, 8)
        self._stop()

        return data_in

    def read16_bulk(self, data_to_read: int) -> List[int]:
        """Read 16-bit data array while transmitting zeros.

        Parameters
        ----------
        data_to_read : int
            Number of 16-bit data to read from slave device.

        Returns
        -------
        list of int
            List of 16-bit date returned by slave device.
        """
        self._start()
        data_in = self._read_bulk(data_to_read, 16)
        self._stop()

        return data_in

    def write8(self, data: int):
        """Send 8-bit data over SPI.

        Parameters
        ----------
        data : int
            Data to transmit.
        """
        self.transfer8(data)

    def write16(self, data: int):
        """Send 16-bit data over SPI.

        Parameters
        ----------
        data : int
            Data to transmit.
        """
        self.transfer16(data)

    def write8_bulk(self, data: List[int]):
        """Send 8-bit data array over SPI.

        Parameters
        ----------
        data : list of int
            List of 8-bit data to transmit.
        """
        self.transfer8_bulk(data)

    def write16_bulk(self, data: List[int]):
        """Send 16-bit data array over SPI.

        Parameters
        ----------
        data : list of int
            List of 16-bit data to transmit.
        """
        self.transfer16_bulk(data)
