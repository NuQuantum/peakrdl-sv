module rdl_axil_to_csr
  import rdl_subreg_pkg::*;
#(
    parameter reset_type_e ResetType = ActiveHighSync,
    parameter integer      AW        = 5,
    parameter integer      DW        = 32
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

    //
    // CSR ( Register interface)
    //
    output logic          reg_we,
    output logic          reg_re,
    output logic [AW-1:0] reg_addr,
    output logic [DW-1:0] reg_wdata,
    input  logic [DW-1:0] reg_rdata
);

  parameter integer SW = $clog2(8);
  typedef enum logic [SW-1:0] {
    IDLE               = 0,
    READ,
    READ_RESPONSE,
    READ_RESPONSE_WAIT,
    WRITE_WAIT_DATA,
    WRITE_WAIT_ADDR,
    WRITE_RESP,
    WRITE_RESP_WAIT
  } state_t;

  state_t          state_q;
  state_t          state_d;

  logic   [AW-1:0] addr_q;
  logic   [AW-1:0] addr_d;

  logic   [DW-1:0] read_data_q;
  logic   [DW-1:0] read_data_d;

  logic   [DW-1:0] write_data_q;
  logic   [DW-1:0] write_data_d;

  // register sequential logic
  assign reg_we         = (state_q == WRITE_RESP);
  assign reg_re         = (state_q == READ);
  assign reg_addr       = addr_q;
  assign reg_wdata      = write_data_q;

  // AXI Lite interface
  assign s_axil_awready = (state_q == IDLE) || (state_q == WRITE_WAIT_ADDR);
  assign s_axil_wready  = (state_q == IDLE) || (state_q == WRITE_WAIT_DATA);
  assign s_axil_arready = (state_q == IDLE);

  assign s_axil_rdata   = read_data_q;
  assign s_axil_rvalid  = (state_q == READ_RESPONSE) || (state_q == READ_RESPONSE_WAIT);

  assign s_axil_bvalid  = (state_q == WRITE_RESP) || (state_q == WRITE_RESP_WAIT);

  assign s_axil_rresp   = 2'b00;  // OKAY
  assign s_axil_bresp   = 2'b00;  // OKAY

  always_comb begin
    state_d      = state_q;
    addr_d       = addr_q;
    read_data_d  = read_data_q;
    write_data_d = write_data_q;

    case (state_q)
      IDLE: begin
        if (s_axil_awvalid) begin
          addr_d = s_axil_awaddr;
          if (s_axil_wvalid) begin
            state_d      = WRITE_RESP;
            write_data_d = s_axil_wdata;
          end else begin
            state_d = WRITE_WAIT_DATA;
          end
        end else if (s_axil_arvalid) begin
          state_d = READ;
          addr_d  = s_axil_araddr;
        end else if (s_axil_wvalid) begin
          state_d      = WRITE_WAIT_ADDR;
          write_data_d = s_axil_wdata;
        end
      end

      READ: begin
        state_d     = READ_RESPONSE;
        read_data_d = reg_rdata;
      end

      READ_RESPONSE: begin
        if (s_axil_rready) begin
          state_d = IDLE;
        end else begin
          state_d = READ_RESPONSE_WAIT;
        end
      end

      READ_RESPONSE_WAIT: begin
        if (s_axil_rready) begin
          state_d = IDLE;
        end
      end

      WRITE_WAIT_DATA: begin
        if (s_axil_wvalid) begin
          state_d      = WRITE_RESP;
          write_data_d = s_axil_wdata;
        end
      end

      WRITE_WAIT_ADDR: begin
        if (s_axil_awvalid) begin
          state_d = WRITE_RESP;
          addr_d  = s_axil_awaddr;
        end
      end

      WRITE_RESP: begin
        if (s_axil_bready) begin
          state_d = IDLE;
        end else begin
          state_d = WRITE_RESP_WAIT;
        end
      end

      WRITE_RESP_WAIT: begin
        if (s_axil_bready) begin
          state_d = IDLE;
        end
      end

      default: begin
        state_d = IDLE;
      end

    endcase
  end

  rdl_subreg_flop #(
      .DW       (SW),
      .ResetType(ResetType)
  ) u_state_flop (
      .clk(clk),
      .rst(rst),
      .de (1'b1),
      .d  (state_d),
      .q  (state_q)
  );

  rdl_subreg_flop #(
      .DW       (AW),
      .ResetType(ResetType)
  ) u_addr_flop (
      .clk(clk),
      .rst(rst),
      .de (1'b1),
      .d  (addr_d),
      .q  (addr_q)
  );

  rdl_subreg_flop #(
      .DW       (DW),
      .ResetType(ResetType)
  ) u_w_data_flop (
      .clk(clk),
      .rst(rst),
      .de (1'b1),
      .d  (write_data_d),
      .q  (write_data_q)
  );

  rdl_subreg_flop #(
      .DW       (DW),
      .ResetType(ResetType)
  ) u_r_data_flop (
      .clk(clk),
      .rst(rst),
      .de (1'b1),
      .d  (read_data_d),
      .q  (read_data_q)
  );

endmodule
