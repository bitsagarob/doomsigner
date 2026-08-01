/*
 * The unlock sequence, in C.
 *
 * Deliberately mirrors bootgame/unlock.py, including the rule that a wrong
 * press may itself begin the next attempt. Kept identical so the easter egg
 * behaves the same whichever game is running.
 */
#ifndef SS_UNLOCK_H
#define SS_UNLOCK_H

typedef struct {
    const int *sequence;
    int length;
    int progress;
} ss_unlock_t;

void ss_unlock_init(ss_unlock_t *unlock, const int *sequence, int length);

/* Feed one press. Returns 1 on the press that completes the sequence. */
int ss_unlock_feed(ss_unlock_t *unlock, int key);

#endif /* SS_UNLOCK_H */
