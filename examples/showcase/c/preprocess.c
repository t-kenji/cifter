#include "app_context.h"

int ConfigureBuild(AppContext *ctx, int mode)
{
#define LOCAL_PHASE_STATE \
    (300 + CMD_LOOP)

#if defined(ENABLE_FAST_PATH) || \
    defined(ENABLE_TRACE)
#if defined(FEATURE_LEVEL) && \
    (FEATURE_LEVEL >= 2)
    ctx->state = LOCAL_PHASE_STATE;
#else
    ctx->state = 305;
#endif
#else
    ctx->state = 301;
#endif

#ifdef LOCAL_PHASE_STATE
    ctx->inner.value = ctx->inner.value + 10;
#endif

#undef LOCAL_PHASE_STATE

#ifndef LOCAL_PHASE_STATE
    ctx->retry_count = ctx->retry_count + 1;
#endif

    if (mode > 0) {
        return ctx->inner.value;
    }
    return ctx->state;
}
