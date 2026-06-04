# Magic PEX Automation Script (Logically optimized version)

# Automatically get the name of the current top cell
set cellname [cellname list self]

if { $cellname == "(none)" || $cellname == "" } {
    puts "Error: No cell loaded. Please check if the GDS read was successful."
} else {
    puts "Starting the extraction process for cell $cellname..."

    # Step 1: Basic extraction
    puts "Step 1: Running 'extract all'..."
    extract all

    # Step 2: Parasitic resistance extraction (with error handling)
    puts "Step 2: Running 'extresis'..."
    if { [catch {extresis tolerance 10} result] } {
        puts "Warning: 'extresis' failed (The Tech file might not support resistance extraction)."
        puts "Will extract parasitic capacitance only..."
        ext2spice extresist off
    } else {
        puts "Parasitic resistance extracted successfully."
        ext2spice extresist on
    }

    # Step 3: Configure and export the netlist
    puts "Step 3: Exporting SPICE netlist..."
    ext2spice lvs
    ext2spice cthresh 0.01
    
    # Automatically name the output file based on the cell name
    ext2spice -o ${cellname}_pex.spice

    puts "----------------------------------------------"
    puts "Extraction complete!"
    puts "Output file: ${cellname}_pex.spice"
    puts "----------------------------------------------"
}