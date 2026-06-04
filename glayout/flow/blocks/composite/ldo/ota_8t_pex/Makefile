# 定义变量
GDS_FILE = opamp_8t_ota.gds
TOP_CELL = opamp_single_top
PEX_SCRIPT = extract_pex.tcl

all: pex

pex:
	@echo "Creating temporary magic command file..."
	@echo "gds read $(GDS_FILE)" > temp_magic_cmd.tcl
	@echo "load $(TOP_CELL)" >> temp_magic_cmd.tcl
	@echo "select top cell" >> temp_magic_cmd.tcl
	@echo "source $(PEX_SCRIPT)" >> temp_magic_cmd.tcl
	@echo "quit" >> temp_magic_cmd.tcl
	@echo "Starting Parasitic Extraction..."
	magic -dnull -noconsole temp_magic_cmd.tcl
	@rm temp_magic_cmd.tcl
	@echo "Extraction flow finished."

clean:
	@echo "Cleaning up..."
	rm -f *.ext *.resis *.bak *_pex.spice temp_magic_cmd.tcl

.PHONY: all pex clean