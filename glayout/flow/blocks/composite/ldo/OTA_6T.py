import sys
from os import path, rename, environ
environ['OPENBLAS_NUM_THREADS'] = '1'
from pathlib import Path
# path to glayout
sys.path.append(path.join(str(Path(__file__).resolve().parents[5])))

from gdsfactory.cell import cell, clear_cache
from gdsfactory.component import Component, copy
from gdsfactory.component_reference import ComponentReference
from gdsfactory.components.rectangle import rectangle
from glayout.flow.pdk.mappedpdk import MappedPDK
from typing import Optional, Union
from glayout.flow.primitives.fet import nmos, pmos, multiplier
from glayout.flow.blocks.elementary.diff_pair import diff_pair
from glayout.flow.primitives.guardring import tapring
from glayout.flow.primitives.mimcap import mimcap_array, mimcap
from glayout.flow.routing.L_route import L_route
from glayout.flow.routing.c_route import c_route
from glayout.flow.primitives.via_gen import via_stack, via_array
from gdsfactory.routing.route_quad import route_quad
from glayout.flow.pdk.util.comp_utils import evaluate_bbox, prec_ref_center, movex, movey, to_decimal, to_float, move, align_comp_to_port, get_padding_points_cc
from glayout.flow.pdk.util.port_utils import rename_ports_by_orientation, rename_ports_by_list, add_ports_perimeter, print_ports, set_port_orientation, rename_component_ports
from glayout.flow.routing.straight_route import straight_route
from glayout.flow.pdk.util.snap_to_grid import component_snap_to_grid
from pydantic import validate_arguments
from glayout.flow.placement.two_transistor_interdigitized import two_nfet_interdigitized

from glayout.flow.blocks.composite.diffpair_cmirror_bias import diff_pair_ibias
from glayout.flow.blocks.composite.stacked_current_mirror import stacked_nfet_current_mirror
from glayout.flow.blocks.composite.differential_to_single_ended_converter import differential_to_single_ended_converter
# from glayout.flow.blocks.composite.opamp.row_csamplifier_diff_to_single_ended_converter import row_csamplifier_diff_to_single_ended_converter
from glayout.flow.spice import Netlist
from glayout.flow.blocks.elementary.current_mirror import current_mirror_netlist


from glayout.flow.blocks.composite.pmos_active_load import pmos_load_module

