# peakrdl-sv

This SystemRDL exporter outputs SystemVerilog that is hopefully consumable by *any*
EDA tool including the common open source simulators such as Icarus and Verilator.

The design philosophy was to keep it simple and avoid the complexity of implementing
the full SystemRDL language.  As such there are limitations on what is supported and
there are no plans to extend support beyond the basics.

## Installation

```shell
$ pip install git+https://github.com/nuquantum/peakrdl-sv
```

## Usage

The exporter integrates with PeakRDL via the plugin flow defined here:
https://peakrdl.readthedocs.io/en/latest/for-devs/exporter-plugin.html

```
$ peakrdl sv -o ./generated <filename.rdl>
```

You can also run a standalone script that offers both `export` and `install`
targets.  The latter will install the required RTL dependencies to a local directory.
This can also be done at the `export` stage by passing the `--include-subreg` argument.

```
$ sv-exporter -h
usage: sv-exporter [-h] [-v] [-o OUTPUT] {export,install} ...

positional arguments:
  {export,install}
    export              Run the SystemVerlog RDL exporter
    install             Install SV source files into local tree

options:
  -h, --help            show this help message and exit
  -v, --verbose         Enable verbose logging
  -o OUTPUT, --output OUTPUT
                        Specify the output path

$ sv-exporter -o ./rtl install
$ sv-exporter -0 ./rtl export <filename>.rdl
$ sv-exporter -0 ./rtl export --include-subreg <filename>.rdl
```

## Contributing

### Requirements

* uv - [installation guide](https://docs.astral.sh/uv/getting-started/installation/)

### Developer Environment

A `sourceme` is provided that will setup the development environment with necessary packages
and environment variables.

```shell
. sourceme [--clean] [--upgrade]
```

Linting and formatting are enforced via [pre-commit](https://pre-commit.com/) hooks, which
are configured upon sourcing the `sourceme`.

## Alternatives

There are already many Verilog SystemRDL exporters out there including `PeakRDL-regblock`
which is maintained by the author of many of the Python tooling.

### PeakRDL-regblock

This is probably the most fully featured of the Verilog/SV exporters but it generates
SV that can't be consumed by all tools.  There is a definite verification style to the
RTL with the use of unpacked structs, interfaces, automatic variables etc.

Additionally, the code base is so complex that it took less time to implement an exporter
from scratch than to try and fix the issues.

If you need support for the majority of the SystemRDL features and have commercial EDA
tools then I'd suggest looking at this package.

### PeakRDL-verilog

There are two GitHub repos that use this name.  The original author has mostly abandonned
their own work in favour of `PeakRDL-regblock` while his work was forked and continues (?)
to be maintained here: https://github.com/bat52/PeakRDL-verilog

Both have simple to fix bugs relating to recent versions of Python but the latter project
has not enabled issues so further investigation was ruled out.

### OpenTitan RegTool

Perhaps the nicest and cleanest register tool out there is `RegTool`.  This is part of the
open source OpenTitan project and you can find the documentation here:
https://opentitan.org/book/util/reggen/index.html

The tool uses its own HJSON schema to define the registers and is somewhat simpler than
SystemRDL.  However, as it has matured, the tooling has become more and more deeply
embedded in the OT workflows with requirements for metadata driven from the IP blocks
that use it.  Extracting a generic version of this tool would be a major undertaking and
importing the Python tooling into your own project isn't clean.

On the plus side, the RTL generated is very clean with a module hierarchy that simplifies
the work needed on the Python side.

## Implementation Details

The implementation choices were made to simplify the complexity of the Python RDL
exporter.  Rather than generating a flat RTL view of the whole register file, as is
done by many of the current SystemRDL exporters, each field is instantiated as a
parameterisable Verilog module.  This vastly reduces the complexity of both the
templating and the exporter code by moving specialisation into the RTL via generate
statements.

This also happened to be the approach taken by `RegTool` which meant that much of the RTL
infrastructure could be taken and modified without much overhead.  There is a very clear
lineage from the OpenTitan work in this exporter in both the RTL and Mako templating.

### RTL Hierarchy

The hierarchy of the generated RTL is shown below:

```
 +---- <block>_reg_pkg
 |
 +---- <block>_reg_top
          |
          +---- rdl_subreg u_field_name_0
          |        |
          |        +---- rdl_subreg_arg u_arb
          |        |
          |        +---- rdl_subreg_flop u_flop
          |
          +---- rdl_subreg u_field_name_1
          |        |
          |        +---- rdl_subreg_arg u_arb
          |        |
          |        +---- rdl_subreg_flop u_flop
          |
          +---- rdl_subreg u_field_name_2
          |
          ...
```

## Limitations

The following is a list of current limitations and assumptions:

* there is a single toplevel address map
* only support for a single sw access width
* no support for register widths > access width
* no support for counters
* no support for aliases
* no support for interrupt registers
* no support for halt registers
* no support for swacc
* no support for onread side effects

Feel free to put in a pull request to add desired features which may be missing!

## Full Example

Given a register map definition `example.rdl`:

```rdl
addrmap an_addrmap {

    name = "Example register map";
    default accesswidth = 8;
    default regwidth = 8;

    regfile a_regfile {
        reg {
            field {
                hw   = r;
                sw   = rw;
            } en[1] = 0x0;
            field {
                hw   = r;
                sw   = rw;
            } sel[2] = 0x0;
        } control ;
        reg {
            name = "Status";
            desc = "Register description";
            field {
                name = "Interrupt request";
                desc = "Field description";
                hw   = w;
                sw   = r;
            } irq[1] = 0x0;
        } status ;
    } ;

    reg a_stb {
        field {
            hw = r;
            sw = w;
            swmod;
        } data[7:0] = 0x1;
    } ;

    internal a_regfile  my_regfile[2]   @ 0x0;
    internal a_stb      my_stb          @ 0xC;
};
```

Run the exporter to generate output products:

```
mkdir -p rdl && peakrdl sv --reset-polarity high --reset-type async -o rdl test.rdl
```

yielding an output directory:

```
rdl
├── an_addrmap_reg_pkg.sv
└── an_addrmap_reg_top.sv
```

Then instance in a SystemVerilog module which uses the register map as:

```sv
module my_module
  import an_addrmap_reg_pkg::*;
  import rdl_subreg_pkg::*;
(
  input  logic       clk,
  input  logic       rst,
  // CSR interface
  input  logic       reg_we,
  input  logic       reg_re,
  input  logic [3:0] reg_addr,
  input  logic [7:0] reg_wdata,
  output logic [7:0] reg_rdata,
  // External inputs
  input logic        irq,
)

  // Register access structs
  an_addrmap_reg_pkg::an_addrmap_reg2hw_t reg2hw;
  an_addrmap_reg_pkg::an_addrmap_hw2reg_t hw2reg;

  logic [1:0] sel;
  logic       en;

  an_addrmap_reg_top #(
    .ResetType(ActiveHighSync)
  ) u_csr (
    .clk,
    .rst,
    // CSR I/F
    .reg_we,
    .reg_re,
    .reg_addr,
    .reg_wdata,
    .reg_rdata,
    // HW I/F
    .reg2hw, // Write
    .hw2reg  // Read
  );

  // Read a register value into hardware
  assign sel = reg2hw.my_regfile_0_control.sel.q;
  assign en  = reg2hw.my_regfile_0_control.en.q;

  // Write to a register form hardware
  assign reg2hw.my_regfile_1_status.irq.d = irq;

endmodule;
```

The registers may be programmed from software by driving the CSR interface presented by
the `an_addrmap_reg_top` module.
