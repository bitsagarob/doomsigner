"""
One module per game.

Each exposes `play(renderer, reader, unlock)`. It is imported only when that
game is chosen, so a game that is broken, heavy or simply unused costs nothing
at boot and cannot stop the device from reaching the wallet.

`play` may return to send the player back to the chooser, or never return if it
hands off.
"""
