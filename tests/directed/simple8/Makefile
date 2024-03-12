sv:
	peakrdl sv -o rtl simple8.rdl
	sv-exporter -o rtl install
	
lint:
	@verilator --lint-only --Wall --top-module simple8_reg_top \
		simple8.vlt \
		$(wildcard ./rtl/*pkg.sv) \
		$(filter-out $(wildcard ./rtl/*pkg.sv), $(wildcard ./rtl/*.sv))