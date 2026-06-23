#ifndef ENACT_RUNTIME_STATS_H
#define ENACT_RUNTIME_STATS_H

#include <stddef.h>

void enact_runtime_stats_reset(void);
void enact_runtime_cell_allocated(void);
void enact_runtime_cell_released(void);
size_t enact_runtime_cells(void);
size_t enact_runtime_max_cells(void);

#endif
