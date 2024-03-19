// Copyright Nu Quantum Ltd
// SPDX-License-Identifier: MIT

module rdl_subreg_arb
  import rdl_subreg_pkg::*;
#(
    parameter int DW = 32,
    parameter on_read_e OnRead = OnReadNone,
    parameter on_write_e OnWrite = OnWriteNone
) (
    // From CPU
    input logic          we,
    input logic [DW-1:0] wd,

    // From HW
    input logic          de,
    input logic [DW-1:0] d,

    // From register
    input [DW-1:0] q,

    // To register
    output logic          wr_en,
    output logic [DW-1:0] wr_data
);

  if (OnRead != OnReadNone) begin : gen_read
    $error("OnRead not supported currently");
  end

  if (OnWrite == OnWriteNone) begin : gen_write
    // No special side effects; software has higher priority.
    assign wr_en   = we || de;
    assign wr_data = we ? wd : d;

  end else if (OnWrite == OnWriteWoset) begin : gen_woset
    // Write one to set
    assign wr_en   = we || de;
    assign wr_data = (de ? d : q) | (we ? wd : '0);

  end else if (OnWrite == OnWriteWoclr) begin : gen_woclr
    // Write one to clear.
    assign wr_en   = we || de;
    assign wr_data = (de ? d : q) & (we ? ~wd : '1);

  end else if (OnWrite == OnWriteWot) begin : gen_wot
    // Write one to toggle
    assign wr_en   = we || de;
    assign wr_data = (de ? d : q) ^ (we ? wd : '0);

  end else if (OnWrite == OnWriteWzs) begin : gen_wzs
    // Write zero to set
    assign wr_en   = we || de;
    assign wr_data = (de ? d : q) | (we ? ~wd : '0);

  end else if (OnWrite == OnWriteWzc) begin : gen_wzc
    // Write zero to clear
    assign wr_en   = we || de;
    assign wr_data = (de ? d : q) & (we ? wd : '1);

  end else if (OnWrite == OnWriteWzt) begin : gen_wzt
    // Write zero to toggle
    assign wr_en   = we || de;
    assign wr_data = (de ? d : q) ^ (we ? ~wd : '0);

  end else if (OnWrite == OnWriteWclr) begin : gen_wclr
    // All bits cleared on write.
    $error("wclr not supported yet");

  end else if (OnWrite == OnWriteWset) begin : gen_wset
    // All bits set on write
    $error("wset not supported yet");

  end

endmodule
