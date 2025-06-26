# jtagsvftb
JTAG TAP Controller TB use Run time cvs input which is translated from Serial vector format (SVF) , via gen_svf_csv.py with these colums: step, trst, tms, tdi, tdo, mask, rep_cycle  Use file IO to read  a jtag svf file named demotdr.svf and create csv to show the sequence step by step with step, trst, tms, tdi, tdo, mask bit columns in each r
