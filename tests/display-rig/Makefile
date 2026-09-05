# Built against a User-Mode Linux kernel tree, never against the host kernel.
#   make KSRC=/path/to/linux-x.y.z
KSRC ?= $(error set KSRC to a UML kernel source tree built with ARCH=um)

obj-m += ss_display_capture.o

all:
	$(MAKE) -C $(KSRC) ARCH=um M=$(CURDIR) modules

clean:
	$(MAKE) -C $(KSRC) ARCH=um M=$(CURDIR) clean
