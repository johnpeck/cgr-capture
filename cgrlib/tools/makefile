# makefile for script file maintenance

SCRIPTS = cgr-capture.py \
          cgr-cal.py


# ------------------------- Done with configuration -------------------

help:
	@echo 'Makefile for maintaining scripts                      '
	@echo '                                                      '
	@echo 'Usage:                                                '
	@echo '   make reindent             Reindent scripts         '
	@echo '                                                      '

.PHONY: reindent
reindent :
	reindent --verbose $(SCRIPTS)


