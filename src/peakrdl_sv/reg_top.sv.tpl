// Copyright Nu Quantum Ltd
// SPDX-License-Identifier: MIT
//
// Auto-generated by peakrdl-sv
<%
  from systemrdl.rdltypes import OnReadType, OnWriteType

  lblock = block.inst_name.lower()
  ublock = block.inst_name.upper()

  addr_width = block.addrwidth
  data_width = block.accesswidth
  registers  = block.get_registers()

  # Construct a dict that contains useful signal names that would otherwise
  # have to be computed in multiple places.
  idx = 0
  reg_enables = {}
  for r in registers:
    key = r.path().lower()
    reg_enables[key] = {}
    reg_enables[key]['idx'] = idx
    reg_enables[key]['we']  = []
    reg_enables[key]['re']  = []

    if r.is_wide:
      # If the regwidth > accesswidth, then we need multiple read/write enables.
      for s in range(r.subregs):
        if r.has_sw_writable:
          reg_enables[key]['we'].append( f"{r.path().lower()}_{s}_we" )
        if r.has_sw_readable:
          reg_enables[key]['re'].append( f"{r.path().lower()}_{s}_re" )
    else:
      # If regwidth == accesswidth, then we have a single read/write enable.
      if r.has_sw_writable:
        reg_enables[key]['we'].append( f"{r.path().lower()}_we" )
      if r.has_sw_readable:
        reg_enables[key]['re'].append( f"{r.path().lower()}_re" )

    # Increase the index by the subreg count.  The index of each addressable
    # node is used to construct the addr_hit vector below.
    idx += r.subregs

  # The total number of addressable registers includes all sub-registers.
  num_regs = idx
  max_regs_char = len("{}".format(num_regs-1))

%>

module ${lblock}_reg_top
  import rdl_subreg_pkg::*;
#(
  parameter reset_type_e ResetType = ActiveHighSync
) (
  input logic clk,
  input logic rst,

  // Bus I/F
  // REVISIT: hacked to the Migen CSR bus for now.
  input logic csr_we,
  input logic csr_re,
  input logic [31:0] csr_addr,
  input logic [7:0] csr_wdata,
  output logic [7:0] csr_rdata,

  // HW I/F
  output ${lblock}_reg_pkg::${lblock}_reg2hw_t reg2hw, // Write
  input  ${lblock}_reg_pkg::${lblock}_hw2reg_t hw2reg  // Read

);

  import ${lblock}_reg_pkg::*;

  localparam int AW  = ${addr_width};
  localparam int DW  = ${data_width};
  localparam int DBW = DW/8;

  // --------------------------------------------------------------------------------
  // Logic Declarations
  // --------------------------------------------------------------------------------

  logic           reg_we;
  logic           reg_re;
  logic [AW-1:0]  reg_addr;
  logic [DW-1:0]  reg_wdata;
  logic [DBW-1:0] reg_wstrb;
  logic [DW-1:0]  reg_rdata;


  // --------------------------------------------------------------------------------
  // REVISIT: temporary hack
  // --------------------------------------------------------------------------------

  assign reg_we    = csr_we;
  assign reg_re    = csr_re;
  assign reg_addr  = csr_addr[AW-1:0];
  assign reg_wdata = csr_wdata;
  assign reg_wstrb = '1;
  assign csr_rdata = reg_rdata;


  // --------------------------------------------------------------------------------
  // Software Logic Declarations
  // --------------------------------------------------------------------------------

  % for r in registers:
  % if r.has_hw_readable:
  % for enable in reg_enables[r.path().lower()]['re']:
  logic ${enable};
  % endfor
  % endif
  % if r.has_sw_writable:
  % for enable in reg_enables[r.path().lower()]['we']:
  logic ${enable};
  % endfor
  % for f in r:
  logic ${sv_bitarray(f)} ${f.path().lower()}_wd;
  % endfor
  % endif
  % endfor

  // --------------------------------------------------------------------------------
  // Field Logic
  // --------------------------------------------------------------------------------

  % for i,r in enumerate(registers):
  % for f in r:
<%
  if len(r) == 1:
    struct_path = f"{r.path()}"
  else:
    struct_path = f"{r.path()}.{f.inst_name}"

  subreg_idx = f.msb // r.accesswidth

  if r.is_wide:
    we_expr = reg_enables[r.path().lower()]['we'][subreg_idx] if f.is_sw_writable else ""
    re_expr = reg_enables[r.path().lower()]['re'][subreg_idx] if f.needs_qre else ""
  else:
    we_expr = f"{r.path().lower()}_we" if f.is_sw_writable else ""
    re_expr = f"{r.path().lower()}_re" if f.needs_qre else ""

  wd_expr = f"{f.path().lower()}_wd" if f.is_sw_writable else ""
  qs_expr = f"{f.path().lower()}_qs" if f.is_sw_readable else ""

  de_expr = f"hw2reg.{struct_path}.de" if f.is_hw_writable else "'0"
  d_expr  = f"hw2reg.{struct_path}.d"  if f.is_hw_writable else "'0"

  q_expr   = f"reg2hw.{struct_path}.q"  if f.is_hw_readable else ""
  qe_expr  = f"reg2hw.{struct_path}.qe" if f.needs_qe else ""
  qre_expr = f"reg2hw.{struct_path}.re" if f.needs_qre else ""

