CC ?= cc
CFLAGS ?= -std=c11 -Wall -Wextra -O0 -g
CPPFLAGS ?= -Isrc -Ibuild

BISON ?= bison
FLEX ?= flex

BUILD_DIR := build
SRC_DIR := src

GENERATED_C := $(BUILD_DIR)/enact.tab.c $(BUILD_DIR)/lex.yy.c
GENERATED_H := $(BUILD_DIR)/enact.tab.h

OBJS := \
	$(BUILD_DIR)/ast.o \
	$(BUILD_DIR)/diag.o \
	$(BUILD_DIR)/parser_state.o \
	$(BUILD_DIR)/eval.o \
	$(BUILD_DIR)/api.o \
	$(BUILD_DIR)/scan.o \
	$(BUILD_DIR)/main.o \
	$(BUILD_DIR)/enact.tab.o \
	$(BUILD_DIR)/lex.yy.o

LIB_OBJS := \
	$(BUILD_DIR)/ast.o \
	$(BUILD_DIR)/diag.o \
	$(BUILD_DIR)/parser_state.o \
	$(BUILD_DIR)/eval.o \
	$(BUILD_DIR)/api.o \
	$(BUILD_DIR)/scan.o \
	$(BUILD_DIR)/enact.tab.o \
	$(BUILD_DIR)/lex.yy.o

HANDWRITTEN_C_COVERAGE_SRCS := \
	$(SRC_DIR)/ast.c \
	$(SRC_DIR)/diag.c \
	$(SRC_DIR)/parser_state.c \
	$(SRC_DIR)/eval.c \
	$(SRC_DIR)/api.c \
	$(SRC_DIR)/scan.c \
	$(SRC_DIR)/main.c

HANDWRITTEN_GRAMMAR_COVERAGE_SRCS := \
	$(BUILD_DIR)/lex.yy.c \
	$(BUILD_DIR)/enact.tab.c

all: $(BUILD_DIR)/enact

$(BUILD_DIR):
	mkdir -p $(BUILD_DIR)

$(BUILD_DIR)/enact.tab.c $(BUILD_DIR)/enact.tab.h: $(SRC_DIR)/enact.y | $(BUILD_DIR)
	$(BISON) -d -o $(BUILD_DIR)/enact.tab.c $(SRC_DIR)/enact.y

$(BUILD_DIR)/lex.yy.c: $(SRC_DIR)/enact.l $(BUILD_DIR)/enact.tab.h | $(BUILD_DIR)
	$(FLEX) -o $(BUILD_DIR)/lex.yy.c $(SRC_DIR)/enact.l

$(BUILD_DIR)/enact.tab.o: $(BUILD_DIR)/enact.tab.c $(GENERATED_H) | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/lex.yy.o: $(BUILD_DIR)/lex.yy.c $(GENERATED_H) | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/scan.o: $(SRC_DIR)/scan.c $(GENERATED_H) | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/%.o: $(SRC_DIR)/%.c | $(BUILD_DIR)
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

$(BUILD_DIR)/enact: $(OBJS)
	$(CC) $(CFLAGS) $(OBJS) -o $@

$(BUILD_DIR)/unit_tests: $(LIB_OBJS) tests/unit_tests.c
	$(CC) $(CPPFLAGS) $(CFLAGS) tests/unit_tests.c $(LIB_OBJS) -o $@

test: $(BUILD_DIR)/enact $(BUILD_DIR)/unit_tests
	python3 tests/run_tests.py
	$(BUILD_DIR)/unit_tests

coverage: clean
	$(MAKE) CFLAGS='-std=c11 -Wall -Wextra -O0 -g --coverage' test
	gcov -b -c -o $(BUILD_DIR) $(HANDWRITTEN_C_COVERAGE_SRCS) >/dev/null
	gcov -b -c -o $(BUILD_DIR) $(HANDWRITTEN_GRAMMAR_COVERAGE_SRCS) >/dev/null
	python3 tools/coverage_report.py

clean:
	rm -rf $(BUILD_DIR)
	rm -f *.gcov

.PHONY: all test coverage clean
