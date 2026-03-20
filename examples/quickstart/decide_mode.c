int DecideMode(int value)
{
    int state = 0;

    if (value > 10) {
        state = 1;
    } else if (value == 10) {
        state = 2;
    } else {
        state = 3;
    }

    return state;
}
