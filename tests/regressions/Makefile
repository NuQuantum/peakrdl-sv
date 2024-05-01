SIM ?= verilator
TOPLEVEL_LANG ?= verilog
WAVES ?= 0

VERILOG_SOURCES += $(PWD)/rtl/rdl_subreg_pkg.sv
VERILOG_SOURCES += $(PWD)/rtl/rdl_subreg_flop.sv
VERILOG_SOURCES += $(PWD)/rtl/rdl_subreg_arb.sv
VERILOG_SOURCES += $(PWD)/rtl/rdl_subreg.sv
VERILOG_SOURCES += $(PWD)/rtl/test_reg_pkg.sv
VERILOG_SOURCES += $(PWD)/rtl/test_reg_top.sv

TOPLEVEL = test_reg_top
MODULE = test

CUSTOM_COMPILE_DEPS = rtl

ADDR_MAP = addrmap.rdl
export ADDR_MAP

ifeq (SIM, verilator)
ifeq (WAVES, 1)
EXTRA_ARGS += --trace-fst --trace-structs
endif
endif

EXTRA_ARGS += --trace-fst --trace-structs
include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: rtl
rtl:
	peakrdl sv -o rtl addrmap.rdl
	sv-exporter -o rtl install
