module afifo #(parameter W = 16, A = 4)(input wclk, wrst, we, input [W-1:0] wd, output full,
                                       input rclk, rrst, re, output [W-1:0] rd, output empty);
  reg [W-1:0] mem [0:(1<<A)-1];
  reg [A:0] wbin, wgray, rbin, rgray, wq1, wq2, rq1, rq2;
  wire [A:0] wbin_n = wbin + (we & ~full), rbin_n = rbin + (re & ~empty);
  wire [A:0] wgray_n = (wbin_n >> 1) ^ wbin_n, rgray_n = (rbin_n >> 1) ^ rbin_n;
  always @(posedge wclk) if (wrst) begin wbin <= 0; wgray <= 0; end else begin
    if (we & ~full) mem[wbin[A-1:0]] <= wd;
    wbin <= wbin_n; wgray <= wgray_n; end
  always @(posedge rclk) if (rrst) begin rbin <= 0; rgray <= 0; end else begin rbin <= rbin_n; rgray <= rgray_n; end
  always @(posedge wclk) if (wrst) {wq2, wq1} <= 0; else {wq2, wq1} <= {wq1, rgray};  // read ptr into write domain
  always @(posedge rclk) if (rrst) {rq2, rq1} <= 0; else {rq2, rq1} <= {rq1, wgray};  // write ptr into read domain
  assign full = (wgray == {~wq2[A:A-1], wq2[A-2:0]});
  assign empty = (rgray == rq2);
  assign rd = mem[rbin[A-1:0]];
endmodule
