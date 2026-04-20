# Location of the MicroPython repo.
MPY_DIR ?= ../../micropython

# Name of the module (matches the Python import name)
MOD = twiddle

# Source files
SRC = twiddle.c

# Target architecture:
# RP2040 is ARM Cortex-M0+, which maps to armv6m
ARCH = armv6m

# Uncomment to link against compiler runtime (e.g. for soft-float helpers)
# LINK_RUNTIME = 1

# Include MicroPython build rules
include $(MPY_DIR)/py/dynruntime.mk
