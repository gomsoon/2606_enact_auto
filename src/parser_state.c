#include "parser_state.h"

static EnactParseContext *g_parse_context;
static EnactScannerState *g_scanner_state;

EnactParseContext *enact_get_parse_context(void)
{
    return g_parse_context;
}

EnactScannerState *enact_get_scanner_state(void)
{
    return g_scanner_state;
}

void enact_set_parse_context(EnactParseContext *context)
{
    g_parse_context = context;
}

void enact_set_scanner_state(EnactScannerState *state)
{
    g_scanner_state = state;
}

void enact_parse_context_take_root(EnactAst *root)
{
    if (g_parse_context) {
        g_parse_context->root = root;
    }
}