%>\
  // Register[${r.name}] Field[${f.name}] Bits[${f.get_bit_slice()}]
  % if f.is_sw_readable:
  logic ${sv_bitarray(f)} ${qs_expr};
  % endif
  % if r.external:
  // Register[${r.name}] Field[${f.name}] Bits[${f.get_bit_slice()}]
  rdl_subreg_ext #(
    .DW (${f.width})
  ) u_${f.path().lower()} (
    .re  (${re_expr}),
    .we  (${we_expr}),
    .wd  (${wd_expr}),
    .d   (${d_expr}),
    .qe  (${qe_expr}),
    .qre (${qre_expr}),
    .q   (${q_expr}),
    .qs  (${qs_expr})
  );
  % else:
  rdl_subreg #(
    .DW         (${f.width}),
    .ResetType  (ResetType),
    .ResetValue (${reset_gen(f)}),
    .OnRead     (${onread_gen(f)}),
    .OnWrite    (${onwrite_gen(f)})
  ) u_${f.path().lower()} (
    .clk (clk),
    .rst (rst),
    .re  (${re_expr}),
    .we  (${we_expr}),
    .wd  (${wd_expr}),
    .de  (${de_expr}),
    .d   (${d_expr}),
    .qs  (${qs_expr}),
    .qe  (${qe_expr}),
    .qre (${qre_expr}),
    .q   (${q_expr})
  );
  % endif

  % endfor
  % endfor

  // --------------------------------------------------------------------------------
  // Address Decode
  // --------------------------------------------------------------------------------

  logic [${num_regs-1}:0] addr_hit;
  always_comb begin
    addr_hit = '0;
    % for i,r in enumerate(registers):
<%
    write_enables = reg_enables[r.path().lower()]['we']
    base_idx = reg_enables[r.path().lower()]['idx']
%>\
    % for i in range(r.subregs):
<%
    justified = "{}".format(base_idx+i).rjust(max_regs_char)
    param = f"{ublock}_{r.path().upper()}_" + (f"{i}_" if r.is_wide else "") + "OFFSET"
%>\
    addr_hit[${justified}] = (reg_addr == ${param});
    % endfor
    % endfor
  end

  // --------------------------------------------------------------------------------
  // Write Enables
  // --------------------------------------------------------------------------------

  % for i,r in enumerate(registers):
    % if r.has_sw_writable:
${register_we_gen(r,i)}\
    % endif
  % if len(r) == 1:
${field_wd_gen(r[0])}\
  % else:
    % for f in r:
${field_wd_gen(f)}\
    % endfor
  % endif
  % endfor

  // --------------------------------------------------------------------------------
  // Read Data Mux
  // --------------------------------------------------------------------------------

  always_comb begin
    reg_rdata = '0;
    unique case (1'b1)
  % for i, r in enumerate(registers):
<%
    idx = reg_enables[r.path().lower()]['idx']
%>\
    % if r.is_wide:
      % for i in range(r.subregs):
      addr_hit[${idx+i}]: begin
        % for f in r.get_subreg_fields(i):
${rdata_gen(f)}\
        % endfor
      end
      % endfor
    % else:
      addr_hit[${idx}]: begin
      % for f in r:
${rdata_gen(f)}\
      % endfor
      end
    % endif
  % endfor
      default: begin
        reg_rdata = 'X;
      end
    endcase
  end

endmodule
<%def name="register_we_gen(reg, idx)">\
<%
  write_enables = reg_enables[reg.path().lower()]['we']
  read_enables  = reg_enables[reg.path().lower()]['re']
  idx           = reg_enables[reg.path().lower()]['idx']
%>\
  % for i,enable in enumerate(write_enables):
  assign ${enable} = addr_hit[${idx+i}] && reg_we;
  % endfor
  % for i,enable in enumerate(read_enables):
  assign ${enable} = addr_hit[${idx+i}] && reg_re;
  % endfor
## REVISIT: this is the old code pre wide-reg support.  Remove once above works.
## <%def name="reg_enable_gen(reg, idx)">\
##   % if reg.has_sw_writable:
##   assign ${reg.path().lower()}_we = addr_hit[${idx}] && reg_we;
##   % endif
##   % if reg.has_sw_readable:
##   assign ${reg.path().lower()}_re = addr_hit[${idx}] && reg_re;
##   % endif
</%def>\
<%def name="field_wd_gen(field)">\
  % if field.is_sw_writable:
  assign ${field.path().lower()}_wd = reg_wdata[${field.get_cpuif_bit_slice()}];
  % endif
</%def>\
<%def name="rdata_gen(field, rd_name='reg_rdata')">\
% if field.is_sw_readable:
        ${rd_name}[${field.get_cpuif_bit_slice()}] = ${field.path().lower()}_qs;
% else:
        ${rd_name}[${field.get_cpuif_bit_slice()}] = '0;
% endif
</%def>\
<%def name="onwrite_gen(field)" filter="trim">\
  % if field.onwrite == None:
OnWriteNone
  % elif isinstance(field.onwrite, OnWriteType.woset):
OnWriteWoset
  % elif isinstance(field.onwrite, OnWriteType.woclr):
OnWriteWoclr
  % elif isinstance(field.onwrite, OnWriteType.wot):
OnWriteWot
  % elif isinstance(field.onwrite, OnWriteType.wzs):
OnWriteWzs
  % elif isinstance(field.onwrite, OnWriteType.wzc):
OnWriteWzc
  % elif isinstance(field.onwrite, OnWriteType.wzt):
OnWriteWzt
  % elif isinstance(field.onwrite, OnWriteType.wclr):
OnWriteWclr
  % elif isinstance(field.onwrite, OnWriteType.wset):
OnWriteWset
  % endif
</%def>\
<%def name="onread_gen(field)" filter="trim">\
OnReadNone
</%def>\
<%def name="reset_gen(field)" filter="trim">\
${field.width}'d${field.reset or 0}
</%def>\
<%def name="sv_bitarray(field)" filter="trim">\
% if field.width > 1:
[${field.width-1}:0]
% endif
</%def>\
