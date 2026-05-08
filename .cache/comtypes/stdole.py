from enum import IntFlag

import comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 as __wrapper_module__
from comtypes.gen._00020430_0000_0000_C000_000000000046_0_2_0 import (
    IDispatch, VARIANT_BOOL, IFont, Color, OLE_XPOS_HIMETRIC,
    VgaColor, OLE_HANDLE, IPictureDisp, Default, GUID, Font, Library,
    IFontEventsDisp, typelib_path, StdPicture, OLE_OPTEXCLUSIVE, BSTR,
    dispid, CoClass, IPicture, OLE_XSIZE_CONTAINER, OLE_COLOR,
    FONTNAME, FONTUNDERSCORE, Picture, StdFont, DISPMETHOD, COMMETHOD,
    DISPPARAMS, IEnumVARIANT, FONTSIZE, FONTSTRIKETHROUGH,
    _check_version, OLE_ENABLEDEFAULTBOOL, OLE_XPOS_CONTAINER,
    FONTITALIC, OLE_YSIZE_HIMETRIC, Gray, FontEvents,
    OLE_XSIZE_HIMETRIC, OLE_YSIZE_CONTAINER, OLE_YPOS_PIXELS,
    OLE_YPOS_HIMETRIC, _lcid, HRESULT, Checked, IFontDisp,
    OLE_XSIZE_PIXELS, OLE_CANCELBOOL, Monochrome, OLE_YPOS_CONTAINER,
    FONTBOLD, IUnknown, Unchecked, EXCEPINFO, DISPPROPERTY,
    OLE_XPOS_PIXELS, OLE_YSIZE_PIXELS
)


class LoadPictureConstants(IntFlag):
    Default = 0
    Monochrome = 1
    VgaColor = 2
    Color = 4


class OLE_TRISTATE(IntFlag):
    Unchecked = 0
    Checked = 1
    Gray = 2


__all__ = [
    'OLE_TRISTATE', 'IFont', 'FONTSIZE', 'Color', 'OLE_XPOS_HIMETRIC',
    'VgaColor', 'OLE_HANDLE', 'FONTSTRIKETHROUGH',
    'OLE_ENABLEDEFAULTBOOL', 'IPictureDisp', 'OLE_XPOS_CONTAINER',
    'FONTITALIC', 'OLE_YSIZE_HIMETRIC', 'Gray', 'FontEvents',
    'Default', 'StdFont', 'OLE_XSIZE_HIMETRIC', 'OLE_YSIZE_CONTAINER',
    'Font', 'Library', 'IFontEventsDisp', 'typelib_path',
    'StdPicture', 'OLE_OPTEXCLUSIVE', 'OLE_YPOS_HIMETRIC',
    'OLE_YPOS_PIXELS', 'Checked', 'IFontDisp', 'OLE_XSIZE_PIXELS',
    'OLE_CANCELBOOL', 'Monochrome', 'OLE_YPOS_CONTAINER', 'IPicture',
    'FONTBOLD', 'OLE_XSIZE_CONTAINER', 'OLE_COLOR', 'Unchecked',
    'FONTNAME', 'FONTUNDERSCORE', 'Picture', 'OLE_XPOS_PIXELS',
    'OLE_YSIZE_PIXELS', 'LoadPictureConstants'
]

