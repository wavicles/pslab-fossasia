"""These tests can be run as either unit tests or integration tests.

By default, they are run as unit tests. When running as unit tests, recorded serial
traffic from passing integration tests are played back during the test.

By calling pytest with the --integration flag, the tests will instead be run as
integration tests. In this test mode, the PSLab's PWM output is used to generate a
signal which is analyzed by the logic analyzer. Before running the integration tests,
connect SQ1->ID1->ID2->ID3->ID4.

By calling pytest with the --record flag, the serial traffic generated by the
integration tests will be recorded to JSON files, which are played back during unit
testing. The --record flag implies --integration.
"""

import json
import os.path
import time

import numpy as np
import pytest

import PSL.commands_proto as CP
from PSL import logic_analyzer
from PSL import packet_handler
from PSL import sciencelab

LOGDIR = os.path.join("tests", "recordings", "logic_analyzer")

EVENTS = 2495
FREQUENCY = 1e5
DUTY_CYCLE = 0.5
LOW_FREQUENCY = 100
LOWER_FREQUENCY = 10
MICROSECONDS = 1e6
ONE_CLOCK_CYCLE = logic_analyzer.CLOCK_RATE ** -1 * MICROSECONDS


def get_frequency(test_name):
    """Return the PWM frequency for integration tests.
    """
    low_frequency_tests = (
        "test_capture_four_low_frequency",
        "test_capture_four_lower_frequency",
        "test_capture_four_lowest_frequency",
        "test_capture_timeout",
        "test_get_states",
    )
    if test_name in low_frequency_tests:
        return LOW_FREQUENCY
    elif test_name == "test_capture_four_too_low_frequency":
        return LOWER_FREQUENCY
    else:
        return FREQUENCY


@pytest.fixture
def scaffold(monkeypatch, request, integration, record):
    """Handle setup and teardown of tests.
    """
    if record:
        integration = True

    test_name = request.node.name
    handler = get_handler(monkeypatch, test_name, integration)

    if record:
        handler._logging = True

    yield logic_analyzer.LogicAnalyzer(handler)

    if record:
        log = handler._log.split(b"STOP")[:-1]
        record_traffic(test_name, log)


def get_handler(monkeypatch, test_name: str, integration: bool = True):
    """Return a Handler instance.

    When running unit tests, the Handler is a MockHandler. When running integration
    tests, this method also sets up the PWM signals before returning the Handler.
    """
    if integration:
        psl = sciencelab.connect()
        psl.sqrPWM(
            freq=get_frequency(test_name),
            h0=DUTY_CYCLE,
            p1=0,
            h1=DUTY_CYCLE,
            p2=0,
            h2=DUTY_CYCLE,
            p3=0,
            h3=DUTY_CYCLE,
        )
        return psl.H
    else:
        logfile = os.path.join(LOGDIR, test_name + ".json")
        tx, rx = json.load(open(logfile, "r"))
        traffic = ((bytes(t), bytes(r)) for t, r in zip(tx, rx))
        monkeypatch.setattr(packet_handler, "RECORDED_TRAFFIC", traffic)
        return packet_handler.MockHandler()


def record_traffic(test_name: str, log: list):
    """Record serial traffic to a JSON file.

    The file name is the test name + .json.
    """
    tx = []
    rx = []

    for b in log:
        direction = b[:2]
        data = b[2:]
        if direction == b"TX":
            tx.append(list(data))
            rx.append([])
        elif direction == b"RX":
            rx[-1] += list(data)
        else:
            raise ValueError("Unknown direction: {direction}")

    logfile = os.path.join(LOGDIR, test_name + ".json")
    print([tx, rx])
    json.dump([tx, rx], open(logfile, "w"))


def test_capture_one_channel(scaffold):
    t = scaffold.capture(1, EVENTS)
    assert len(t[0]) == EVENTS


def test_capture_two_channels(scaffold):
    t1, t2 = scaffold.capture(2, EVENTS)
    assert len(t1) == len(t2) == EVENTS


