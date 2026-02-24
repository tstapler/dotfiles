import pytest
from unittest.mock import patch, MagicMock
import display_switch

# Sample xrandr --verbose output
XRANDR_OUTPUT_1 = """
Screen 0: minimum 8 x 8, current 7440 x 3240, maximum 32767 x 32767
HDMI-0 connected 1920x1080+3146+0 (0x1cc) normal (normal left inverted right x axis y axis) 620mm x 340mm
	Identifier: 0x1bc
	Timestamp:  760126363
	Subpixel:   unknown
   1920x1080 (0x1cc) 60.00*+ 119.88    75.00    50.00
DP-0 connected primary 2560x2880+0+360 (0x1e4) left (normal left inverted right x axis y axis) 465mm x 523mm
	Identifier: 0x1e3
   2560x2880 (0x1e4) 59.98*+
DP-4 connected 1440x2560+6000+680 (0x1f4) right (normal left inverted right x axis y axis) 597mm x 336mm
	Identifier: 0x1f3
   2560x1440 (0x1f4) 143.97*+ 120.00    99.95    59.95
DP-1 disconnected (normal left inverted right x axis y axis)
"""

XRANDR_OUTPUT_SIMPLE = """
Screen 0: minimum 8 x 8, current 1920 x 1080, maximum 32767 x 32767
HDMI-0 connected primary 1920x1080+0+0 (0x46) normal (normal left inverted right x axis y axis) 531mm x 299mm
   1920x1080 (0x46) 60.00*+ 74.97    59.94    50.00
"""

@patch('subprocess.check_output')
def test_get_current_state_complex(mock_check_output):
    mock_check_output.return_value = XRANDR_OUTPUT_1
    
    monitors = display_switch.get_current_state()
    
    assert len(monitors) == 3
    
    # Check HDMI-0
    m1 = monitors[0]
    assert m1['name'] == 'HDMI-0'
    assert m1['primary'] == False
    assert m1['active'] == True
    assert m1['rotation'] == 'normal'
    assert m1['active_mode'] == '1920x1080'
    assert m1['pos'] == '3146x0'
    assert m1['rate'] == '60.00'

    # Check DP-0 (Primary, Left rotation)
    m2 = monitors[1]
    assert m2['name'] == 'DP-0'
    assert m2['primary'] == True
    assert m2['active'] == True
    assert m2['rotation'] == 'left'
    assert m2['active_mode'] == '2560x2880' # Note: xrandr reports rotated dims? 
    # Wait, usually mode line is unrotated dimensions, but geometry string +X+Y is final.
    # In regex we extracted 2560x2880 from geometry.
    assert m2['pos'] == '0x360'
    assert m2['rate'] == '59.98'

    # Check DP-4 (Right rotation)
    m3 = monitors[2]
    assert m3['name'] == 'DP-4'
    assert m3['rotation'] == 'right'
    assert m3['active_mode'] == '1440x2560'
    assert m3['pos'] == '6000x680'
    assert m3['rate'] == '143.97'

@patch('subprocess.check_output')
def test_get_current_state_simple(mock_check_output):
    mock_check_output.return_value = XRANDR_OUTPUT_SIMPLE
    
    monitors = display_switch.get_current_state()
    
    assert len(monitors) == 1
    m = monitors[0]
    assert m['name'] == 'HDMI-0'
    assert m['primary'] == True
    assert m['rotation'] == 'normal'
    assert m['pos'] == '0x0'
    assert m['rate'] == '60.00'
