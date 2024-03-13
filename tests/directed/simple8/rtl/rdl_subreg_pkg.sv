// Copyright Nu Quantum Ltd
// SPDX-License-Identifier: MIT

package rdl_subreg_pkg;

  typedef enum logic [1:0] {
    OnReadClear = 2'b00,
    OnReadSet   = 2'b01,
    OnReadNone  = 2'b10
  } on_read_e;

  typedef enum logic [3:0] {
    OnWriteNone  = 4'b1000,
    OnWriteWoset = 4'b0000,
    OnWriteWoclr = 4'b0001,
    OnWriteWot   = 4'b0010,
    OnWriteWzs   = 4'b0011,
    OnWriteWzc   = 4'b0100,
    OnWriteWzt   = 4'b0101,
    OnWriteWclr  = 4'b0110,
    OnWriteWset  = 4'b0111
  } on_write_e;

  typedef enum int {
    ActiveHighAsync = 0,
    ActiveLowAsync  = 1,
    ActiveHighSync  = 2,
    ActiveLowSync   = 3
  } reset_type_e;

endpackage
