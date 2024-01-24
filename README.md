# peakrdl-sv

This SystemRDL exporter outputs SystemVerilog that is hopefully consumable by *any* 
EDA tool including the common open source simulators such as Icarus and Verilator.

The design philosophy was to keep it simple and avoid the complexity of implementing
the full SystemRDL language.  As such there are limitations on what is supported and
there are no plans to extend support beyond the basics.

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

REVISIT: flesh out this section.

The hierarchy of the generated RTL is shown below:

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



## Installation

```
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

## Limitations

The following is a list of current limitations and assumptions:

* there is a single toplevel address map
* only support for a single sw access width
* no support for register widths > access width
* no support for countrs
* no support for aliases
* no support for interrupt registers
* no support for halt registers
* no support for swacc
* no support for onread side effects
