# makefile for cgrlib

PYFILES = bin/cgr-cal.py \
          bin/cgr-capture.py \
          setup.py


# ------------------------ Done with configuration --------------------

help:
	@echo 'Makefile for cgrlib                                             '
	@echo '                                                                '
	@echo 'Usage:                                                          '
	@echo '   make install      (as root) install the library              '
	@echo '   make indent       Properly indent python code                '
	@echo '                                                                '


# Install cgrlib into the python path.  Must be done as root.
.PHONY : install
install :
	python setup.py install


# Change Python (.py) files to use 4-space indents and no hard tab
# characters. Also trim excess spaces and tabs from ends of lines, and
# remove empty lines at the end of files.  Also ensure the last line
# ends with a newline.
.PHONY : indent
indent :
	reindent --verbose $(PYFILES)
