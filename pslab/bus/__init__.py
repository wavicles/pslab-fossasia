"""Contains modules for interfacing with the PSLab's I2C, SPI, and UART buses.

(UART still TODO)
"""

from pslab.bus.i2c import I2CMaster, I2CSlave
from pslab.bus.spi import SPIMaster, SPISlave

__all__ = (
    "I2CMaster",
    "I2CSlave",
    "SPIMaster",
    "SPISlave",
)