def test_capture_four_channels(scaffold):
    t1, t2, t3, t4 = scaffold.capture(4, EVENTS)
    assert len(t1) == len(t2) == len(t3) == len(t4) == EVENTS


def test_capture_four_low_frequency(scaffold):
    e2e_time = (LOW_FREQUENCY ** -1) / 2
    t1 = scaffold.capture(4, 10, e2e_time=e2e_time)[0]
    # When capturing every edge, the accuracy seems to depend on
    # the PWM prescaler as well as the logic analyzer prescaler.
    pwm_abstol = ONE_CLOCK_CYCLE * logic_analyzer.PRESCALERS[2]
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), abs=ONE_CLOCK_CYCLE * logic_analyzer.PRESCALERS[1] + pwm_abstol
    )


def test_capture_four_lower_frequency(scaffold):
    e2e_time = LOW_FREQUENCY ** -1
    t1 = scaffold.capture(4, 10, modes=4 * ["rising"], e2e_time=e2e_time)[0]
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), abs=ONE_CLOCK_CYCLE * logic_analyzer.PRESCALERS[2]
    )


def test_capture_four_lowest_frequency(scaffold):
    e2e_time = (LOW_FREQUENCY ** -1) * 16
    t1 = scaffold.capture(
        4, 10, modes=4 * ["sixteen rising"], e2e_time=e2e_time, timeout=2
    )[0]
    assert np.array(9 * [e2e_time * MICROSECONDS]) == pytest.approx(
        np.diff(t1), abs=ONE_CLOCK_CYCLE * logic_analyzer.PRESCALERS[3]
    )


def test_capture_four_too_low_frequency(scaffold):
    e2e_time = (LOWER_FREQUENCY ** -1) * 4
    with pytest.raises(ValueError):
        scaffold.capture(4, 10, modes=4 * ["four rising"], e2e_time=e2e_time, timeout=5)


def test_capture_nonblocking(scaffold):
    scaffold.capture(1, EVENTS, block=False)
    time.sleep(EVENTS * FREQUENCY ** -1)
    t = scaffold.fetch_data()
    assert len(t[0]) >= EVENTS


def test_capture_rising_edges(scaffold):
    events = 100
    t1, t2 = scaffold.capture(2, events, modes=["any", "rising"])
    expected = FREQUENCY ** -1 * MICROSECONDS / 2
    result = t2 - t1 - (t2 - t1)[0]
    assert np.arange(0, expected * events, expected) == pytest.approx(
        result, abs=ONE_CLOCK_CYCLE
    )


def test_capture_four_rising_edges(scaffold):
    events = 100
    t1, t2 = scaffold.capture(2, events, modes=["rising", "four rising"])
    expected = FREQUENCY ** -1 * MICROSECONDS * 3
    result = t2 - t1 - (t2 - t1)[0]
    assert np.arange(0, expected * events, expected) == pytest.approx(
        result, abs=ONE_CLOCK_CYCLE
    )


def test_capture_sixteen_rising_edges(scaffold):
    events = 100
    t1, t2 = scaffold.capture(2, events, modes=["four rising", "sixteen rising"])
    expected = FREQUENCY ** -1 * MICROSECONDS * 12
    result = t2 - t1 - (t2 - t1)[0]
    assert np.arange(0, expected * events, expected) == pytest.approx(
        result, abs=ONE_CLOCK_CYCLE
    )


