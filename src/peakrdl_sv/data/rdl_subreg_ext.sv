// Copyright Nu Quantum Ltd
// SPDX-License-Identifier: MIT

module rdl_subreg_ext #(
    parameter int DW = 32
) (
    // inputs from SW
    input          re,
    input          we,
    input [DW-1:0] wd,

    // inputs from HW
    input [DW-1:0] d,  // extern flop q output

    // output to HW
    output logic          qe,   // asserted on SW write
    output logic          qre,  // asserted on SW read
    output logic [DW-1:0] q,    // data written by SW

    // output to SW
    output logic [DW-1:0] qs
);

  // The register is implemented externally.
  assign qs  = d;
  assign q   = wd;
  assign qe  = we;
  assign qre = re;

endmodule
