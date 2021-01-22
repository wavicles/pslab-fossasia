# https://www.st.com/resource/en/datasheet/vl53l0x.pdf
# https://www.st.com/resource/en/datasheet/vl53l1x.pdf

# see also:
# https://github.com/adafruit/Adafruit_VL53L0X/blob/master/src/vl53l0x_tuning.h#L49
# https://github.com/pololu/vl53l0x-arduino/blob/master/VL53L0X.cpp
# https://os.mbed.com/teams/ST/code/VL53L0X//annotate/834986cdde0a/VL53L0X_tuning.h/
# https://git.nukon.com.au/public-group/iot-counter/blob/124e2d2f6a5690ec11c67aaa5b70bb8cca27bca8/VL50L0X_library/Api/core/inc/vl53l0x_tuning.h
# https://github.com/adafruit/Adafruit_CircuitPython_VL53L0X/blob/master/adafruit_vl53l0x.py

from __future__ import print_function
import time

from PSL.Peripherals import I2CSlave

def connect(route, **args):
    '''
    route can either be I.I2C , or a radioLink instance
    '''
    return VL531X(route, **args)

# registers
# VL530X
# MODEL_ID    = 0xEA
# MODULE_TYPE = 0xCC
# MASK_REV    = 0x10
# VL531X
# MODEL_ID    = 0x010F
# MODULE_TYPE = 0x0110
# MASK_REV    = 0x0111

# Configuration constants, taken from
# https://github.com/adafruit/Adafruit_CircuitPython_VL53L0X.git
_SYSRANGE_START = 0x00
_SYSTEM_THRESH_HIGH = 0x0C
_SYSTEM_THRESH_LOW = 0x0E
_SYSTEM_SEQUENCE_CONFIG = 0x01
_SYSTEM_RANGE_CONFIG = 0x09
_SYSTEM_INTERMEASUREMENT_PERIOD = 0x04
_SYSTEM_INTERRUPT_CONFIG_GPIO = 0x0A
_GPIO_HV_MUX_ACTIVE_HIGH = 0x84
_SYSTEM_INTERRUPT_CLEAR = 0x0B
_RESULT_INTERRUPT_STATUS = 0x13
_RESULT_RANGE_STATUS = 0x14
_RESULT_CORE_AMBIENT_WINDOW_EVENTS_RTN = 0xBC
_RESULT_CORE_RANGING_TOTAL_EVENTS_RTN = 0xC0
_RESULT_CORE_AMBIENT_WINDOW_EVENTS_REF = 0xD0
_RESULT_CORE_RANGING_TOTAL_EVENTS_REF = 0xD4
_RESULT_PEAK_SIGNAL_RATE_REF = 0xB6
_ALGO_PART_TO_PART_RANGE_OFFSET_MM = 0x28
_I2C_SLAVE_DEVICE_ADDRESS = 0x8A
_MSRC_CONFIG_CONTROL = 0x60
_PRE_RANGE_CONFIG_MIN_SNR = 0x27
_PRE_RANGE_CONFIG_VALID_PHASE_LOW = 0x56
_PRE_RANGE_CONFIG_VALID_PHASE_HIGH = 0x57
_PRE_RANGE_MIN_COUNT_RATE_RTN_LIMIT = 0x64
_FINAL_RANGE_CONFIG_MIN_SNR = 0x67
_FINAL_RANGE_CONFIG_VALID_PHASE_LOW = 0x47
_FINAL_RANGE_CONFIG_VALID_PHASE_HIGH = 0x48
_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT = 0x44
_PRE_RANGE_CONFIG_SIGMA_THRESH_HI = 0x61
_PRE_RANGE_CONFIG_SIGMA_THRESH_LO = 0x62
_PRE_RANGE_CONFIG_VCSEL_PERIOD = 0x50
_PRE_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x51
_PRE_RANGE_CONFIG_TIMEOUT_MACROP_LO = 0x52
_SYSTEM_HISTOGRAM_BIN = 0x81
_HISTOGRAM_CONFIG_INITIAL_PHASE_SELECT = 0x33
_HISTOGRAM_CONFIG_READOUT_CTRL = 0x55
_FINAL_RANGE_CONFIG_VCSEL_PERIOD = 0x70
_FINAL_RANGE_CONFIG_TIMEOUT_MACROP_HI = 0x71
_FINAL_RANGE_CONFIG_TIMEOUT_MACROP_LO = 0x72
_CROSSTALK_COMPENSATION_PEAK_RATE_MCPS = 0x20
_MSRC_CONFIG_TIMEOUT_MACROP = 0x46
_SOFT_RESET_GO2_SOFT_RESET_N = 0xBF
_IDENTIFICATION_MODEL_ID = 0xC0
_IDENTIFICATION_REVISION_ID = 0xC2
_OSC_CALIBRATE_VAL = 0xF8
_GLOBAL_CONFIG_VCSEL_WIDTH = 0x32
_GLOBAL_CONFIG_SPAD_ENABLES_REF_0 = 0xB0
_GLOBAL_CONFIG_SPAD_ENABLES_REF_1 = 0xB1
_GLOBAL_CONFIG_SPAD_ENABLES_REF_2 = 0xB2
_GLOBAL_CONFIG_SPAD_ENABLES_REF_3 = 0xB3
_GLOBAL_CONFIG_SPAD_ENABLES_REF_4 = 0xB4
_GLOBAL_CONFIG_SPAD_ENABLES_REF_5 = 0xB5
_GLOBAL_CONFIG_REF_EN_START_SELECT = 0xB6
_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD = 0x4E
_DYNAMIC_SPAD_REF_EN_START_OFFSET = 0x4F
_POWER_MANAGEMENT_GO1_POWER_FORCE = 0x80
_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV = 0x89
_ALGO_PHASECAL_LIM = 0x30
_ALGO_PHASECAL_CONFIG_TIMEOUT = 0x30
_VCSEL_PERIOD_PRE_RANGE = 0
_VCSEL_PERIOD_FINAL_RANGE = 1

