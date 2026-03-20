from __future__ import annotations

import re
import tomllib
from pathlib import Path

from typer.testing import CliRunner

ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*m")


def _read_expected_version() -> str:
    pyproject_path = Path(__file__).resolve().parents[1] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = data["project"]["version"]
    assert isinstance(version, str)
    return f"cift {version}"


def normalize_help_output(text: str) -> str:
    return ANSI_ESCAPE_RE.sub("", text)


runner = CliRunner()
EXPECTED_VERSION = _read_expected_version()

SOURCE = """#define LOCAL_FLAG 1
#include <stdio.h>

int FooFunction(int command)
{
    int state = INIT;
    int ret = NG;

    switch (command) {
    case CMD_HOGE:
        state = RUN;
        ret = DoHoge(state);
        if (ret == OK) {
            state = DONE;
            return state;
        } else if (errno == EINT) {
            state = RETRY;
            return -2;
        } else {
            state = ERR;
            return -1;
        }

    default:
        break;
    }

    return -9;
}

int OtherFunction(void)
{
    return 0;
}
"""

TRACK_SOURCE = """typedef struct Context {
    int state;
} Context;

int TrackOnly(Context *ctx)
{
    int state = 0;
    ctx->state = 1;
    state = state + 1;
    return state;
}
"""

MULTILINE_TRACK_SOURCE = """typedef struct Context {
    int state;
} Context;

int TrackMultiline(Context *ctx)
{
    ctx
        ->state = 1;
    return ctx
        ->state;
}
"""

TAB_TRACK_SOURCE = """int TabTrack(void)
{
\t\tst->spl.status = status;
    return 0;
}
"""

PATH_TRAILING_SOURCE = """int RouteTail(int x)
{
    switch (x) {
    case 1:
        Prep();
        if (x > 0) {
            Work();
        }
        After();
        break;
    default:
        break;
    }
}
"""

ELSE_SOURCE = """int ElseRoute(int x)
{
    if (x > 0) {
        WorkA();
    } else {
        WorkB();
    }

    After();
    return 3;
}
"""

DUPLICATE_FUNCTION_SOURCE = """int Repeat(void)
{
    return 1;
}

int Repeat(void)
{
    return 2;
}
"""

DEFAULT_SOURCE = """int DefaultRoute(int x)
{
    switch (x) {
    case 1:
        return 1;
    default:
        HandleDefault();
        break;
    }
}
"""

BLOCK_CASE_SOURCE = """int BlockCaseRoute(int x)
{
    switch (x) {
    case REQ_A:
    {
        Prep();
        if (x > 0) {
            Work();
        }
        After();
        break;
    }
    default:
    {
        break;
    }
    }
}
"""

AMBIGUOUS_SOURCE = """int Ambiguous(int x)
{
    if (x > 0) {
        First();
    }

    if (x > 0) {
        Second();
    }
}
"""

LOOP_PATH_SOURCE = """int LoopRoute(int sts)
{
    if (status == BAR) {
    } else {
        if (POWER == ON) {
        } else {
        }
        for (;;) {
            if (result == OK) {
            } else {
            }
            if (res == NG) break;
            switch (sts) {
            case STS_IDLE:
                Work();
                break;
            }
        }
    }
}
"""

WHILE_ROUTE_SOURCE = """int WhileRoute(int sts)
{
    while ((sts > 0)) {
        switch (sts) {
        case STS_IDLE:
            Work();
            break;
        }
    }
}
"""

DO_WHILE_ROUTE_SOURCE = """int DoWhileRoute(int sts)
{
    do {
        switch (sts) {
        case STS_IDLE:
            Work();
            break;
        }
    } while ((sts > 0));
}
"""

AMBIGUOUS_FOR_SOURCE = """int AmbiguousFor(void)
{
    for (;;) {
        First();
    }

    for (;;) {
        Second();
    }
}
"""

AMBIGUOUS_WHILE_SOURCE = """int AmbiguousWhile(int x)
{
    while (x > 0) {
        First();
    }

    while (x > 0) {
        Second();
    }
}
"""

AMBIGUOUS_CASE_SOURCE = """int AmbiguousCase(int x)
{
    switch (x) {
    case STS_IDLE:
        First();
        break;
    }

    switch (x) {
    case STS_IDLE:
        Second();
        break;
    }
}
"""

