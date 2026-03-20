namespace mirror {

int MirrorValue(int value)
{
    if (value > 0) {
        return value;
    }
    return -value;
}

}  // namespace mirror
