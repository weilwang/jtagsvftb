import re
import csv

# JTAG state machine transitions from RTI
RTI_TO_SHIFTIR = [(1, "SELECT-DR"), (1, "SELECT-IR"), (0, "CAPTURE-IR"), (0, "SHIFT-IR")]
RTI_TO_SHIFTDR = [(0, "SELECT-DR"), (1, "SELECT-IR"), (0, "CAPTURE-DR"), (0, "SHIFT-DR")]
SHIFT_TO_RTI = [(1, "EXIT1"), (1, "UPDATE"), (0, "RUN-TEST/IDLE")]

def hex_to_binary(hex_str, length):
    """Convert hex string to binary string, little-endian, padded to length."""
    binary = bin(int(hex_str, 16))[2:].zfill(length)[::-1]  # Reverse for little-endian
    return binary

def parse_svf_file(filename):
    steps = []
    step_counter = 0
    current_state = "RESET"
    trst = 1  # TRST OFF default

    with open(filename, 'r') as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip().split('//')[0].strip()  # Remove comments and whitespace
        if not line:
            continue

        # Parse TRST commands
        if line.startswith("TRST ON"):
            trst = 0
            steps.append((step_counter, trst, 0, 0, 0, 0, 1, "TRST ON"))
            step_counter += 1
        elif line.startswith("TRST OFF"):
            trst = 1
            steps.append((step_counter, trst, 0, 0, 0, 0, 1, "TRST OFF"))
            step_counter += 1

        # Parse STATE commands
        elif line.startswith("STATE"):
            target_state = line.split()[1].rstrip(';')
            if target_state == "RESET":
                steps.append((step_counter, trst, 1, 0, 0, 0, 5, "STATE RESET"))
                step_counter += 5  # 5 TMS=1 pulses to ensure RESET
                current_state = "RESET"
            elif target_state == "IDLE":
                if current_state != "IDLE":
                    steps.append((step_counter, trst, 0, 0, 0, 0, 1, "STATE IDLE"))
                    step_counter += 1
                    current_state = "IDLE"

        # Parse SIR command
        elif line.startswith("SIR"):
            match = re.match(r'SIR (\d+) TDI \(([\da-fA-F]+)\) SMASK \(([\da-fA-F]+)\) TDO \(([\da-fA-F]+)\) MASK \(([\da-fA-F]+)\)', line)
            if match:
                length = int(match.group(1))
                tdi_hex = match.group(2)
                smask_hex = match.group(3)
                tdo_hex = match.group(4)
                mask_hex = match.group(5)

                tdi_bin = hex_to_binary(tdi_hex, length)
                smask_bin = hex_to_binary(smask_hex, length)
                tdo_bin = hex_to_binary(tdo_hex, length)
                mask_bin = hex_to_binary(mask_hex, length)

                # Transition from IDLE to SHIFT-IR
                for tms, state_name in RTI_TO_SHIFTIR:
                    steps.append((step_counter, trst, tms, 0, 0, 0, 1, f"Move to {state_name}"))
                    step_counter += 1

                # Shift data
                for i in range(length):
                    tdi = int(tdi_bin[i])
                    tdo = int(tdo_bin[i]) if smask_bin[i] == '1' else 0
                    mask = int(smask_bin[i])  # Use SMASK for SIR
                    steps.append((step_counter, trst, 0, tdi, tdo, mask, 1, "Shift IR"))
                    step_counter += 1

                # Transition back to IDLE
                for tms, state_name in SHIFT_TO_RTI:
                    steps.append((step_counter, trst, tms, 0, 0, 0, 1, f"Move to {state_name}"))
                    step_counter += 1
                current_state = "IDLE"

        # Parse SDR command
        elif line.startswith("SDR"):
            match = re.match(r'SDR (\d+) TDI \(([\da-fA-F]+)\) SMASK \(([\da-fA-F]+)\) TDO \(([\da-fA-F]+)\) MASK \(([\da-fA-F]+)\)', line)
            if match:
                length = int(match.group(1))
                tdi_hex = match.group(2)
                smask_hex = match.group(3)
                tdo_hex = match.group(4)
                mask_hex = match.group(5)

                tdi_bin = hex_to_binary(tdi_hex, length)
                smask_bin = hex_to_binary(smask_hex, length)
                tdo_bin = hex_to_binary(tdo_hex, length)
                mask_bin = hex_to_binary(mask_hex, length)

                # Transition from IDLE to SHIFT-DR
                for tms, state_name in RTI_TO_SHIFTDR:
                    steps.append((step_counter, trst, tms, 0, 0, 0, 1, f"Move to {state_name}"))
                    step_counter += 1

                # Shift data
                for i in range(length):
                    tdi = int(tdi_bin[i])
                    tdo = int(tdo_bin[i]) if mask_bin[i] == '1' else 0
                    mask = int(mask_bin[i])
                    steps.append((step_counter, trst, 0, tdi, tdo, mask, 1, "Shift DR"))
                    step_counter += 1

                # Transition back to IDLE
                for tms, state_name in SHIFT_TO_RTI:
                    steps.append((step_counter, trst, tms, 0, 0, 0, 1, f"Move to {state_name}"))
                    step_counter += 1
                current_state = "IDLE"

        # Parse RUNIDLE command
        elif line.startswith("RUNIDLE"):
            repeat = int(line.split()[1])
            steps.append((step_counter, trst, 0, 0, 0, 0, repeat, "RUNIDLE"))
            step_counter += repeat

    return steps

def consolidate_steps(steps):
    consolidated = []
    i = 0
    while i < len(steps):
        step, trst, tms, tdi, tdo, mask, repeat, comment = steps[i]
        if mask != 1 and repeat == 1 and comment in ["Shift IR", "Shift DR"]:
            # Look ahead for identical rows to consolidate
            count = 1
            j = i + 1
            while j < len(steps):
                next_step = steps[j]
                if (next_step[1:] == (trst, tms, tdi, tdo, mask, 1, comment)):
                    count += 1
                    j += 1
                else:
                    break
            consolidated.append((step, trst, tms, tdi, tdo, mask, count, comment))
            i = j
        else:
            consolidated.append((step, trst, tms, tdi, tdo, mask, repeat, comment))
            i += 1
    return consolidated

def write_csv(steps, output_filename):
    with open(output_filename, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["step", "trst", "tms", "tdi", "tdo", "mask", "repeat"])
        for step, trst, tms, tdi, tdo, mask, repeat, _ in steps:
            writer.writerow([step, trst, tms, tdi, tdo, mask, repeat])

def main():
    input_file = "demotdr.svf"
    output_file = "demotdr.csv"
    steps = parse_svf_file(input_file)
    consolidated_steps = consolidate_steps(steps)
    write_csv(consolidated_steps, output_file)

if __name__ == "__main__":
    main()