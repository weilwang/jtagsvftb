import csv
import re
import os

def parse_svf_to_csv(svf_filename, csv_filename):
    # Initialize variables
    steps = []
    step_count = 0
    trst = 1  # TRST OFF default
    tms = 0   # Default TMS
    tdi = 0   # Default TDI
    tdo = 0   # Default TDO
    mask = 0  # Default MASK
    repeat_count = 1
    prev_row = None
    endir_state = 'IDLE'  # Default ENDIR
    enddr_state = 'IDLE'  # Default ENDDR

    # Read SVF file
    if not os.path.exists(svf_filename):
        raise FileNotFoundError(f"SVF file {svf_filename} not found")
    
    with open(svf_filename, 'r') as svf_file:
        lines = svf_file.readlines()

    # Process each line
    for line in lines:
        line = line.strip().rstrip(';')
        if not line or line.startswith('//'):
            continue

        # Handle TRST commands
        if line == 'TRST ON':
            trst = 0
            steps.append([step_count, trst, tms, tdi, tdo, mask, repeat_count])
            step_count += 1
            repeat_count = 1
            prev_row = [trst, tms, tdi, tdo, mask]
        elif line == 'TRST OFF':
            trst = 1
            steps.append([step_count, trst, tms, tdi, tdo, mask, repeat_count])
            step_count += 1
            repeat_count = 1
            prev_row = [trst, tms, tdi, tdo, mask]
        # Handle ENDIR and ENDDR
        elif line.startswith('ENDIR'):
            endir_state = line.split()[1]
            continue  # No direct effect on sequence
        elif line.startswith('ENDDR'):
            enddr_state = line.split()[1]
            continue  # No direct effect on sequence
        # Handle STATE commands
        elif line.startswith('STATE'):
            state = line.split()[1]
            if state == 'RESET':
                # TMS sequence for RESET: 11111 (5 cycles)
                tms_sequence = [1] * 5
            elif state == 'IDLE':
                # TMS sequence for IDLE: 0 (1 cycle)
                tms_sequence = [0]
            else:
                continue

            for tms_val in tms_sequence:
                if prev_row and prev_row == [trst, tms_val, tdi, tdo, mask] and mask == 0:
                    steps[-1][-1] += 1  # Increment repeat count
                else:
                    steps.append([step_count, trst, tms_val, tdi, tdo, mask, repeat_count])
                    step_count += 1
                    repeat_count = 1
                    prev_row = [trst, tms_val, tdi, tdo, mask]
        # Handle SIR command
        elif line.startswith('SIR'):
            match = re.match(r'SIR (\d+) TDI \(([0-9a-fA-F]+)\).*SMASK \(([0-9a-fA-F]+)\).*TDO \(([0-9a-fA-F]+)\).*MASK \(([0-9a-fA-F]+)\)', line)
            if match:
                length = int(match.group(1))
                tdi_val = int(match.group(2), 16)
                smask_val = int(match.group(3), 16)
                tdo_val = int(match.group(4), 16)
                mask_val = int(match.group(5), 16)

                # TMS for SIR: 11 (Select-DR-Scan, Select-IR-Scan) + 0*(length) + 11 (Exit1-IR, Update-IR)
                tms_sequence = [1, 1, 0, 0] + [0] * length + [1, 1]
                # If ENDIR is IDLE, add TMS=0,0 to reach IDLE after Update-IR
                if endir_state == 'IDLE':
                    tms_sequence.extend([0, 0])

                for i in range(len(tms_sequence)):
                    tms = tms_sequence[i]
                    # Little-endian: LSB shifted first
                    tdi_bit = (tdi_val >> (i - 4)) & 1 if 4 <= i < length + 4 else 0
                    tdo_bit = (tdo_val >> (i - 4)) & 1 if 4 <= i < length + 4 else 0
                    mask_bit = (mask_val >> (i - 4)) & 1 if 4 <= i < length + 4 else 0
                    if prev_row and prev_row == [trst, tms, tdi_bit, tdo_bit, mask_bit] and mask_bit == 0:
                        steps[-1][-1] += 1
                    else:
                        steps.append([step_count, trst, tms, tdi_bit, tdo_bit, mask_bit, repeat_count])
                        step_count += 1
                        repeat_count = 1
                        prev_row = [trst, tms, tdi_bit, tdo_bit, mask_bit]
        # Handle SDR command
        elif line.startswith('SDR'):
            match = re.match(r'SDR (\d+) TDI \(([0-9a-fA-F]+)\).*SMASK \(([0-9a-fA-F]+)\).*TDO \(([0-9a-fA-F]+)\).*MASK \(([0-9a-fA-F]+)\)', line)
            if match:
                length = int(match.group(1))
                tdi_val = int(match.group(2), 16)
                smask_val = int(match.group(3), 16)
                tdo_val = int(match.group(4), 16)
                mask_val = int(match.group(5), 16)

                # TMS for SDR: 10 (Select-DR-Scan, Shift-DR) + 0*(length) + 11 (Exit1-DR, Update-DR)
                tms_sequence = [1, 0, 0] + [0] * length + [1, 1]
                # If ENDDR is IDLE, add TMS=0,0 to reach IDLE after Update-DR
                if enddr_state == 'IDLE':
                    tms_sequence.extend([0, 0])

                for i in range(len(tms_sequence)):
                    tms = tms_sequence[i]
                    # Little-endian: LSB shifted first
                    tdi_bit = (tdi_val >> (i - 3)) & 1 if 3 <= i < length + 3 else 0
                    tdo_bit = (tdo_val >> (i - 3)) & 1 if 3 <= i < length + 3 else 0
                    mask_bit = (mask_val >> (i - 3)) & 1 if 3 <= i < length + 3 else 0
                    if prev_row and prev_row == [trst, tms, tdi_bit, tdo_bit, mask_bit] and mask_bit == 0:
                        steps[-1][-1] += 1
                    else:
                        steps.append([step_count, trst, tms, tdi_bit, tdo_bit, mask_bit, repeat_count])
                        step_count += 1
                        repeat_count = 1
                        prev_row = [trst, tms, tdi_bit, tdo_bit, mask_bit]
        # Handle RUNIDLE command
        elif line.startswith('RUNIDLE'):
            match = re.match(r'RUNIDLE (\d+)', line)
            if match:
                cycles = int(match.group(1))
                tms_sequence = [0] * cycles  # Stay in Run-Test/Idle with TMS=0
                for tms_val in tms_sequence:
                    if prev_row and prev_row == [trst, tms_val, tdi, tdo, mask] and mask == 0:
                        steps[-1][-1] += 1  # Increment repeat count
                    else:
                        steps.append([step_count, trst, tms_val, tdi, tdo, mask, repeat_count])
                        step_count += 1
                        repeat_count = 1
                        prev_row = [trst, tms_val, tdi, tdo, mask]
    
    # Write to CSV
    with open(csv_filename, 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['step', 'TRST', 'TMS', 'TDI', 'TDO', 'MASK', 'Repeat'])
        for step in steps:
            writer.writerow(step)

# File paths
svf_filename = 'demotdr.svf'
csv_filename = 'demotdr.csv'

# Write SVF file
with open(svf_filename, 'w') as svf_file:
    svf_file.write('''// Example JTAG SVF file 
TRST ON;
TRST OFF;
ENDIR IDLE;
ENDDR IDLE;
STATE RESET;
STATE IDLE;
FREQUENCY 1E4 HZ;
TIR 0;
HIR 0;
TDR 0;
HDR 0;
// Check idcode
SIR 4 TDI (2) SMASK (f) TDO (5) MASK (f);
SDR 32 TDI (deadbeef) SMASK (ffffffff) TDO (149511c3) MASK (ffffffff);
RUNIDLE 102
''')

# Generate CSV
parse_svf_to_csv(svf_filename, csv_filename)