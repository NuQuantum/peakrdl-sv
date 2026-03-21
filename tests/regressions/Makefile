SIM           ?= verilator
TOPLEVEL_LANG ?= verilog
WAVES         ?= 0

RTL_DIR       := rtl
RTL_PKG_FILES := $(wildcard $(RTL_DIR)/*_pkg.sv)
RTL_SRC_FILES := $(filter-out $(RTL_PKG_FILES), $(wildcard $(RTL_DIR)/*.sv))

TOPLEVEL := test_reg_top
MODULE   := test

CUSTOM_COMPILE_DEPS = rtl
VERILOG_SOURCES := $(RTL_PKG_FILES) $(RTL_SRC_FILES)

ADDR_MAP = addrmap.rdl
export ADDR_MAP

ifeq ($(SIM), verilator)
ifeq ($(WAVES), 1)
EXTRA_ARGS += --trace-fst --trace-structs
endif
endif

include $(shell cocotb-config --makefiles)/Makefile.sim

.PHONY: rtl test clean

rtl:
	@echo "Auto-generating SV output"
	uv run peakrdl sv -o $(RTL_DIR) addrmap.rdl
	uv run sv-exporter -o $(RTL_DIR) install

clean::
	rm -rf $(RTL_DIR)
	rm -f results.xml

test: rtl $(.DEFAULT_GOAL)
	@echo $(RTL_PKG_FILES)
	@echo $(RTL_SRC_FILES)
