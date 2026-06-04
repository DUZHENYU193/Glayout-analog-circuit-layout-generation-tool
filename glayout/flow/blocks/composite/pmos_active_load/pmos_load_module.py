from gdsfactory.cell import clear_cache
from gdsfactory.component import Component
from gdsfactory.components.rectangle import rectangle
from glayout.flow.pdk.mappedpdk import MappedPDK
from glayout.flow.primitives.fet import multiplier
from glayout.flow.routing.straight_route import straight_route
from glayout.flow.spice import Netlist
from glayout.flow.primitives.guardring import tapring
from glayout.flow.pdk.util.comp_utils import evaluate_bbox
from pydantic import validate_arguments

def pmos_active_load_netlist(pdk: MappedPDK, half_pload: tuple[float, float, int]) -> Netlist:
    """2 PMOS Active Load Netlist Generator"""
    return Netlist(
        circuit_name="PMOS_ACTIVE_LOAD",
        nodes=['VDD', 'DRAIN_L', 'DRAIN_R'],
        source_netlist="""
.subckt {circuit_name} {nodes}
XM_L DRAIN_L DRAIN_L VDD VDD {model} l={length} w={width} m={mult}
XM_R DRAIN_R DRAIN_L VDD VDD {model} l={length} w={width} m={mult}
.ends {circuit_name}
        """,
        parameters={
            'model': pdk.models['pfet'],
            'width': half_pload[0],
            'length': half_pload[1],
            'mult': half_pload[2]
        }
    )

@validate_arguments
def pmos_active_load(
    pdk: MappedPDK, 
    rmult: int, 
    half_pload: tuple[float,float,int], 
    dp_drain_l_x: float, 
    dp_drain_r_x: float
) -> Component:
    """
    2-PMOS Active Load Module with Guard Ring and NWELL Background
    """
    top = Component("pmos_active_load")
    clear_cache()
    
    
    pmos_L = multiplier(pdk, "p+s/d", width=half_pload[0], length=half_pload[1], fingers=half_pload[2], rmult=rmult)
    pmos_R = multiplier(pdk, "p+s/d", width=half_pload[0], length=half_pload[1], fingers=half_pload[2], rmult=rmult)
    
    pref_L = top << pmos_L
    pref_R = top << pmos_R
    
    
    pref_L.movex(dp_drain_l_x - pref_L.ports["drain_S"].center[0])
    pref_R.movex(dp_drain_r_x - pref_R.ports["drain_S"].center[0])
    
    
    top << straight_route(pdk, pref_L.ports["source_E"], pref_R.ports["source_W"], glayer1="met2") # 源极短接
    top << straight_route(pdk, pref_L.ports["gate_E"], pref_R.ports["gate_W"], glayer1="met2")   # 栅极短接
    top << straight_route(pdk, pref_L.ports["drain_W"], pref_L.ports["gate_W"], glayer1="met3")  # 左侧二极管连接
    
    
    tap_padding = max(0.4 + pdk.get_grule("n+s/d", "active_tap")["min_enclosure"], pdk.util_max_metal_seperation())
    tring_bbox = evaluate_bbox(top, padding=tap_padding)
    
    
    tring_ref = top << tapring(pdk, tring_bbox, "n+s/d", "met1", "met1")
    top.add_ports(tring_ref.get_ports_list(), prefix="welltap_")

    
    nwell_padding = pdk.get_grule("active_tap", "nwell")["min_enclosure"]
    nwell_width = (tring_ref.xmax - tring_ref.xmin) + 2 * nwell_padding
    nwell_height = (tring_ref.ymax - tring_ref.ymin) + 2 * nwell_padding
    
    
    nwell_rect = top << rectangle(size=(nwell_width, nwell_height), layer=pdk.get_glayer("nwell"), centered=True)
    nwell_rect.movex(tring_ref.center[0]).movey(tring_ref.center[1])
    
    
    top.add_ports(pref_L.get_ports_list(), prefix="L_")
    top.add_ports(pref_R.get_ports_list(), prefix="R_")
    
    
    top.info['netlist'] = pmos_active_load_netlist(pdk, half_pload)
    return top