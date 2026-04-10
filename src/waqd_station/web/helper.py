from pathlib import Path
from typing import Optional

from pint.facets.plain import PlainQuantity as Quantity

from waqd import unit_reg
from waqd.base.assets import get_asset_file


def format_unit_disp_value(
    quantity: Optional[Quantity], unit: bool = True, precision=int(1)
) -> str:
    """Format sensor value for display by appending the unit symbol (if unit is True) and float precision"""
    disp_value = "N/A"
    if quantity is not None:
        if isinstance(quantity, Quantity):
            disp_value = f"{float(quantity.m):.{precision}f}"
            if unit:
                disp_value += " " + unit_reg().get_symbol(str(quantity.u))
        else:
            disp_value = f"{float(quantity):.{precision}f}"
            if unit:
                disp_value += " " + unit
    return disp_value


def get_temperature_icon(temp_value: Optional[Quantity]) -> Path:
    """
    Return the path of the image resource for the appropriate temperature input.
    t < 0: empty
    t < 10: low
    t < 22: half
    t < 30 high
    t > 30: full
    """
    assets_subfolder = "weather_icons"
    # set dummy as default
    icon_path = get_asset_file(assets_subfolder, "thermometer_empty")
    # return dummy for invalid value
    if temp_value is None:
        return icon_path
    temp_deg_c = temp_value.m_as(unit_reg().degC)
    # set up ranges for the 5 icons
    if temp_deg_c <= 0:
        icon_path = get_asset_file(assets_subfolder, "thermometer_empty")
    elif temp_deg_c < 10:
        icon_path = get_asset_file(assets_subfolder, "thermometer_almost_empty")
    elif temp_deg_c < 22:
        icon_path = get_asset_file(assets_subfolder, "thermometer_half")
    elif temp_deg_c < 30:
        icon_path = get_asset_file(assets_subfolder, "thermometer_almost_full")
    else:
        icon_path = get_asset_file(assets_subfolder, "thermometer_full")
    return icon_path
