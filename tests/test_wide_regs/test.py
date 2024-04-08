from __future__ import annotations

import logging

import cocotb
from testbench import Testbench

logger = logging.getLogger(__name__)


async def assert_equal(tb: Testbench, register: str) -> None:
    assert tb.RAL.get(register) == await tb.RAL.read(register)


async def assert_field_equal(tb: Testbench, register: str, field: str) -> None:
    assert tb.RAL.get_field(register, field) == await tb.RAL.read(register, field)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_bringup(dut):
    """Bringup"""

    tb = Testbench(dut)

    # init the dut
    await tb.reset()

    # wait some cycles
    for _ in range(20):
        await tb.clkedge


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_register_read_write(dut):
    """Writes to a register and reads back the value"""
    tb = Testbench(dut)

    # reset the dut
    await tb.reset()
    await tb.clkedge

    target = "r1"

    # set the LED by name
    tb.RAL.randomize(target)
    await tb.RAL.write(target)

    # read the register value from the DUT
    await assert_equal(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_register_array_read_write(dut):
    """Writes to a register and reads back the value"""
    tb = Testbench(dut)

    # reset the dut
    await tb.reset()
    await tb.clkedge

    for i in range(4):
        target = f"r2_array_{i}"

        # write a random value
        tb.RAL.randomize(target)
        await tb.RAL.write(target)

        await assert_equal(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_field_read_write(dut):
    """Writes to a field and reads back the value"""
    tb = Testbench(dut)

    # init the dut
    await tb.reset()
    await tb.clkedge

    target = "r8"

    # randomize the value of the register and write to DUT
    tb.RAL.randomize(target)
    await tb.RAL.write(target)

    for i in range(2):
        # Assert equality
        await assert_field_equal(tb, target, f"f{i+1}")

    for i in range(2):
        # randomize the current field value
        tb.RAL.randomize_field(target, f"f{i+1}")
        await tb.RAL.write(target)

        # assert value of the register
        await assert_equal(tb, target)

    # Test writing the value directly
    tb.RAL.write(target, 0xFA)
    await assert_equal(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_wide_register_read_write(dut):
    """Writes to a wide register and reads back the value"""
    tb = Testbench(dut)

    # reset the dut
    await tb.reset()
    await tb.clkedge

    target = "r4"

    for i in range(2):
        # randomize the current field
        tb.RAL.randomize_field(target, f"f{i+1}")
        await tb.RAL.write(target)

        # assert equality on entire register
        assert_field_equal(tb, target, f"f{i+1}")

    # write a wide reg by setting each field and then writing
    tb.RAL.randomize(target)
    await tb.RAL.write(target)
    await assert_equal(tb, target)

    # write a wide value all at once
    await tb.RAL.write(target, data=0xABCD1234)
    await assert_equal(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_wide_narrow_register_read_write(dut):
    """writes to the fields of a register which is wide (> accesswidth) but has fields
    which are smaller than the accesswidth"""
    tb = Testbench(dut, debug=True)
    await tb.reset()

    target = "r5"

    # write a random value to the register
    tb.RAL.randomize(target)
    await tb.RAL.write(target)

    # check the entire register matches
    await assert_equal(tb, target)

    # Check that each field match
    for i in range(4):
        await assert_field_equal(tb, target, f"f{i+1}")
