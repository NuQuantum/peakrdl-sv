// Copyright Nu Quantum Ltd
// SPDX-License-Identifier: MIT

module rdl_subreg_flop
  import rdl_subreg_pkg::*;
#(
    parameter int                   DW         = 32,
    parameter reset_type_e          ResetType  = ActiveHighAsync,
    parameter logic        [DW-1:0] ResetValue = '0
) (
    input  logic          clk,
    input  logic          rst,
    input  logic [DW-1:0] d,
    input  logic          de,
    output logic [DW-1:0] q
);

  if (ResetType == ActiveHighAsync) begin : gen_aha
    always_ff @(posedge clk or posedge rst) begin
      if (rst) begin
        q <= ResetValue;
      end else begin
        q <= de ? d : q;
      end
    end
  end else if (ResetType == ActiveHighSync) begin : gen_ahs
    always_ff @(posedge clk) begin
      if (rst) begin
        q <= ResetValue;
      end else begin
        q <= de ? d : q;
      end
    end
  end else if (ResetType == ActiveLowAsync) begin : gen_ala
    always_ff @(posedge clk or negedge rst) begin
      if (!rst) begin
        q <= ResetValue;
      end else begin
        q <= de ? d : q;
      end
    end
  end else if (ResetType == ActiveLowSync) begin : gen_als
    always_ff @(posedge clk) begin
      if (!rst) begin
        q <= ResetValue;
      end else begin
        q <= de ? d : q;
      end
    end
  end

endmodule
