/*
 * Pin map, in BCM numbering.
 *
 * SeedSigner's Python uses RPi.GPIO BOARD numbering; these are the same
 * physical pins. The button values match the desktop emulator's constants
 * exactly, which is a useful independent check that the conversion is right.
 *
 *   display  DC   BOARD 22 -> BCM 25
 *            RST  BOARD 13 -> BCM 27
 *            BL   BOARD 18 -> BCM 24
 *   buttons  UP   BOARD 31 -> BCM 6      KEY1 BOARD 40 -> BCM 21
 *            DOWN BOARD 35 -> BCM 19     KEY2 BOARD 38 -> BCM 20
 *            LEFT BOARD 29 -> BCM 5      KEY3 BOARD 36 -> BCM 16
 *            RIGHT BOARD 37 -> BCM 26
 *            PRESS BOARD 33 -> BCM 13
 */
#ifndef SS_PINS_H
#define SS_PINS_H

#define SS_PIN_DC    25
#define SS_PIN_RST   27
#define SS_PIN_BL    24

#define SS_PIN_UP     6
#define SS_PIN_DOWN  19
#define SS_PIN_LEFT   5
#define SS_PIN_RIGHT 26
#define SS_PIN_PRESS 13
#define SS_PIN_KEY1  21
#define SS_PIN_KEY2  20
#define SS_PIN_KEY3  16

#endif /* SS_PINS_H */
