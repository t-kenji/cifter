#include <stdio.h>

#define OK 0
#define NG -1

#define CMD_HOGE 1
#define CMD_FUGA 2
#define CMD_LOOP 3
#define CMD_EMERG 99

typedef struct InnerState {
    int value;
} InnerState;

typedef struct AppContext {
    int state;
    int retry_count;
    InnerState inner;
} AppContext;

static int DoHoge(AppContext *ctx, int state)
{
    if (state == 30) {
        return OK;
    }
    if (ctx->retry_count > 1) {
        return 11;
    }
    return NG;
}

static int DoFuga(AppContext *ctx)
{
    ctx->inner.value = ctx->inner.value + 1;
    return OK;
}

static int PollWork(AppContext *ctx, int index)
{
    if (index == 2) {
        ctx->state = 50;
        return OK;
    }
    return NG;
}

int FooFunction(AppContext *ctx, int command)
{
    int state = 10;
    int ret = NG;
    int i = 0;

#if defined(DEF_FOO)
    ctx->state = 100;
#else
    ctx->state = 101;
#endif

#ifdef LOCAL_TRACE
    puts("LOCAL_TRACE enabled");
#endif

#if ENABLE_BAR == 1
    ctx->inner.value = 7;
#endif

    switch (command) {
    case CMD_HOGE:
        state = 30;
        ret = DoHoge(ctx, state);
        if (ret == OK) {
            ctx->state = 200;
            return state;
        } else if (ret == 11) {
            ctx->state = 210;
            return -2;
        } else {
            ctx->state = 220;
            goto ERROR_EXIT;
        }

    case CMD_FUGA:
        ret = DoFuga(ctx);
        if (ret != OK) {
            goto ERROR_EXIT;
        }
        break;

    case CMD_LOOP:
        for (i = 0; i < 4; i++) {
            if (i == 1) {
                continue;
            }
            ret = PollWork(ctx, i);
            if (ret == OK) {
                break;
            }
        }

        while (ctx->retry_count < 2) {
            ctx->retry_count = ctx->retry_count + 1;
            if (ctx->retry_count == 1) {
                continue;
            }
            break;
        }

        do {
            state = state + 1;
        } while (state < 31);
        break;

    case CMD_EMERG:
        goto FATAL_EXIT;

    default:
        break;
    }

    return 0;

ERROR_EXIT:
    return -1;

FATAL_EXIT:
    return -9;
}

int FlowOnlySample(AppContext *ctx)
{
    int state = 0;

    if (ctx->state == 0) {
        state = 1;
    } else if (ctx->state == 1) {
        state = 2;
    } else {
        state = 3;
    }

    return state;
}
