namespace demo {

int RouteMode(int value)
{
    if (value > 0) {
        return 1;
    } else {
        return 0;
    }
}

}  // namespace demo

namespace ns {

enum class State {
    Idle,
    Busy,
};

}  // namespace ns

int QualifiedDispatch(ns::State state)
{
    switch (state) {
    case ns::State::Idle:
        return 1;
    case ns::State::Busy:
        return 2;
    }
    return 0;
}