_ID_REGISTERS = (
    (0xC0, 0xEE),
    (0xC1, 0xAA),
    (0xC2, 0x10),
)

_SPAD_CONFIG = (
    (0xFF, 0x01),
    (_DYNAMIC_SPAD_REF_EN_START_OFFSET, 0x00),
    (_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, 0x2C),
    (0xFF, 0x00),
    (_GLOBAL_CONFIG_REF_EN_START_SELECT, 0xB4),
)

# TODO: What do these values mean?
_TUNING_CONFIG = (
    (0xFF, 0x01),
    (0x00, 0x00),
    (0xFF, 0x00),
    (0x09, 0x00),
    (0x10, 0x00),
    (0x11, 0x00),
    (0x24, 0x01),
    (0x25, 0xFF),
    (0x75, 0x00),
    (0xFF, 0x01),
    (0x4E, 0x2C),
    (0x48, 0x00),
    (0x30, 0x20),
    (0xFF, 0x00),
    (0x30, 0x09),
    (0x54, 0x00),
    (0x31, 0x04),
    (0x32, 0x03),
    (0x40, 0x83),
    (0x46, 0x25),
    (0x60, 0x00),
    (0x27, 0x00),
    (0x50, 0x06),
    (0x51, 0x00),
    (0x52, 0x96),
    (0x56, 0x08),
    (0x57, 0x30),
    (0x61, 0x00),
    (0x62, 0x00),
    (0x64, 0x00),
    (0x65, 0x00),
    (0x66, 0xA0),
    (0xFF, 0x01),
    (0x22, 0x32),
    (0x47, 0x14),
    (0x49, 0xFF),
    (0x4A, 0x00),
    (0xFF, 0x00),
    (0x7A, 0x0A),
    (0x7B, 0x00),
    (0x78, 0x21),
    (0xFF, 0x01),
    (0x23, 0x34),
    (0x42, 0x00),
    (0x44, 0xFF),
    (0x45, 0x26),
    (0x46, 0x05),
    (0x40, 0x40),
    (0x0E, 0x06),
    (0x20, 0x1A),
    (0x43, 0x40),
    (0xFF, 0x00),
    (0x34, 0x03),
    (0x35, 0x44),
    (0xFF, 0x01),
    (0x31, 0x04),
    (0x4B, 0x09),
    (0x4C, 0x05),
    (0x4D, 0x04),
    (0xFF, 0x00),
    (0x44, 0x00),
    (0x45, 0x20),
    (0x47, 0x08),
    (0x48, 0x28),
    (0x67, 0x00),
    (0x70, 0x04),
    (0x71, 0x01),
    (0x72, 0xFE),
    (0x76, 0x00),
    (0x77, 0x00),
    (0xFF, 0x01),
    (0x0D, 0x01),
    (0xFF, 0x00),
    (0x80, 0x01),
    (0x01, 0xF8),
    (0xFF, 0x01),
    (0x8E, 0x01),
    (0x00, 0x01),
    (0xFF, 0x00),
    (0x80, 0x00),
)

