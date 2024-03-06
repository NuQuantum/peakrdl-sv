from __future__ import annotations

import logging

import cocotb
from cocotb.triggers import ClockCycles
from testbench import CsrTransaction
from testbench import Testbench

logger = logging.getLogger(__name__)


@cocotb.test(timeout_time=2000, timeout_unit="ns")
async def test_regfile(dut):
    tb = Testbench(dut)
    await ClockCycles(dut.clk, 20)
    await tb.bus.send(CsrTransaction(0, 255))
    await ClockCycles(dut.clk, 20)

    logger.info("exiting test")