def test_capture_too_many_events(scaffold):
    with pytest.raises(ValueError):
        scaffold.capture(1, CP.MAX_SAMPLES // 4 + 1)


def test_capture_too_many_channels(scaffold):
    with pytest.raises(ValueError):
        scaffold.capture(5)


def test_measure_frequency(scaffold):
    frequency = scaffold.measure_frequency("ID1", timeout=0.1)
    assert FREQUENCY == pytest.approx(frequency)


def test_measure_frequency_firmware(scaffold):
    frequency = scaffold.measure_frequency(
        "ID2", timeout=0.1, simultaneous_oscilloscope=True
    )
    assert FREQUENCY == pytest.approx(frequency)


def test_measure_interval(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    interval = scaffold.measure_interval(
        channels=["ID1", "ID2"], modes=["rising", "falling"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * MICROSECONDS * 0.5
    assert expected_interval == pytest.approx(interval, abs=ONE_CLOCK_CYCLE)


def test_measure_interval_same_channel(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    interval = scaffold.measure_interval(
        channels=["ID1", "ID1"], modes=["rising", "falling"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * DUTY_CYCLE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=ONE_CLOCK_CYCLE)


def test_measure_interval_same_channel_any(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    interval = scaffold.measure_interval(
        channels=["ID1", "ID1"], modes=["any", "any"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * DUTY_CYCLE * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=ONE_CLOCK_CYCLE)


def test_measure_interval_same_channel_four_rising(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    interval = scaffold.measure_interval(
        channels=["ID1", "ID1"], modes=["rising", "four rising"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * 3 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=ONE_CLOCK_CYCLE)


def test_measure_interval_same_channel_sixteen_rising(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    interval = scaffold.measure_interval(
        channels=["ID1", "ID1"], modes=["rising", "sixteen rising"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * 15 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=ONE_CLOCK_CYCLE)


def test_measure_interval_same_channel_same_event(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    interval = scaffold.measure_interval(
        channels=["ID3", "ID3"], modes=["rising", "rising"], timeout=0.1
    )
    expected_interval = FREQUENCY ** -1 * MICROSECONDS
    assert expected_interval == pytest.approx(interval, abs=ONE_CLOCK_CYCLE)


def test_measure_duty_cycle(scaffold):
    period, duty_cycle = scaffold.measure_duty_cycle("ID4", timeout=0.1)
    expected_period = FREQUENCY ** -1 * MICROSECONDS
    assert (expected_period, DUTY_CYCLE) == pytest.approx(
        (period, duty_cycle), abs=ONE_CLOCK_CYCLE
    )


def test_get_xy_rising_trigger(scaffold):
    scaffold.configure_trigger("ID1", "rising")
    t = scaffold.capture(1, 100)
    _, y = scaffold.get_xy(t)
    assert y[0]


def test_get_xy_falling_trigger(scaffold):
    scaffold.configure_trigger("ID1", "falling")
    t = scaffold.capture(1, 100)
    _, y = scaffold.get_xy(t)
    assert not y[0]


def test_get_xy_rising_capture(scaffold):
    t = scaffold.capture(1, 100, modes=["rising"])
    _, y = scaffold.get_xy(t)
    assert sum(y) == 100


def test_get_xy_falling_capture(scaffold):
    t = scaffold.capture(1, 100, modes=["falling"])
    _, y = scaffold.get_xy(t)
    assert sum(~y) == 100


def test_stop(scaffold):
    scaffold.capture(1, EVENTS, modes=["sixteen rising"], block=False)
    time.sleep(EVENTS * FREQUENCY ** -1)
    progress_time = time.time()
    progress = scaffold.get_progress()
    scaffold.stop()
    stop_time = time.time()
    time.sleep(EVENTS * FREQUENCY ** -1)
    assert progress < CP.MAX_SAMPLES // 4
    abstol = FREQUENCY * (stop_time - progress_time)
    assert progress == pytest.approx(scaffold.get_progress(), abs=abstol)


def test_get_states(scaffold):
    time.sleep(LOW_FREQUENCY ** -1)
    states = scaffold.get_states()
    expected_states = {"ID1": True, "ID2": True, "ID3": True, "ID4": True}
    assert states == expected_states


def test_count_pulses(scaffold):
    interval = 0.2
    pulses = scaffold.count_pulses("ID2", interval)
    expected_pulses = FREQUENCY * interval
    assert expected_pulses == pytest.approx(pulses, rel=0.1)  # Pretty bad accuracy.
