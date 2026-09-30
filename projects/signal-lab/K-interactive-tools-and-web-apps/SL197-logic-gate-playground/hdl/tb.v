`timescale 1ns/1ps
module tb;
  reg [1:0] x0; wire o0_0; wire o0_1; wire o0_2;
  c0 u0(.i0(x0[1]), .i1(x0[0]), .o0(o0_0), .o1(o0_1), .o2(o0_2));
  reg [3:0] x1; wire o1_0; wire o1_1; wire o1_2;
  c1 u1(.i0(x1[3]), .i1(x1[2]), .i2(x1[1]), .i3(x1[0]), .o0(o1_0), .o1(o1_1), .o2(o1_2));
  reg [4:0] x2; wire o2_0; wire o2_1; wire o2_2;
  c2 u2(.i0(x2[4]), .i1(x2[3]), .i2(x2[2]), .i3(x2[1]), .i4(x2[0]), .o0(o2_0), .o1(o2_1), .o2(o2_2));
  reg [1:0] x3; wire o3_0; wire o3_1; wire o3_2;
  c3 u3(.i0(x3[1]), .i1(x3[0]), .o0(o3_0), .o1(o3_1), .o2(o3_2));
  reg [3:0] x4; wire o4_0; wire o4_1; wire o4_2;
  c4 u4(.i0(x4[3]), .i1(x4[2]), .i2(x4[1]), .i3(x4[0]), .o0(o4_0), .o1(o4_1), .o2(o4_2));
  reg [2:0] x5; wire o5_0; wire o5_1; wire o5_2;
  c5 u5(.i0(x5[2]), .i1(x5[1]), .i2(x5[0]), .o0(o5_0), .o1(o5_1), .o2(o5_2));
  reg [3:0] x6; wire o6_0; wire o6_1; wire o6_2;
  c6 u6(.i0(x6[3]), .i1(x6[2]), .i2(x6[1]), .i3(x6[0]), .o0(o6_0), .o1(o6_1), .o2(o6_2));
  reg [3:0] x7; wire o7_0; wire o7_1; wire o7_2;
  c7 u7(.i0(x7[3]), .i1(x7[2]), .i2(x7[1]), .i3(x7[0]), .o0(o7_0), .o1(o7_1), .o2(o7_2));
  reg [1:0] x8; wire o8_0; wire o8_1; wire o8_2;
  c8 u8(.i0(x8[1]), .i1(x8[0]), .o0(o8_0), .o1(o8_1), .o2(o8_2));
  reg [4:0] x9; wire o9_0; wire o9_1; wire o9_2;
  c9 u9(.i0(x9[4]), .i1(x9[3]), .i2(x9[2]), .i3(x9[1]), .i4(x9[0]), .o0(o9_0), .o1(o9_1), .o2(o9_2));
  reg [4:0] x10; wire o10_0; wire o10_1; wire o10_2;
  c10 u10(.i0(x10[4]), .i1(x10[3]), .i2(x10[2]), .i3(x10[1]), .i4(x10[0]), .o0(o10_0), .o1(o10_1), .o2(o10_2));
  reg [3:0] x11; wire o11_0; wire o11_1; wire o11_2;
  c11 u11(.i0(x11[3]), .i1(x11[2]), .i2(x11[1]), .i3(x11[0]), .o0(o11_0), .o1(o11_1), .o2(o11_2));
  reg [3:0] x12; wire o12_0; wire o12_1; wire o12_2;
  c12 u12(.i0(x12[3]), .i1(x12[2]), .i2(x12[1]), .i3(x12[0]), .o0(o12_0), .o1(o12_1), .o2(o12_2));
  reg [2:0] x13; wire o13_0; wire o13_1; wire o13_2;
  c13 u13(.i0(x13[2]), .i1(x13[1]), .i2(x13[0]), .o0(o13_0), .o1(o13_1), .o2(o13_2));
  reg [5:0] x14; wire o14_0; wire o14_1; wire o14_2;
  c14 u14(.i0(x14[5]), .i1(x14[4]), .i2(x14[3]), .i3(x14[2]), .i4(x14[1]), .i5(x14[0]), .o0(o14_0), .o1(o14_1), .o2(o14_2));
  reg [4:0] x15; wire o15_0; wire o15_1; wire o15_2;
  c15 u15(.i0(x15[4]), .i1(x15[3]), .i2(x15[2]), .i3(x15[1]), .i4(x15[0]), .o0(o15_0), .o1(o15_1), .o2(o15_2));
  reg [5:0] x16; wire o16_0; wire o16_1; wire o16_2;
  c16 u16(.i0(x16[5]), .i1(x16[4]), .i2(x16[3]), .i3(x16[2]), .i4(x16[1]), .i5(x16[0]), .o0(o16_0), .o1(o16_1), .o2(o16_2));
  reg [4:0] x17; wire o17_0; wire o17_1; wire o17_2;
  c17 u17(.i0(x17[4]), .i1(x17[3]), .i2(x17[2]), .i3(x17[1]), .i4(x17[0]), .o0(o17_0), .o1(o17_1), .o2(o17_2));
  reg [1:0] x18; wire o18_0; wire o18_1; wire o18_2;
  c18 u18(.i0(x18[1]), .i1(x18[0]), .o0(o18_0), .o1(o18_1), .o2(o18_2));
  reg [3:0] x19; wire o19_0; wire o19_1; wire o19_2;
  c19 u19(.i0(x19[3]), .i1(x19[2]), .i2(x19[1]), .i3(x19[0]), .o0(o19_0), .o1(o19_1), .o2(o19_2));
  reg [2:0] x20; wire o20_0; wire o20_1; wire o20_2;
  c20 u20(.i0(x20[2]), .i1(x20[1]), .i2(x20[0]), .o0(o20_0), .o1(o20_1), .o2(o20_2));
  reg [2:0] x21; wire o21_0; wire o21_1; wire o21_2;
  c21 u21(.i0(x21[2]), .i1(x21[1]), .i2(x21[0]), .o0(o21_0), .o1(o21_1), .o2(o21_2));
  reg [5:0] x22; wire o22_0; wire o22_1; wire o22_2;
  c22 u22(.i0(x22[5]), .i1(x22[4]), .i2(x22[3]), .i3(x22[2]), .i4(x22[1]), .i5(x22[0]), .o0(o22_0), .o1(o22_1), .o2(o22_2));
  reg [2:0] x23; wire o23_0; wire o23_1; wire o23_2;
  c23 u23(.i0(x23[2]), .i1(x23[1]), .i2(x23[0]), .o0(o23_0), .o1(o23_1), .o2(o23_2));
  reg [3:0] x24; wire o24_0; wire o24_1; wire o24_2;
  c24 u24(.i0(x24[3]), .i1(x24[2]), .i2(x24[1]), .i3(x24[0]), .o0(o24_0), .o1(o24_1), .o2(o24_2));
  reg [4:0] x25; wire o25_0; wire o25_1; wire o25_2;
  c25 u25(.i0(x25[4]), .i1(x25[3]), .i2(x25[2]), .i3(x25[1]), .i4(x25[0]), .o0(o25_0), .o1(o25_1), .o2(o25_2));
  reg [1:0] x26; wire o26_0; wire o26_1; wire o26_2;
  c26 u26(.i0(x26[1]), .i1(x26[0]), .o0(o26_0), .o1(o26_1), .o2(o26_2));
  reg [5:0] x27; wire o27_0; wire o27_1; wire o27_2;
  c27 u27(.i0(x27[5]), .i1(x27[4]), .i2(x27[3]), .i3(x27[2]), .i4(x27[1]), .i5(x27[0]), .o0(o27_0), .o1(o27_1), .o2(o27_2));
  reg [1:0] x28; wire o28_0; wire o28_1; wire o28_2;
  c28 u28(.i0(x28[1]), .i1(x28[0]), .o0(o28_0), .o1(o28_1), .o2(o28_2));
  reg [1:0] x29; wire o29_0; wire o29_1; wire o29_2;
  c29 u29(.i0(x29[1]), .i1(x29[0]), .o0(o29_0), .o1(o29_1), .o2(o29_2));
  reg [5:0] x30; wire o30_0; wire o30_1; wire o30_2;
  c30 u30(.i0(x30[5]), .i1(x30[4]), .i2(x30[3]), .i3(x30[2]), .i4(x30[1]), .i5(x30[0]), .o0(o30_0), .o1(o30_1), .o2(o30_2));
  reg [1:0] x31; wire o31_0; wire o31_1; wire o31_2;
  c31 u31(.i0(x31[1]), .i1(x31[0]), .o0(o31_0), .o1(o31_1), .o2(o31_2));
  reg [3:0] x32; wire o32_0; wire o32_1; wire o32_2;
  c32 u32(.i0(x32[3]), .i1(x32[2]), .i2(x32[1]), .i3(x32[0]), .o0(o32_0), .o1(o32_1), .o2(o32_2));
  reg [5:0] x33; wire o33_0; wire o33_1; wire o33_2;
  c33 u33(.i0(x33[5]), .i1(x33[4]), .i2(x33[3]), .i3(x33[2]), .i4(x33[1]), .i5(x33[0]), .o0(o33_0), .o1(o33_1), .o2(o33_2));
  reg [1:0] x34; wire o34_0; wire o34_1; wire o34_2;
  c34 u34(.i0(x34[1]), .i1(x34[0]), .o0(o34_0), .o1(o34_1), .o2(o34_2));
  reg [3:0] x35; wire o35_0; wire o35_1; wire o35_2;
  c35 u35(.i0(x35[3]), .i1(x35[2]), .i2(x35[1]), .i3(x35[0]), .o0(o35_0), .o1(o35_1), .o2(o35_2));
  reg [1:0] x36; wire o36_0; wire o36_1;
  c36 u36(.a(x36[1]), .b(x36[0]), .s(o36_0), .c(o36_1));
  reg [2:0] x37; wire o37_0; wire o37_1;
  c37 u37(.a(x37[2]), .b(x37[1]), .cin(x37[0]), .s(o37_0), .cout(o37_1));
  reg [2:0] x38; wire o38_0;
  c38 u38(.s(x38[2]), .d0(x38[1]), .d1(x38[0]), .y(o38_0));
  reg [1:0] x39; wire o39_0;
  c39 u39(.a(x39[1]), .b(x39[0]), .y(o39_0));
  integer m;
  initial begin
    for (m = 0; m < 4; m = m + 1) begin x0 = m; #1; $display("ROW 0 %0d %0d%0d%0d", m, o0_0, o0_1, o0_2); end
    for (m = 0; m < 16; m = m + 1) begin x1 = m; #1; $display("ROW 1 %0d %0d%0d%0d", m, o1_0, o1_1, o1_2); end
    for (m = 0; m < 32; m = m + 1) begin x2 = m; #1; $display("ROW 2 %0d %0d%0d%0d", m, o2_0, o2_1, o2_2); end
    for (m = 0; m < 4; m = m + 1) begin x3 = m; #1; $display("ROW 3 %0d %0d%0d%0d", m, o3_0, o3_1, o3_2); end
    for (m = 0; m < 16; m = m + 1) begin x4 = m; #1; $display("ROW 4 %0d %0d%0d%0d", m, o4_0, o4_1, o4_2); end
    for (m = 0; m < 8; m = m + 1) begin x5 = m; #1; $display("ROW 5 %0d %0d%0d%0d", m, o5_0, o5_1, o5_2); end
    for (m = 0; m < 16; m = m + 1) begin x6 = m; #1; $display("ROW 6 %0d %0d%0d%0d", m, o6_0, o6_1, o6_2); end
    for (m = 0; m < 16; m = m + 1) begin x7 = m; #1; $display("ROW 7 %0d %0d%0d%0d", m, o7_0, o7_1, o7_2); end
    for (m = 0; m < 4; m = m + 1) begin x8 = m; #1; $display("ROW 8 %0d %0d%0d%0d", m, o8_0, o8_1, o8_2); end
    for (m = 0; m < 32; m = m + 1) begin x9 = m; #1; $display("ROW 9 %0d %0d%0d%0d", m, o9_0, o9_1, o9_2); end
    for (m = 0; m < 32; m = m + 1) begin x10 = m; #1; $display("ROW 10 %0d %0d%0d%0d", m, o10_0, o10_1, o10_2); end
    for (m = 0; m < 16; m = m + 1) begin x11 = m; #1; $display("ROW 11 %0d %0d%0d%0d", m, o11_0, o11_1, o11_2); end
    for (m = 0; m < 16; m = m + 1) begin x12 = m; #1; $display("ROW 12 %0d %0d%0d%0d", m, o12_0, o12_1, o12_2); end
    for (m = 0; m < 8; m = m + 1) begin x13 = m; #1; $display("ROW 13 %0d %0d%0d%0d", m, o13_0, o13_1, o13_2); end
    for (m = 0; m < 64; m = m + 1) begin x14 = m; #1; $display("ROW 14 %0d %0d%0d%0d", m, o14_0, o14_1, o14_2); end
    for (m = 0; m < 32; m = m + 1) begin x15 = m; #1; $display("ROW 15 %0d %0d%0d%0d", m, o15_0, o15_1, o15_2); end
    for (m = 0; m < 64; m = m + 1) begin x16 = m; #1; $display("ROW 16 %0d %0d%0d%0d", m, o16_0, o16_1, o16_2); end
    for (m = 0; m < 32; m = m + 1) begin x17 = m; #1; $display("ROW 17 %0d %0d%0d%0d", m, o17_0, o17_1, o17_2); end
    for (m = 0; m < 4; m = m + 1) begin x18 = m; #1; $display("ROW 18 %0d %0d%0d%0d", m, o18_0, o18_1, o18_2); end
    for (m = 0; m < 16; m = m + 1) begin x19 = m; #1; $display("ROW 19 %0d %0d%0d%0d", m, o19_0, o19_1, o19_2); end
    for (m = 0; m < 8; m = m + 1) begin x20 = m; #1; $display("ROW 20 %0d %0d%0d%0d", m, o20_0, o20_1, o20_2); end
    for (m = 0; m < 8; m = m + 1) begin x21 = m; #1; $display("ROW 21 %0d %0d%0d%0d", m, o21_0, o21_1, o21_2); end
    for (m = 0; m < 64; m = m + 1) begin x22 = m; #1; $display("ROW 22 %0d %0d%0d%0d", m, o22_0, o22_1, o22_2); end
    for (m = 0; m < 8; m = m + 1) begin x23 = m; #1; $display("ROW 23 %0d %0d%0d%0d", m, o23_0, o23_1, o23_2); end
    for (m = 0; m < 16; m = m + 1) begin x24 = m; #1; $display("ROW 24 %0d %0d%0d%0d", m, o24_0, o24_1, o24_2); end
    for (m = 0; m < 32; m = m + 1) begin x25 = m; #1; $display("ROW 25 %0d %0d%0d%0d", m, o25_0, o25_1, o25_2); end
    for (m = 0; m < 4; m = m + 1) begin x26 = m; #1; $display("ROW 26 %0d %0d%0d%0d", m, o26_0, o26_1, o26_2); end
    for (m = 0; m < 64; m = m + 1) begin x27 = m; #1; $display("ROW 27 %0d %0d%0d%0d", m, o27_0, o27_1, o27_2); end
    for (m = 0; m < 4; m = m + 1) begin x28 = m; #1; $display("ROW 28 %0d %0d%0d%0d", m, o28_0, o28_1, o28_2); end
    for (m = 0; m < 4; m = m + 1) begin x29 = m; #1; $display("ROW 29 %0d %0d%0d%0d", m, o29_0, o29_1, o29_2); end
    for (m = 0; m < 64; m = m + 1) begin x30 = m; #1; $display("ROW 30 %0d %0d%0d%0d", m, o30_0, o30_1, o30_2); end
    for (m = 0; m < 4; m = m + 1) begin x31 = m; #1; $display("ROW 31 %0d %0d%0d%0d", m, o31_0, o31_1, o31_2); end
    for (m = 0; m < 16; m = m + 1) begin x32 = m; #1; $display("ROW 32 %0d %0d%0d%0d", m, o32_0, o32_1, o32_2); end
    for (m = 0; m < 64; m = m + 1) begin x33 = m; #1; $display("ROW 33 %0d %0d%0d%0d", m, o33_0, o33_1, o33_2); end
    for (m = 0; m < 4; m = m + 1) begin x34 = m; #1; $display("ROW 34 %0d %0d%0d%0d", m, o34_0, o34_1, o34_2); end
    for (m = 0; m < 16; m = m + 1) begin x35 = m; #1; $display("ROW 35 %0d %0d%0d%0d", m, o35_0, o35_1, o35_2); end
    for (m = 0; m < 4; m = m + 1) begin x36 = m; #1; $display("ROW 36 %0d %0d%0d", m, o36_0, o36_1); end
    for (m = 0; m < 8; m = m + 1) begin x37 = m; #1; $display("ROW 37 %0d %0d%0d", m, o37_0, o37_1); end
    for (m = 0; m < 8; m = m + 1) begin x38 = m; #1; $display("ROW 38 %0d %0d", m, o38_0); end
    for (m = 0; m < 4; m = m + 1) begin x39 = m; #1; $display("ROW 39 %0d %0d", m, o39_0); end
    $finish;
  end
endmodule
