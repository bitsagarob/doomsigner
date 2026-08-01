/*
 * Reading the buttons.
 *
 * Edge detected, matching bootgame/edges.py: one event per press, not one per
 * poll, so a held button cannot walk through the unlock sequence.
 *
 * Two backends, chosen at runtime with SS_INPUT:
 *   gpio   the real buttons (default)
 *   stdin  one character per press, for testing off-device
 */
#ifndef SS_INPUT_H
#define SS_INPUT_H

/* Our own codes for the three side buttons; DOOM never sees these values. */
#define SS_KEY1 0xE1
#define SS_KEY2 0xE2
#define SS_KEY3 0xE3

int ss_input_init(void);

/*
 * Returns 1 if there was an event, and fills in the DOOM key code and whether
 * it was a press or a release. `side_button` is set to SS_KEY1/2/3 when one of
 * the side buttons caused the event, and 0 otherwise.
 */
int ss_input_poll(int *doom_key, int *pressed, int *side_button);

#endif /* SS_INPUT_H */
