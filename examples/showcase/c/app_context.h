#ifndef CIFTER_EXAMPLES_SHOWCASE_C_APP_CONTEXT_H
#define CIFTER_EXAMPLES_SHOWCASE_C_APP_CONTEXT_H

#define OK 0
#define NG -1
#define RETRY_LATER 11

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

#endif
