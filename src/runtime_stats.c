#include "runtime_stats.h"

static size_t enact_runtime_current_cells;
static size_t enact_runtime_peak_cells;

void enact_runtime_stats_reset(void)
{
    enact_runtime_current_cells = 0;
    enact_runtime_peak_cells = 0;
}

void enact_runtime_cell_allocated(void)
{
    enact_runtime_current_cells += 1;
    if (enact_runtime_current_cells > enact_runtime_peak_cells) {
        enact_runtime_peak_cells = enact_runtime_current_cells;
    }
}

void enact_runtime_cell_released(void)
{
    if (enact_runtime_current_cells > 0) {
        enact_runtime_current_cells -= 1;
    }
}

size_t enact_runtime_cells(void)
{
    return enact_runtime_current_cells;
}

size_t enact_runtime_max_cells(void)
{
    return enact_runtime_peak_cells;
}
