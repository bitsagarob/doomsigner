"""Render a real SeedSigner screen through the real display driver.

Runs inside the UML sandbox. Nothing here patches the app: it sets the hardware
profile the way a Pi's device tree would, then lets the app's own Renderer pick
the ST7789 driver and write to the real /dev/spidev0.0.
"""
import sys, time

from seedsigner.models.settings import Settings
Settings.RUNTIME_PROFILE = "rpi_40"

from seedsigner.models.settings_definition import SettingsConstants
settings = Settings.get_instance()
settings.set_value(SettingsConstants.SETTING__DISPLAY_CONFIGURATION,
                   SettingsConstants.DISPLAY_CONFIGURATION__ST7789__240x240)

from seedsigner.gui.renderer import Renderer
Renderer.configure_instance()
renderer = Renderer.get_instance()
print("display driver:", type(renderer.disp).__name__,
      renderer.canvas_width, "x", renderer.canvas_height, flush=True)

from seedsigner.gui.screens.screen import ButtonListScreen, ButtonOption

screen = ButtonListScreen(
    title="Main Menu",
    button_data=[
        ButtonOption("Scan"),
        ButtonOption("Seeds"),
        ButtonOption("Tools"),
        ButtonOption("Settings"),
    ],
)
screen._render()
renderer.show_image()
print("SCREEN RENDERED THROUGH THE REAL DRIVER", flush=True)
time.sleep(0.5)