@validate_arguments
def __create_and_route_pins(
    pdk: MappedPDK,
    opamp_single_top: Component,
    pmos_comps_ref: ComponentReference
) -> tuple:
    _max_metal_seperation_ps = pdk.util_max_metal_seperation()

    
    vddpin = opamp_single_top << rectangle(size=(5,3), layer=pdk.get_glayer("met4"), centered=True)
    
    vddpin.movex(opamp_single_top.ports["pcomps_welltap_N_top_met_N"].center[0]).movey(opamp_single_top.ymax + 5)
    
    
    opamp_single_top << straight_route(pdk, opamp_single_top.ports["pcomps_L_source_N"], vddpin.ports["e4"], glayer1="met4")
    
    opamp_single_top << straight_route(pdk, opamp_single_top.ports["pcomps_welltap_N_top_met_N"], vddpin.ports["e4"], glayer1="met4")

    
    vbias1 = opamp_single_top << rectangle(size=(5,3), layer=pdk.get_glayer("met3"), centered=True)
    vbias1.movey(opamp_single_top.ymin - _max_metal_seperation_ps - vbias1.ymax)
    opamp_single_top << straight_route(pdk, vbias1.ports["e2"], opamp_single_top.ports["diffpair_ibias_B_gate_S"], width=1, fullbottom=False)

    
    # (VIN-)
    minusi_pin = opamp_single_top << rectangle(size=(5,2), layer=pdk.get_glayer("met3"), centered=True)
    minusi_pin.movex(opamp_single_top.xmin-5).movey(opamp_single_top.ports["diffpair_MINUSgateroute_W_con_N"].center[1])
    iport_antenna1 = movex(minusi_pin.ports["e3"], destination=opamp_single_top.ports["diffpair_MINUSgateroute_W_con_N"].center[0]-9*_max_metal_seperation_ps)
    opamp_single_top << L_route(pdk, opamp_single_top.ports["diffpair_MINUSgateroute_W_con_N"], iport_antenna1)
    iport_antenna2 = movex(iport_antenna1, offsetx=-9*_max_metal_seperation_ps)
    opamp_single_top << straight_route(pdk, iport_antenna1, iport_antenna2, glayer1="met4", glayer2="met4", via2_alignment=('c','c'), via1_alignment=('c','c'), fullbottom=True)
    iport_antenna2.layer = pdk.get_glayer("met4")
    opamp_single_top << straight_route(pdk, iport_antenna2, minusi_pin.ports["e3"], glayer1="met3", via2_alignment=('c','c'), via1_alignment=('c','c'), fullbottom=True)

    # (VIN+)
    plusi_pin = opamp_single_top << rectangle(size=(5,2), layer=pdk.get_glayer("met3"), centered=True)
    plusi_pin.movex(opamp_single_top.xmax + 5).movey(opamp_single_top.ports["diffpair_PLUSgateroute_E_con_N"].center[1])
    iport_antenna1_p = movex(plusi_pin.ports["e3"], destination=opamp_single_top.ports["diffpair_PLUSgateroute_E_con_N"].center[0] + 9*_max_metal_seperation_ps)
    opamp_single_top << L_route(pdk, opamp_single_top.ports["diffpair_PLUSgateroute_E_con_N"], iport_antenna1_p)
    iport_antenna2_p = movex(iport_antenna1_p, offsetx=9*_max_metal_seperation_ps) 
    opamp_single_top << straight_route(pdk, iport_antenna1_p, iport_antenna2_p, glayer1="met4", glayer2="met4", via2_alignment=('c','c'), via1_alignment=('c','c'), fullbottom=True)
    iport_antenna2_p.layer = pdk.get_glayer("met4")
    opamp_single_top << straight_route(pdk, iport_antenna2_p, plusi_pin.ports["e3"], glayer1="met3", via2_alignment=('c','c'), via1_alignment=('c','c'), fullbottom=True)

    
    opamp_single_top << straight_route(
        pdk, 
        opamp_single_top.ports["diffpair_tl_multiplier_0_drain_N"], 
        opamp_single_top.ports["pcomps_L_drain_S"], 
        glayer1="met4", width=3*pdk.get_grule("met4")["min_width"]
    )
    
    
    out_route = opamp_single_top << straight_route(
        pdk, 
        opamp_single_top.ports["diffpair_tr_multiplier_0_drain_N"], 
        opamp_single_top.ports["pcomps_R_drain_S"], 
        glayer1="met4", width=3*pdk.get_grule("met4")["min_width"]
    )

    
    vout_pin = opamp_single_top << rectangle(size=(5,3), layer=pdk.get_glayer("met4"), centered=True)
    
    
    dp_drain_y = opamp_single_top.ports["diffpair_tr_multiplier_0_drain_N"].center[1]
    pmos_drain_y = opamp_single_top.ports["pcomps_R_drain_S"].center[1]
    mid_y = (dp_drain_y + pmos_drain_y) / 2
    
    
    drain_x = opamp_single_top.ports["pcomps_R_drain_S"].center[0]
    vout_pin.movex(drain_x + 10).movey(mid_y)
    
    
    horizontal_tie = opamp_single_top << rectangle(size=(10, 3 * pdk.get_grule("met4")["min_width"]), layer=pdk.get_glayer("met4"), centered=False)
    horizontal_tie.movex(drain_x).movey(mid_y - (3 * pdk.get_grule("met4")["min_width"])/2)

    
    opamp_single_top.add_ports(vddpin.get_ports_list(), prefix="pin_vdd_")
    opamp_single_top.add_ports(vbias1.get_ports_list(), prefix="pin_diffpairibias_")
    opamp_single_top.add_ports(minusi_pin.get_ports_list(), prefix="pin_minus_")
    opamp_single_top.add_ports(plusi_pin.get_ports_list(), prefix="pin_plus_")
    opamp_single_top.add_ports(vout_pin.get_ports_list(), prefix="pin_vout_")

    return opamp_single_top, out_route

