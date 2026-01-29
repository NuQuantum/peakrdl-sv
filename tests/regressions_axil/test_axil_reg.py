from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

import cocotb
from cocotb_tools.runner import get_runner
from testbench import Testbench

logger = logging.getLogger(__name__)

proj_path = Path(__file__).resolve().parent
rtl_dir = proj_path / "rtl"
addr_map = proj_path / "addrmap.rdl"


# set in cmd line
try:
    debug = os.environ["DEBUG"] == "1"
except KeyError:
    debug = False


async def assert_register_match(tb: Testbench, register: str) -> None:
    """Reads the value of a register by name from the device under test and asserts
    that its value is equal to the locally stored expected value.

    :param tb: A handle to the testbench (to provide RAL access)
    :type tb: Testbench
    :param register: The name of the register to perform the assertion on
    :type register: str
    """
    actual = await tb.RAL.read(register)
    assert tb.RAL.get(register) == actual, f"Expected does not equal actual ({actual})"


async def assert_field_match(tb: Testbench, register: str, field: str) -> None:
    """Reads the value of a register's field by name from the device under test and
    asserts that its value is equal to the locally stored expected value.

    :param tb: A handle to the testbench (to provide RAL access)
    :type tb: Testbench
    :param register: The name of the register to within which the field is located
    :type register: str
    :param field: The field to perform the assertion on
    :type field: str
    """
    actual = await tb.RAL.read(register, field)
    assert tb.RAL.get_field(register, field) == actual, (
        f"Expected does not equal actual ({actual})"
    )


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_bringup(dut):
    """Bringup"""

    tb = Testbench(dut, addr_map, debug)

    # init the dut
    await tb.reset()

    # wait some cycles
    for _ in range(20):
        await tb.clkedge


@cocotb.test(timeout_time=50, timeout_unit="us")
@cocotb.parametrize(
    target=["r1"]
    + [f"r2_array_{i}" for i in range(4)]
    + [f"r{i}" for i in range(3, 9)],
)
async def test_register_read_write(dut, target):
    """Writes to a register and reads back the value"""

    tb = Testbench(dut, addr_map, debug)

    # reset the dut
    await tb.reset()

    # Write a random value to the register
    tb.RAL.randomize(target)
    await tb.RAL.write(target)

    # Assert the local version matches the HW version
    await assert_register_match(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_register_array_read_write(dut):
    """Writes to a register and reads back the value"""

    tb = Testbench(dut, addr_map, debug)

    # reset the dut
    await tb.reset()
    await tb.clkedge

    for i in range(4):
        target = f"r2_array_{i}"

        # write a random value
        tb.RAL.randomize(target)
        await tb.RAL.write(target)

        await assert_register_match(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_field_read_write(dut):
    """Writes to a field and reads back the value"""

    tb = Testbench(dut, addr_map, debug)

    # init the dut
    await tb.reset()
    await tb.clkedge

    target = "r8"

    # randomize the value of the register and write to DUT
    tb.RAL.randomize(target)
    await tb.RAL.write(target)

    for i in range(2):
        # Assert equality
        await assert_field_match(tb, target, f"f{i + 1}")

    for i in range(2):
        # randomize the current field value
        tb.RAL.randomize_field(target, f"f{i + 1}")
        await tb.RAL.write(target)

        # assert value of the register
        await assert_register_match(tb, target)

    # Test writing the value directly
    await tb.RAL.write(target, 0xFA)
    await assert_register_match(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_wide_register_read_write(dut):
    """Writes to a wide register and reads back the value"""

    tb = Testbench(dut, addr_map, debug)

    # reset the dut
    await tb.reset()
    await tb.clkedge

    target = "r4"

    for i in range(2):
        # randomize the current field
        tb.RAL.randomize_field(target, f"f{i + 1}")
        await tb.RAL.write(target)

        # assert equality on entire register
        await assert_field_match(tb, target, f"f{i + 1}")

    # write a wide reg by setting each field and then writing
    tb.RAL.randomize(target)
    await tb.RAL.write(target)
    await assert_register_match(tb, target)

    # write a wide value all at once
    await tb.RAL.write(target, data=0xAB12)
    await assert_register_match(tb, target)


@cocotb.test(timeout_time=50, timeout_unit="us")
async def test_wide_narrow_register_read_write(dut):
    """writes to the fields of a register which is wide (> accesswidth) but has fields
    which are smaller than the accesswidth"""

    tb = Testbench(dut, addr_map, debug)
    await tb.reset()

    target = "r5"

    # write a random value to the register
    tb.RAL.randomize(target)
    await tb.RAL.write(target)

    # check the entire register matches
    await assert_register_match(tb, target)

    # Check that each field match
    for i in range(4):
        await assert_field_match(tb, target, f"f{i + 1}")


#
# Cocotb Runner (pytest)
#
def test_simple_dff_runner():
    # first create files
    os.environ.update({"ADDR_MAP": str(addr_map)})

    subprocess.run(["uv", "run", "peakrdl", "sv", "-o", rtl_dir, addr_map], check=True)
    subprocess.run(["uv", "run", "sv-exporter", "-o", rtl_dir, "install"], check=True)

    # start simulation
    sim = os.getenv("SIM", "icarus")

    sources = [
        rtl_dir / f
        for f in [
            "rdl_subreg_pkg.sv",
            "rdl_subreg_ext.sv",
            "rdl_subreg_flop.sv",
            "rdl_subreg_arb.sv",
            "rdl_subreg.sv",
            "test_reg_pkg.sv",
            "test_reg_top.sv",
        ]
    ]

    runner = get_runner(sim)
    runner.build(
        sources=sources,
        hdl_toplevel="test_reg_top",
        always=True,
        timescale=("1ns", "1ps"),
        build_dir=proj_path / "sim_build",
    )

    runner.test(
        hdl_toplevel="test_reg_top",
        test_module=Path(__file__).stem,
        timescale=("1ns", "1ps"),
        build_dir=proj_path / "sim_build",
    )


if __name__ == "__main__":
    test_simple_dff_runner()
