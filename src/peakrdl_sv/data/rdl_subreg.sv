// Copyright Shareef Jalloq
// SPDX-License-Identifier: MIT

module rdl_subreg
  import rdl_subreg_pkg::*;
#(
    parameter int                   DW         = 32,
    parameter reset_type_e          ResetType  = ActiveHighAsync,
    parameter logic        [DW-1:0] ResetValue = '0,
    parameter on_read_e             OnRead     = OnReadNone,
    parameter on_write_e            OnWrite    = OnWriteNone
) (
    input logic clk,
    input logic rst,

    // From CPU
    input logic          we,
    input logic [DW-1:0] wd,

    // From HW
    input logic          de,
    input logic [DW-1:0] d,

    // Output to HW
    output logic [DW-1:0] q,
    output logic          qe,

    // Output to CPU
    output logic [DW-1:0] qs
);

  logic          wr_en;
  logic [DW-1:0] wr_data;

  rdl_subreg_arb #(
      .DW     (DW),
      .OnRead (OnRead),
      .OnWrite(OnWrite)
  ) u_arb (
      .we(we),
      .wd(wd),
      .de(de),
      .d(d),
      .q(q),
      .wr_en(wr_en),
      .wr_data(wr_data)
  );

  rdl_subreg_flop #(
      .DW(DW),
      .ResetType(ResetType),
      .ResetValue(ResetValue)
  ) u_flop (
      .clk(clk),
      .rst(rst),
      .de (wr_en),
      .d  (wr_data),
      .q  (q)
  );

  assign qs = q;  // REVISIT: look at OnReadClear race condition for SW/HW simultaneous access.
  assign qe = wr_en;  // REVISIT: qe needs to be asserted on read with side effects.

endmodule
