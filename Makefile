CXX ?= c++
CXXFLAGS ?= -O3 -DNDEBUG
FLAGS = -std=c++20 -Wall -Wextra -Wpedantic -fPIC
BUILD ?= build
LEAN ?= $(or $(wildcard .tools/lean-4.19.0-linux/bin/lean),lean)
PYTHON ?= python3

.PHONY: all test lean clean
all: $(BUILD)/tera $(BUILD)/libtera.so

$(BUILD):
	mkdir -p $@

$(BUILD)/%.o: cpp/%.cpp | $(BUILD)
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(FLAGS) -MMD -MP -c $< -o $@

$(BUILD)/tera: $(BUILD)/engine.o $(BUILD)/main.o
	$(CXX) $(LDFLAGS) $^ -o $@

$(BUILD)/libtera.so: $(BUILD)/engine.o $(BUILD)/mcts.o $(BUILD)/api.o
	$(CXX) $(LDFLAGS) -shared $^ -o $@

$(BUILD)/native_test: tests/native.cpp $(BUILD)/engine.o $(BUILD)/mcts.o
	$(CXX) $(CPPFLAGS) $(CXXFLAGS) $(FLAGS) -UNDEBUG -Icpp $^ $(LDFLAGS) -o $@

test: all $(BUILD)/native_test
	$(BUILD)/native_test
	TERA_BIN=$(BUILD)/tera $(PYTHON) -m unittest discover -s tests -v

lean:
	$(LEAN) Rules.lean

clean:
	rm -rf $(BUILD)

-include $(wildcard $(BUILD)/*.d)

.PHONY: lean-test
lean-test: all
	mkdir -p .lean-build
	$(LEAN) -o .lean-build/Rules.olean Rules.lean
	LEAN_PATH=.lean-build LEAN=$(LEAN) TERA_BIN=$(BUILD)/tera $(PYTHON) tests/compare_lean.py