PREPROCESS_SOURCE = """int Flagged(void)
{
#if defined(DEF_FOO)
    return 1;
#else
    return 0;
#endif
#ifdef LOCAL_FLAG
    return 2;
#endif
#if ENABLE_BAR == 1
    return 3;
#endif
}
"""

PREPROCESS_NESTED_SOURCE = """int Nested(void)
{
#define LOCAL 1
#if defined(LOCAL)
#if defined(OUTER)
    return 1;
#else
    return 2;
#endif
#endif
#undef LOCAL
#ifdef LOCAL
    return 3;
#endif
    return 4;
}
"""

PREPROCESS_TAB_DIRECTIVE_SOURCE = """int Tabbed(void)
{
#if defined(ENABLE_FIRST)
    return 1;
#else\t// fallback
    return 0;
#endif\t// end first
    return 9;
}
"""

PREPROCESS_TAB_DEFINE_SOURCE = """int TabMacros(void)
{
#define\tLOCAL 1
#ifdef\tLOCAL
    return 1;
#endif\t// local
#undef\tLOCAL
#ifndef\tLOCAL
    return 2;
#endif\t// after undef
    return 3;
}
"""

PREPROCESS_MULTILINE_IF_SOURCE = """int MultiIf(void)
{
#if defined(ENABLE_A) || \\
    defined(ENABLE_B)
    return 1;
#else
    return 0;
#endif
}
"""

PREPROCESS_MULTILINE_DEFINE_SOURCE = """int MultiDefine(void)
{
#define LOCAL_FLAG \\
    1
#ifdef LOCAL_FLAG
    return 1;
#endif
#undef LOCAL_FLAG
#ifdef LOCAL_FLAG
    return 2;
#endif
    return 3;
}
"""

PREPROCESS_DEFINE_EXPR_SOURCE = """int DefineExpr(void)
{
#define CMP (1==1)
#if CMP
    return 1;
#else
    return 2;
#endif
}
"""

PREPROCESS_FUNCTION_MACRO_SOURCE = """int FunctionMacro(void)
{
#define IS_OK(x) ((x) == 1)
#if IS_OK(1)
    return 1;
#else
    return 2;
#endif
}
"""

PREPROCESS_UNSUPPORTED_DIRECTIVE_SOURCE = """#pragma once
int KeepPragma(void)
{
    return 1;
}
"""

PREPROCESS_ERROR_DIRECTIVE_SOURCE = """#error keep this line
int KeepError(void)
{
    return 1;
}
"""

HEADER_C_SOURCE = """int SharedHeader(void)
{
    return 1;
}
"""

HEADER_CPP_SOURCE = """namespace Demo {
inline int HeaderCpp(int &value)
{
    return value;
}
}
"""

CPP_MEMBER_SOURCE = """namespace Demo {
class Worker {
public:
    int Step(int *ptr);
};

int Worker::Step(int *ptr)
{
    auto current = ptr;
    if constexpr (true) {
        if (current == nullptr) {
            return 0;
        }
    }
    return 1;
}
}
"""

CPP_PATH_SOURCE = """namespace Demo {
int Route(int value)
{
    if (value > 0) {
        return 1;
    } else {
        return 0;
    }
}
}
"""

CPP_TEMPLATE_SOURCE = """template <typename T>
T Pick(T value)
{
    return value;
}
"""

QUALIFIED_CASE_SOURCE = """namespace ns {
enum class State { Idle, Busy };
}

int QualifiedRoute(ns::State state)
{
    switch (state) {
    case ns::State::Idle:
        return 1;
    case ns::State::Busy:
        return 2;
    }
    return 0;
}
"""

ANSI_ESCAPE_PATTERN = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def write_text_file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def write_bytes_file(tmp_path: Path, name: str, content: bytes) -> Path:
    path = tmp_path / name
    path.write_bytes(content)
    return path


def demo_source() -> Path:
    return Path(__file__).resolve().parents[1] / "examples" / "demo.c"


def strip_ansi(text: str) -> str:
    return ANSI_ESCAPE_PATTERN.sub("", text)


class FakeStream:
    def __init__(self, *, is_tty: bool) -> None:
        self._is_tty = is_tty

    def isatty(self) -> bool:
        return self._is_tty