# I2C general - probably implemented in firmware; not our concern here
#  # datasheet p18: first byte is address and read/write direction
#  WRITE_ADDRESS = 0x52
#  READ_ADDRESS = 0x53

# abbreviations and acronyms
# VCSEL - Vertical Cavity Surface Emitting Laser
# SPAD - Single Photon Avalanche Diode
# MSRC - Minimum Signal Rate Check
class VL531X():
    PLOTNAMES = ['Data']
    ADDRESS = 0x29
    NAME = 'Time-of-Flight Proximity Sensor'

    def __init__(self, handler, **args):
        self.ADDRESS = args.get('address', self.ADDRESS)
        self.I2C = I2CSlave(handler, self.ADDRESS)

        self.io_timeout_s = 10
        # TODO: yet unused; move up?
        self.signal_rate_limit = 0.25

        # Check identification registers for expected values
        # VL53L0X datasheet section 3.2 / p21
        for reg, val in _ID_REGISTERS:
            res = self.I2C.read_bulk_byte(reg)
            if (res != val):
                print(res, val)
                raise RuntimeError(
                    "Unexpected ID register values"
                )

        # Initial configuration
        # Access to sensor, based on Adafruit's and Polulu's code
        # See https://github.com/adafruit/Adafruit_CircuitPython_VL53L0X.git
        # and https://github.com/pololu/vl53l0x-arduino/blob/master/VL53L0X.cpp
        # I2C standard mode
        # TODO: What do these registers and values actually mean?
        for reg_and_val in (
            (0x88, 0x00),
            (0x80, 0x01),
            (0xFF, 0x01),
            (0x00, 0x00)
        ):
            self.I2C.write_bulk(reg_and_val)
        self._stop_byte = self.I2C.read_bulk_byte(0x91)
        # useful for debugging
        # print("stop byte", self._stop_byte)
        # TODO: What do these registers and values actually mean?
        for reg_and_val in (
            (0x00, 0x01),
            (0xFF, 0x00),
            (0x80, 0x00)
        ):
            self.I2C.write_bulk(reg_and_val)
        # disable SIGNAL_RATE_MSRC (bit 1) and SIGNAL_RATE_PRE_RANGE (bit 4)
        # limit checks
        # TODO: What is MSRC config control?
        config_control = self.I2C.read_bulk_byte(_MSRC_CONFIG_CONTROL) | 0x12

        self.I2C.write_bulk([_MSRC_CONFIG_CONTROL, config_control])
        # set final range signal rate limit to 0.25 MCPS (million counts per
        # second)

        self.I2C.write_bulk([_SYSTEM_SEQUENCE_CONFIG, 0xFF])

        # SPAD config
        # TODO: doument what it really does; reading works without it, but may
        # yield less accurate values
        self._spad_config()

        for reg_and_val in _TUNING_CONFIG:
            self.I2C.write_bulk(reg_and_val)

        # more config
        self.I2C.write_bulk([_SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04])
        gpio_hv_mux_active_high = self.I2C.read_bulk_byte(_GPIO_HV_MUX_ACTIVE_HIGH)
        self.I2C.write_bulk([
            _GPIO_HV_MUX_ACTIVE_HIGH, gpio_hv_mux_active_high & ~0x10
        ])  # active low
        self.I2C.write_bulk([_SYSTEM_INTERRUPT_CLEAR, 0x01])
        #self._measurement_timing_budget_us = self.measurement_timing_budget
        self.I2C.write_bulk([_SYSTEM_SEQUENCE_CONFIG, 0xE8])
        #self.measurement_timing_budget = self._measurement_timing_budget_us
        # calibration
        self.I2C.write_bulk([_SYSTEM_SEQUENCE_CONFIG, 0x01])
        self._perform_single_ref_calibration(0x40)
        self.I2C.write_bulk([_SYSTEM_SEQUENCE_CONFIG, 0x01])
        self.I2C.write_bulk([_SYSTEM_SEQUENCE_CONFIG, 0x02])
        self._perform_single_ref_calibration(0x00)
        # "restore the previous Sequence Config"
        self.I2C.write_bulk([_SYSTEM_SEQUENCE_CONFIG, 0xE8])

    def _get_spad_info(self):
        _MAYBE_TIMER_REG = 0x83
        _SPAD_1 = (
            (0x80, 0x01),
            (0xFF, 0x01),
            (0x00, 0x00),
            (0xFF, 0x06)
        )
        _SPAD_2 = (
            (0xFF, 0x07),
            (0x81, 0x01),
            (0x80, 0x01),
            (0x94, 0x6B),
            (_MAYBE_TIMER_REG, 0x00),
        )
        _SPAD_3 = (
            (0x81, 0x00),
            (0xFF, 0x06)
        )
        _SPAD_4 = (
            (0xFF, 0x01),
            (0x00, 0x01),
            (0xFF, 0x00),
            (0x80, 0x00)
        )
        # Get reference SPAD count and type, returned as a 2-tuple of
        # count and boolean is_aperture.
        # Adapted from Adafruit, which is based on code from Pololu:
        # https://github.com/pololu/vl53l0x-arduino/blob/master/VL53L0X.cpp
        for reg_and_val in _SPAD_1:
            self.I2C.write_bulk(reg_and_val)

        # OR reg 0x83 with 0x04 - what does that do? Prepare timer?
        uu = self.I2C.read_bulk_byte(_MAYBE_TIMER_REG) | 0x04
        self.I2C.write_bulk([_MAYBE_TIMER_REG, uu])

        for reg_and_val in _SPAD_2:
            self.I2C.write_bulk(reg_and_val)

        start = time.monotonic()
        while self.I2C.read_bulk_byte(_MAYBE_TIMER_REG) == 0x00:
            if (
                self.io_timeout_s > 0
                and (time.monotonic() - start) >= self.io_timeout_s
            ):
                raise RuntimeError("Timeout waiting for VL53L0X!")

        # Timer reset?
        self.I2C.write_bulk([_MAYBE_TIMER_REG, 0x01])

        tmp = self.I2C.read_bulk_byte(0x92)
        # TODO: count is the lowest 7 bits of 0x92?
        count = tmp & 0x7F
        is_aperture = ((tmp >> 7) & 0x01) == 1

        for reg_and_val in _SPAD_3:
            self.I2C.write_bulk(reg_and_val)

        # TODO: What is this?
        vv = self.I2C.read_bulk_byte(_MAYBE_TIMER_REG) & ~0x04
        self.I2C.write_bulk([_MAYBE_TIMER_REG, vv])

        for reg_and_val in _SPAD_4:
            self.I2C.write_bulk(reg_and_val)

        return (count, is_aperture)

    def _spad_config(self):
        spad_count, spad_is_aperture = self._get_spad_info()
        # The SPAD map (RefGoodSpadMap) is read by
        # VL53L0X_get_info_from_device() in the API, but the same data seems to
        # be more easily readable from GLOBAL_CONFIG_SPAD_ENABLES_REF_0 through
        # _6, so read it from there.
        ref_spad_map = bytearray(7)
        ref_spad_map[0] = _GLOBAL_CONFIG_SPAD_ENABLES_REF_0
        # init SPAD reference stuff
        self.I2C.write_bulk([_GLOBAL_CONFIG_SPAD_ENABLES_REF_0, 0])
        spad_map = self.I2C.read_bulk(_GLOBAL_CONFIG_SPAD_ENABLES_REF_0, 6)
        # for debugging
        # print("SPAD map", spad_map)
        for i in range(6):
            ref_spad_map[i+1] = spad_map[i]

        for reg_and_val in _SPAD_CONFIG:
            self.I2C.write_bulk(reg_and_val)

        first_spad_to_enable = 12 if spad_is_aperture else 0
        spads_enabled = 0
        # check the 48 bits (6 bytes) read before
        for i in range(48):
            # ref_spad_map contains _GLOBAL_CONFIG_SPAD_ENABLES_REF_0 plus
            # 6 bytes from reading, so the index here is off by 1
            index = 1 + (i // 8)
            if i < first_spad_to_enable or spads_enabled == spad_count:
                # This bit is lower than the first one that should be enabled,
                # or (reference_spad_count) bits have already been enabled, so
                # zero this bit.
                ref_spad_map[index] &= ~(1 << (i % 8))
            elif (ref_spad_map[index] >> (i % 8)) & 0x1 > 0:
                spads_enabled += 1

        self.I2C.write_bulk(ref_spad_map)

    def _perform_single_ref_calibration(self, vhv_init_byte):
        # based on VL53L0X_perform_single_ref_calibration() from ST API.
        self.I2C.write_bulk([_SYSRANGE_START, 0x01 | vhv_init_byte & 0xFF])
        start = time.monotonic()
        while (self.I2C.read_bulk_byte(_RESULT_INTERRUPT_STATUS) & 0x07) == 0:
            if (
                self.io_timeout_s > 0
                and (time.monotonic() - start) >= self.io_timeout_s
            ):
                raise RuntimeError("Timeout waiting for VL53L0X!")
        self.I2C.write_bulk([_SYSTEM_INTERRUPT_CLEAR, 0x01])
        self.I2C.write_bulk([_SYSRANGE_START, 0x00])

    def getRaw(self):
        """Perform a single reading of the range for an object in front of
        the sensor and return the distance in millimeters.
        Taken from Adafruit
        """
        # Adapted from readRangeSingleMillimeters &
        # readRangeContinuousMillimeters in pololu code at:
        #   https://github.com/pololu/vl53l0x-arduino/blob/master/VL53L0X.cpp
        for reg_and_val in (
            (0x80, 0x01),
            (0xFF, 0x01),
            (0x00, 0x00),
            (0x91, self._stop_byte),
            (0x00, 0x01),
            (0xFF, 0x00),
            (0x80, 0x00),
            (_SYSRANGE_START, 0x01),
        ):
            self.I2C.write_bulk(reg_and_val)
        start = time.monotonic()

        while (self.I2C.read_bulk_byte(_SYSRANGE_START) & 0x01) > 0:
            if (
                self.io_timeout_s > 0
                and (time.monotonic() - start) >= self.io_timeout_s
            ):
                raise RuntimeError("Timeout waiting for VL53L0X!")
        start = time.monotonic()
        while (self.I2C.read_bulk_byte(_RESULT_INTERRUPT_STATUS) & 0x07) == 0:
            if (
                self.io_timeout_s > 0
                and (time.monotonic() - start) >= self.io_timeout_s
            ):
                raise RuntimeError("Timeout waiting for VL53L0X!")
        # assumptions: Linearity Corrective Gain is 1000 (default)
        # fractional ranging is not enabled
        data = self.I2C.read_bulk(_RESULT_RANGE_STATUS + 10, 2)
        self.I2C.write_bulk([_SYSTEM_INTERRUPT_CLEAR, 0x01])
        range_mm = (data[0] << 8) | data[1]
        return range_mm
