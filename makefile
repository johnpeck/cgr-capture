# makefile for cgrlib

PYFILES = bin/cgr-cal.py \
          bin/cgr-capture.py \
          setup.py


# ------------------------ Done with configuration --------------------

help:
	@echo 'Makefile for cgrlib                                             '
	@echo '                                                                '
	@echo 'Usage:                                                          '
	@echo '   make register     Register project with pypi                 '
	@echo '   make upload       Upload project to pypi                     '
	@echo '   make install      (as root) install the library              '
	@echo '   make indent       Properly indent python code                '
	@echo '   make toc          Make table of contents for README          '
	@echo '                                                                '


# Install cgrlib into the python path.  Must be done as root.
.PHONY : install
install :
	python setup.py install

# Register the project with pypi
.PHONY : register
register :
	python setup.py register

# Upload the project to pypi
.PHONY : upload
upload :
	python setup.py sdist upload

# Generate a table of contents for the README file
.PHONY : toc
toc :
	doctoc README.markdown


# Change Python (.py) files to use 4-space indents and no hard tab
# characters. Also trim excess spaces and tabs from ends of lines, and
# remove empty lines at the end of files.  Also ensure the last line
# ends with a newline.
.PHONY : indent
indent :
	reindent --verbose $(PYFILES)