def opamp_singlestage_netlist(nmos_input_netlist: Netlist, pmos_load_netlist: Netlist) -> Netlist:
    single_stage_netlist = Netlist(
        circuit_name="OPAMP_6T_OTA",
        nodes=['VDD', 'VSS', 'IB', 'VIP', 'VIN', 'VOUT']
    )

    
    single_stage_netlist.connect_netlist(
        nmos_input_netlist,
        [
            ('VP', 'VIP'),
            ('VN', 'VIN'),
            ('IBIAS', 'IB'), 
            ('VSS', 'VSS'), 
            ('B', 'VSS'),
            ('VDD1', 'DRAIN_L'), 
            ('VDD2', 'VOUT') 
        ]
    )

    
    single_stage_netlist.connect_netlist(
        pmos_load_netlist,
        [     
            ('VDD', 'VDD'),
            ('DRAIN_L', 'DRAIN_L'),
            ('DRAIN_R', 'VOUT')        
        ]
    )

    return single_stage_netlist

def opamp_6t_singlestage(
    pdk: MappedPDK,
    half_diffpair_params: tuple[float, float, int] = (10.5, 0.15, 10),
    diffpair_bias: tuple[float, float, int] = (6.3, 0.15, 6),
    half_pload: tuple[float,float,int] = (10.5,0.15,10),
    rmult: int = 2,
    with_antenna_diode_on_diffinputs: int=0
) -> Component:
    if with_antenna_diode_on_diffinputs != 0 and with_antenna_diode_on_diffinputs < 2:
        raise ValueError("number of antenna diodes should be at least 2 (or 0 to specify no diodes)")

    opamp_single_top = Component("opamp_6t_top")

    
    diffpair_i_ref = diff_pair_ibias(
        pdk, 
        half_diffpair_params, 
        diffpair_bias, 
        rmult, 
        with_antenna_diode_on_diffinputs
    )

    opamp_single_top.add(diffpair_i_ref)
    opamp_single_top.add_ports(diffpair_i_ref.get_ports_list(), prefix="diffpair_")
    opamp_single_top.info['netlist'] = diffpair_i_ref.info['netlist']
    opamp_single_top.info['netlist'].circuit_name = "INPUT_STAGE"
    
    
    gndpin = opamp_single_top << rename_ports_by_orientation(rectangle(size=(5,3),layer=pdk.get_glayer("met4"),centered=True))
    gndpin.movey(pdk.snap_to_2xgrid(opamp_single_top.ymin - pdk.util_max_metal_seperation() - gndpin.ymax))
    opamp_single_top << L_route(pdk, opamp_single_top.ports["diffpair_ibias_purposegndport"], gndpin.ports["W"])
    opamp_single_top.add_ports(gndpin.get_ports_list(), prefix="pin_gnd_")

    
    dp_drain_l_x = opamp_single_top.ports["diffpair_tl_multiplier_0_drain_N"].center[0]
    dp_drain_r_x = opamp_single_top.ports["diffpair_tr_multiplier_0_drain_N"].center[0]

    
    pmos_comps = pmos_load_module.pmos_active_load(pdk, rmult, half_pload, dp_drain_l_x, dp_drain_r_x)
    clear_cache()

    pmos_comps_ref = opamp_single_top << pmos_comps
    
    pmos_comps_ref.movey(round(opamp_single_top.ymax + pmos_comps_ref.ymax + 15))
    opamp_single_top.add_ports(pmos_comps_ref.get_ports_list(), prefix="pcomps_")

    clear_cache()
    
    
    opamp_single_top, n_to_p_output_route = __create_and_route_pins(pdk, opamp_single_top, pmos_comps_ref)

    
    opamp_single_top.info['netlist'] = opamp_singlestage_netlist(
        opamp_single_top.info['netlist'], 
        pmos_comps.info['netlist']        
    )

    
    met3_pin_layer = (pdk.get_glayer("met3")[0], 16)
    met4_pin_layer = (pdk.get_glayer("met4")[0], 16)

    pin_prefixes = {
        "pin_vdd_": ("VDD", met4_pin_layer),
        "pin_gnd_": ("VSS", met4_pin_layer),  
        "pin_vout_": ("VOUT", met4_pin_layer),
        "pin_minus_": ("VIN", met3_pin_layer),
        "pin_plus_": ("VIP", met3_pin_layer),
        "pin_diffpairibias_": ("IB", met3_pin_layer)
    }

    found_pins = set()
    for port_name, port in opamp_single_top.ports.items():
        for prefix, (label_text, layer) in pin_prefixes.items():
            if port_name.startswith(prefix) and prefix not in found_pins:
                opamp_single_top.add_label(text=label_text, position=port.center, layer=layer)
                found_pins.add(prefix) 

    return opamp_single_top

