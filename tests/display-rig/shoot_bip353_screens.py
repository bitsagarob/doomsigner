"""Render the BIP-353 payment-name screens through the real display driver.

Runs inside the UML sandbox. It builds each screen exactly the way
PSBTAddressDetailsView does, including the app's own status text and colour
maps, so what reaches the panel is what a user would see.

One full-screen write per case; decode_st7789.py --split turns the capture into
one PNG per screen.
"""
from gettext import gettext as _

from seedsigner.models.settings import Settings
Settings.RUNTIME_PROFILE = "rpi_40"

from seedsigner.models.settings_definition import SettingsConstants
Settings.get_instance().set_value(
    SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
    SettingsConstants.DISPLAY_CONFIGURATION__ST7789__240x240,
)

from seedsigner.gui.renderer import Renderer
Renderer.configure_instance()
renderer = Renderer.get_instance()

from seedsigner.gui.components import GUIConstants
from seedsigner.gui.screens.psbt_screens import PSBTAddressDetailsScreen
from seedsigner.gui.screens.screen import ButtonOption
from seedsigner.helpers import bip353
from seedsigner.views.psbt_views import PSBTAddressDetailsView

ADDRESS = "bc1qar0srrr7xfkvy5l643lydnw9re59gtzzwf5mdq"
LONG_NAME = "averylongpaymentname@some-quite-long-domain.example.org"

CASES = [
    ("verified", bip353.Status.VERIFIED, "rob@bitsaga.be"),
    ("no-clock", bip353.Status.NO_CLOCK, "rob@bitsaga.be"),
    ("expired", bip353.Status.EXPIRED, "rob@bitsaga.be"),
    ("bad-proof", bip353.Status.CHAIN_INVALID, "rob@bitsaga.be"),
    ("wrong-recipient", bip353.Status.OUTPUT_MISMATCH, "rob@bitsaga.be"),
    ("verified-long-name", bip353.Status.VERIFIED, LONG_NAME),
]

for label, status, name in CASES:
    screen = PSBTAddressDetailsScreen(
        title="Send",
        button_data=[ButtonOption("Next")],
        address=ADDRESS,
        amount=123_456,
        payment_name=name,
        payment_name_status=_(PSBTAddressDetailsView.STATUS_TEXT[status]),
        payment_name_color=PSBTAddressDetailsView.STATUS_COLOR.get(
            status, GUIConstants.ERROR_COLOR),
    )
    screen._render()
    renderer.show_image()
    print(f"rendered {label}: {status}", flush=True)

print("ALL SCREENS RENDERED", flush=True)
