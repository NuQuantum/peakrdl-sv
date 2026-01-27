SIM ?= verilator
TOPLEVEL_LANG ?= verilog
WAVES ?= 0

RTL_DIR = rtl
RTL_PKG_FILES = $(wildcard $(RTL_DIR)/*_pkg.sv)
RTL_SRC_FILES = $(filter-out $(RTL_PKG_FILES), $(wildcard $(RTL_DIR)/*.sv))

TOPLEVEL = test_reg_top
MODULE = test

CUSTOM_COMPILE_DEPS = rtl
COMPILE_ARGS += $(RTL_PKG_FILES) $(RTL_SRC_FILES)

ADDR_MAP = addrmap.rdl
export ADDR_MAP

ifeq (SIM, verilator)
ifeq (WAVES, 1)
EXTRA_ARGS += --trace-fst --trace-structs
endif
endif

EXTRA_ARGS += --trace-fst --trace-structs
include $(shell cocotb-config --makefiles)/Makefile.sim

rtl:
	echo "Auto-generating SV output"
	peakrdl sv -o rtl addrmap.rdl
	sv-exporter -o rtl install

clean::
	rm -rf rtl
	rm -f results.xml

test: $(.DEFAULT_GOAL)
	@echo $(RTL_PKG_FILES)
	@echo $(RTL_SRC_FILES)
