#include "ss_unlock.h"

void ss_unlock_init(ss_unlock_t *unlock, const int *sequence, int length)
{
    unlock->sequence = sequence;
    unlock->length = length;
    unlock->progress = 0;
}

int ss_unlock_feed(ss_unlock_t *unlock, int key)
{
    if (unlock->length <= 0) {
        return 0;
    }

    if (key == unlock->sequence[unlock->progress]) {
        unlock->progress++;
        if (unlock->progress == unlock->length) {
            unlock->progress = 0;
            return 1;
        }
        return 0;
    }

    /* A wrong press restarts, but may itself be a valid opening. */
    unlock->progress = (key == unlock->sequence[0]) ? 1 : 0;
    return 0;
}