# if __name__ == "__main__":
#     from glayout.flow.pdk.sky130_mapped import sky130_mapped_pdk
    
#     print("Generating 6T OTA layout...")
    
#     my_6t_opamp = opamp_6t_singlestage(
#         pdk=sky130_mapped_pdk,
#         half_diffpair_params=(10.5, 0.15, 10),
#         diffpair_bias=(6.3, 0.15, 6),
#         half_pload=(10.5, 0.15, 1)
#     )
    
#     gds_filename = "opamp_6t_ota.gds"
#     my_6t_opamp.write_gds(gds_filename)
#     print(f"Layout successfully exported to: {path.abspath(gds_filename)}")
        
#     print("\n================ Extracted SPICE Netlist ================")
#     try:
#         netlist_str = my_6t_opamp.info['netlist'].generate_netlist()
#         print(netlist_str)
#     except AttributeError:
#         print(my_6t_opamp.info['netlist'])

if __name__ == "__main__":
    import time
    from glayout.flow.pdk.sky130_mapped import sky130_mapped_pdk
    
    # Define a list of different sizing configurations to test
    # Format: (diffpair_params, bias_params, pload_params)
    sizing_variations = [
        ((10.5, 0.15, 10), (6.3, 0.15, 6), (10.5, 0.15, 10)),  # Standard
        ((20.0, 0.15, 20), (10.0, 0.15, 10), (20.0, 0.15, 20)), # Large
        ((5.0, 0.5, 4), (4.0, 0.5, 2), (5.0, 0.5, 4))          # Long Channel
    ]

    print(f"{'Set':<5} | {'DiffPair (W/L/F)':<20} | {'Time (s)':<10}")
    print("-" * 45)

    for i, (dp, bias, pload) in enumerate(sizing_variations):
        # 1. Start timer
        start_time = time.time()
        
        # 2. Clear cache to ensure fresh generation for new parameters
        clear_cache()
        
        # 3. Generate the layout
        opamp_comp = opamp_6t_singlestage(
            pdk=sky130_mapped_pdk,
            half_diffpair_params=dp,
            diffpair_bias=bias,
            half_pload=pload
        )
        
        # 4. Write to GDS
        filename = f"opamp_6t_set_{i}.gds"
        opamp_comp.write_gds(filename)
        
        # 5. Calculate elapsed time
        elapsed_time = time.time() - start_time
        
        print(f"{i:<5} | {str(dp):<20} | {elapsed_time:.3f}s")

    print("\nAll layouts generated successfully.")