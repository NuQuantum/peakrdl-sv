module rdl_axil_to_reg
  import rdl_subreg_pkg::*;
#(
  parameter reset_type_e ResetType = ActiveHighSync,
  parameter int AW                = 6,
  parameter int DW                = 8
) (
  input logic clk,
  input logic rst,

  //
  // AXI Lite slave interface
  //
  // AXI Lite address write channel
  output logic                s_axil_awready,
  input  wire                 s_axil_awvalid,
  input  wire  [      AW-1:0] s_axil_awaddr,
  // AXI Lite write data channel
  output logic                s_axil_wready,
  input  wire                 s_axil_wvalid,
  input  wire  [      DW-1:0] s_axil_wdata,
  input  wire  [(DW / 8)-1:0] s_axil_wstrb,
  // AXI Lite write response channel
  input  wire                 s_axil_bready,
  output logic                s_axil_bvalid,
  output logic [         1:0] s_axil_bresp,
  // AXI Lite address read channel
  output logic                s_axil_arready,
  input  wire                 s_axil_arvalid,
  input  wire  [      AW-1:0] s_axil_araddr,
  // AXI Lite read data channel
  input  wire                 s_axil_rready,
  output logic                s_axil_rvalid,
  output logic [      DW-1:0] s_axil_rdata,
  output logic [         1:0] s_axil_rresp,

  output logic                reg_we,
  output logic                reg_re,
  output logic [AW-1:0]       reg_waddr,
  output logic [AW-1:0]       reg_raddr,
  output logic [DW-1:0]       reg_wdata,
  input  logic [DW-1:0]       reg_rdata
);

  logic [AW-1:0] w_addr_q, w_addr_d;
  logic [DW-1:0] w_data_q, w_data_d;
  logic          w_en_q, w_en_d;
  logic          b_valid_q, b_valid_d;



  typedef enum logic [1:0] {
    W_IDLE,
    W_WAIT_DATA,
    W_WAIT_ADDRESS
  } write_state_t;
  write_state_t w_state_q, w_state_d;

  assign s_axil_bresp = 2'b00; // OKAY
  assign s_axil_wready = (w_state_q == W_IDLE || w_state_q == W_WAIT_DATA);
  assign s_axil_awready = (w_state_q == W_IDLE || w_state_q == W_WAIT_ADDRESS);
  assign s_axil_bvalid = b_valid_q;

  assign reg_we    = w_en_q;
  assign reg_waddr = w_addr_q;
  assign reg_wdata = w_data_q;

  always_comb begin
    w_state_d = w_state_q;
    w_en_d     = 1'b0;
    w_addr_d   = w_addr_q;
    w_data_d   = w_data_q;
    b_valid_d = b_valid_q;

    if (s_axil_bready) begin
      b_valid_d = 1'b0;
    end

    case (w_state_q)
      W_IDLE: begin
        if (s_axil_awvalid && s_axil_wvalid) begin
          w_data_d = s_axil_wdata;
          w_addr_d = s_axil_awaddr;
          w_en_d   = 1'b1;
          b_valid_d = 1'b1;

          w_state_d = W_IDLE;
        end
        else if (s_axil_awvalid) begin
          w_addr_d = s_axil_awaddr;
          w_state_d = W_WAIT_DATA;
        end
        else if (s_axil_wvalid) begin
          w_data_d = s_axil_wdata;
          w_state_d = W_WAIT_ADDRESS;
        end
      end
      W_WAIT_DATA: begin
        if (s_axil_wvalid) begin
          w_data_d = s_axil_wdata;
          w_en_d   = 1'b1;
          b_valid_d = 1'b1;

          w_state_d = W_IDLE;
        end
      end
      W_WAIT_ADDRESS: begin
        if (s_axil_awvalid) begin
          w_addr_d = s_axil_awaddr;
          w_en_d   = 1'b1;
          b_valid_d = 1'b1;

          w_state_d = W_IDLE;
        end
      end
      default: begin
        w_state_d = W_IDLE;
      end
    endcase
  end

  rdl_subreg_flop #(
      .DW(2),
      .ResetType(ResetType),
      .ResetValue(W_IDLE)
  ) u_w_state_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (w_state_d),
      .q (w_state_q)
  );

  rdl_subreg_flop #(
      .DW(AW),
      .ResetType(ResetType),
      .ResetValue('0)
  ) u_w_addr_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (w_addr_d),
      .q (w_addr_q)
  );

  rdl_subreg_flop #(
      .DW(DW),
      .ResetType(ResetType),
      .ResetValue('0)
  ) u_w_data_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (w_data_d),
      .q (w_data_q)
  );

  rdl_subreg_flop #(
      .DW(1),
      .ResetType(ResetType),
      .ResetValue(1'b0)
  ) u_w_en_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (w_en_d),
      .q (w_en_q)
  );

  rdl_subreg_flop #(
      .DW(1),
      .ResetType(ResetType),
      .ResetValue(1'b0)
  ) u_b_valid_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (b_valid_d),
      .q (b_valid_q)
  );



  //----------------------------------
  // Read channel
  //----------------------------------

  logic [AW-1:0] r_addr_q, r_addr_d;
  logic [DW-1:0] r_data_q, r_data_d;
  logic          r_en_q, r_en_d;
  logic          r_valid_q, r_valid_d;

  assign s_axil_rresp = 2'b00; // OKAY
  assign s_axil_rvalid = r_valid_q;
  assign s_axil_rdata = r_data_q;
  assign s_axil_arready = 1'b1;

  assign reg_re    = r_en_q;
  assign reg_raddr = r_addr_q;

  always_comb begin
    r_en_d     = 1'b0;
    r_addr_d   = r_addr_q;
    r_data_d   = r_data_q;
    r_valid_d  = r_valid_q;

    if (s_axil_rready) begin
      r_valid_d = 1'b0;
    end

    if (s_axil_arvalid) begin
      r_addr_d = s_axil_araddr;
      r_en_d   = 1'b1;
    end

    if (r_en_q) begin
      r_valid_d = 1'b1;
      r_data_d = reg_rdata;
    end
  end



  rdl_subreg_flop #(
      .DW(AW),
      .ResetType(ResetType),
      .ResetValue('0)
  ) u_r_addr_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (r_addr_d),
      .q (r_addr_q)
  );

  rdl_subreg_flop #(
      .DW(DW),
      .ResetType(ResetType),
      .ResetValue('0)
  ) u_r_data_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (r_data_d),
      .q (r_data_q)
  );

  rdl_subreg_flop #(
      .DW(1),
      .ResetType(ResetType),
      .ResetValue(1'b0)
  ) u_r_en_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (r_en_d),
      .q (r_en_q)
  );

  rdl_subreg_flop #(
      .DW(1),
      .ResetType(ResetType),
      .ResetValue(1'b0)
  ) u_r_valid_flop (
      .clk(clk),
      .rst(rst),
      .de(1'b1),
      .d (r_valid_d),
      .q (r_valid_q)
  );



endmodule
