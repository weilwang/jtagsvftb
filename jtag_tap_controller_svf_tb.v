/////////////////////////////////////////////////////////////////////
////                                                             ////
////  jtag_tap_controller_svf_tb.v                               ////
////                                                             ////
////  For SVF verification of the JTAG Test Access Port (TAP)    ////
////  Author: Weili Wang                                         ////
////          weili.wang@rubylili.com                            ////
////                                                             ////
////  Downloaded from:  https://www.edaplayground.com/x/Cj7v     ////
/////////////////////////////////////////////////////////////////////
////                                                             ////
//// Copyright (C) 2025 RUBYLILI INC.                            ////
//// www.rubylili.com                                            ////
//// weili.wang@rubylili.com                                     ////
////                                                             ////
//// This source file may be used and distributed without        ////
//// restriction provided that this copyright statement is not   ////
//// removed from the file and that any derivative work contains ////
//// the original copyright notice and the associated disclaimer.////
////                                                             ////
//// This source file is free software; you can redistribute it  ////
//// and/or modify it under the terms of the GNU Lesser General  ////
//// Public License as published by the Free Software Foundation.////
////                                                             ////
//// This source is distributed in the hope that it will be      ////
//// useful, but WITHOUT ANY WARRANTY; without even the implied  ////
//// warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR     ////
//// PURPOSE.  See the GNU Lesser General Public License for more////
//// details. http://www.gnu.org/licenses/lgpl.html              ////
////                                                             ////
/////////////////////////////////////////////////////////////////////
//---------------------------------------------------------
// svf --> demotdr.vec as run time input
// UVM 1.2
// Compile Options: +UVM -timescale=1ns/1ns +vcs+flush+all +warn=all -sverilog
// Run Options example: +TCK_PERIOD=200 +VECFILE=demotdrfi.vec
//---------------------------------------------------------
`timescale 1ns / 1ps
`define PRE_CYC 10  // PRE CYCLE NUM before reading the vector
`define POST_CYC 10 // POST CYCLE NUM after reading the vector
`define PERIOD              100ns  // default 100ns tck period
`define MARGIN_FRACTION 10 // Fraction of clk for margin

module jtag_tap_controller_svf_tb;

    integer in,mon;
    integer statusI,statusO;
  
    // Inputs
    reg tck;
    reg trst;
    reg tms;
    reg ptdi;
    reg tdi;
    reg exptdo;
    reg mask;
    integer step,repcyc;
    string vecfile, vecout, msg,line_from_file;

    // Outputs
    wire tdo;
    wire [7:0] ir_out;
    wire shift_ir;
    wire shift_dr;
    wire update_ir;
    wire update_dr;
    wire capture_dr;

    // Instantiate the JTAG TAP Controller
    tap_top uut (
      
                // JTAG pads
                .tms_pad_i(tms), 
                .tck_pad_i(tck), 
                .trst_pad_i(!trst), // opposit polarity
                .tdi_pad_i(tdi), 
                .tdo_pad_o(tdo), 
                .tdo_padoe_o(),

                // TAP states
                .shift_dr_o(shift_dr),
                .pause_dr_o(), 
                .update_dr_o(update_dr),
                .capture_dr_o(),
                
                // Select signals for boundary scan or mbist
                .extest_select_o(), 
                .sample_preload_select_o(),
                .mbist_select_o(),
                .debug_select_o(),
                
                // TDO signal that is connected to TDI of sub-modules.
                .tdo_o(), 
                
                // TDI signals from sub-modules
                .debug_tdi_i(1'b0),    // from debug module
                .bs_chain_tdi_i(1'b0), // from Boundary Scan Chain
                .mbist_tdi_i(1'b0)     // from Mbist Chain
    );
    
    initial begin
      tck = 0;
      trst = 0;
      tms = 1;
      tdi = 0;
      ptdi = 0;
      step = 0;
      repcyc = 0;
      exptdo= 0;
      
      vecfile = "demotdr.csv";
      if($value$plusargs("VECFILE=%s", vecfile))
        `uvm_info("PARSE", $sformatf("+VECFILE:%s",vecfile),UVM_MEDIUM)
      else
        `uvm_warning("RUNOPT", 
                     $sformatf("+VECFILE is not passed, use %s as default", vecfile));
      
      vecout = "demotdr.vecout";
      if($value$plusargs("VECOUT=%s", vecout))
        `uvm_info("PARSE", $sformatf("+VECOUT:%s",vecout),UVM_MEDIUM)
      else
        `uvm_warning("RUNOPT",
                     $sformatf("+VECOUT is not passed, use demotdr.vecout as default"));
  		 
      in  = $fopen(vecfile,"r");
      mon = $fopen(vecout,"w");
      if (in == 0) `uvm_fatal("FILE", $sformatf("Failed to open %s", vecfile));
      if (mon == 0) `uvm_fatal("FILE", $sformatf("Failed to open %s", vecout));
    end
  
  // Clock generation (default TCK: 10 MHz, 100ns period, per SVF FREQUENCY 1.00E7 HZ)
    realtime t_period, arg_period;
    initial begin
      t_period = `PERIOD;
      if ($value$plusargs("TCK_PERIOD=%f",arg_period))
        t_period = arg_period *1ns;
      else
        `uvm_warning("RUNOPT", 
                     $sformatf("+TCK_PERIOD is not passed, use %f NS as default",`PERIOD));
      
      `uvm_info("TCKGEN", $sformatf("TCK Period is set to %f NS", t_period),UVM_MEDIUM)
    end
    integer i_fraction, arg_fraction;
    initial begin
      i_fraction = `MARGIN_FRACTION;
      if ($value$plusargs("MARGIN_FRACTION=%d",arg_fraction))
        i_fraction = arg_fraction;
      else
        `uvm_warning("RUNOPT", 
                     $sformatf("+MARGIN_FRACTION is not passed, use %d as default",`MARGIN_FRACTION));
      if (i_fraction == 0) `uvm_fatal("CONFIG", "MARGIN_FRACTION cannot be zero"); 
      `uvm_info("TCKGEN", $sformatf("MARGIN_FRACTION is set to %d for TDO setup time margin", i_fraction),UVM_MEDIUM)
    end
    always #(t_period/2) tck = ~tck;
 
    always @ (posedge tck) begin
      tdi <= #(t_period/i_fraction) ptdi;
    end
  
 // DUT input driver code
    initial begin
      repeat (`PRE_CYC) @ (posedge tck);
      if (!$feof(in) && $fgets(line_from_file, in)) begin
        `uvm_info("PARSE",$sformatf("Columns:%s",line_from_file),UVM_MEDIUM)
      end
      while ( ! $feof(in)) begin
        @ (negedge tck);
        statusI = $fscanf(in,
          "%d,%b,%b,%b,%b,%b,%d\n",step, trst, tms, ptdi, exptdo, mask, repcyc);
        if (statusI != 7) `uvm_error("PARSE", $sformatf("Invalid vector line: %s", line_from_file));
        `uvm_info("PARSE",
                  $sformatf("STEP=%d TRST=%b TMS=%b TDI=%b EXPTDO=%b MASK=%b REPCYC=%d", step, trst, tms, ptdi, exptdo, mask, repcyc),UVM_MEDIUM)
        #(t_period/i_fraction) 
        if (mask==1&& tdo!==exptdo) begin
          `uvm_error("RUN",
                     $sformatf("MISMATCH STEP=%d TRST=%b TMS=%b TDI=%b EXPTDO=%b MASK=%b REPCYC=%d", step, trst, tms, ptdi, exptdo, mask, repcyc));
        end
        statusO = $fwrite(mon, "STEP=%d TRST=%b TMS=%b TDI=%b TDO=%b EXPTDO=%b MASK=%b REPCYC=%d\n",
        step, trst, tms, ptdi, tdo, exptdo, mask, repcyc);
        if (statusO == 0) `uvm_error("FILE", "Failed to write to vecout");
        repeat (repcyc-1) @ (negedge tck);
      end
      $fclose(in);
      $fclose(mon);
      repeat (`POST_CYC) @ (posedge tck);
      #100  $finish;
 end
   
    // Dump waveform
    initial begin
        $dumpfile("jtag_tap_controller_svf_tb.vcd");
        $dumpvars(0, jtag_tap_controller_svf_tb);
    end

endmodule