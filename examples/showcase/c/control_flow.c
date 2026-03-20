#include "app_context.h"

static int DoHoge(AppContext *ctx, int state)
{
    if (ctx->retry_count > 1) {
        return RETRY_LATER;
    }
    if (state == 30) {
        return OK;
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

int DispatchCommand(AppContext *ctx, int command)
{
    int state = 10;
    int ret = NG;
    int i = 0;

    ctx->state = 101;

    switch (command) {
    case CMD_HOGE:
        state = 30;
        ret = DoHoge(ctx, state);
        if (ret == OK) {
            ctx->state = 200;
            return state;
        } else if (ret == RETRY_LATER) {
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
        ctx->state = 299;
        break;
    }

    return 0;

ERROR_EXIT:
    return -1;

FATAL_EXIT:
    return -9;
}
