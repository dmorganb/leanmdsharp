PYTHON ?= python3
CHARMSHARP ?= ../../charmsharp/build/charmsharp
CHARMC ?= charmc
OPTS ?= -O3
CI_FLAGS ?=

.PHONY: all generate test clean
all: generate
	cd build && $(CHARMC) -E leanmd.ci $(CI_FLAGS)
	cd build && $(CHARMC) $(OPTS) -include compat_types.h -c leanmd.cpp -o leanmd.o
	cd build && $(CHARMC) $(OPTS) -module CkMulticast -module CommonLBs -language charm++ leanmd.o -o leanmd

generate:
	$(PYTHON) assemble.py --compiler "$(CHARMSHARP)"

test:
	$(PYTHON) test_migration.py --compiler "$(CHARMSHARP)"

clean:
	rm -rf build
