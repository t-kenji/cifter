namespace demo {

struct WorkerContext {
    int state;
    int retries;
};

class Worker {
public:
    int Process(WorkerContext *ctx, int value);
};

template <typename T>
T PickNonZero(T current, T fallback)
{
    if (current != 0) {
        return current;
    }
    return fallback;
}

int Worker::Process(WorkerContext *ctx, int value)
{
    if constexpr (sizeof(int) >= 4) {
        if (ctx == nullptr) {
            return -1;
        }
    }

    auto next = PickNonZero(value, ctx->state);
    if (next > 0) {
        return next;
    }
    return ctx->state;
}

}  // namespace demo
