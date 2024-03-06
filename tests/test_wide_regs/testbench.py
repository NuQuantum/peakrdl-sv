from __future__ import annotations

import logging

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import RisingEdge
from cocotb_bus.drivers import BusDriver
from systemrdl.compiler import RDLCompiler
from systemrdl.compiler import RootNode  # noqa
from systemrdl.node import AddrmapNode  # noqa
from systemrdl.node import FieldNode  # noqa
from systemrdl.node import RegfileNode  # noqa
from systemrdl.node import RegNode  # noqa

from peakrdl_sv.exporter import VerilogExporter

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


class CsrTransaction:
    def __init__(self, addr: int, wdata=None):
        self.addr = addr
        self.wdata = wdata
        self.rdata = 0

    @property
    def is_write(self):
        return self.wdata is not None

    @property
    def re(self):
        return 0 if self.is_write else 1

    @property
    def we(self):
        return 1 if self.is_write else 0


class CsrDriver(BusDriver):
    _signals = ["re", "we", "addr", "rdata", "wdata"]

    def __init__(self, dut, clock, name="csr", **kwargs):
        BusDriver.__init__(self, dut, name, clock, **kwargs)

    async def _driver_send(self, transaction: CsrTransaction, sync):
        await RisingEdge(self.clock)
        self.bus.re.value = transaction.re
        self.bus.we.value = transaction.we
        self.bus.addr.value = transaction.addr
        if transaction.is_write:
            self.bus.wdata.value = transaction.wdata
        await RisingEdge(self.clock)
        self.bus.re.value = 0
        self.bus.we.value = 0


class RegisterMap:
    def __init__(self, rdlfile, bus):
        self.bus = bus
        self.node = self._parse_rdl(rdlfile)

    def _parse_rdl(self, rdlfile):
        rdlc = RDLCompiler()
        rdlc.compile_file(rdlfile)
        root = rdlc.elaborate()
        exporter = VerilogExporter()
        exporter.walk(root)
        return exporter.top

    def get_registers(self):
        return self.node.get_registers()


class Testbench:
    def __init__(self, dut):
        self.dut = dut
        self.bus = CsrDriver(dut, dut.clk)
        self.regmap = RegisterMap("addrmap.rdl", self.bus)
        registers = self.regmap.get_registers()
        for register in registers:
            logger.info(f"name={register.inst_name}")
            for field in register:
                logger.info(f"field={field.inst_name} addr={field.absolute_address}")

        dut.rst.setimmediatevalue(0)
        dut.csr_we.setimmediatevalue(0)
        dut.csr_re.setimmediatevalue(0)
        dut.csr_addr.setimmediatevalue(0)
        dut.csr_wdata.setimmediatevalue(0)
        dut.hw2reg.setimmediatevalue(0)

        cocotb.start_soon(Clock(dut.clk, 5, "ns").start())
