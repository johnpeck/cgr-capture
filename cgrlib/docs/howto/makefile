# makefile for cgrlib's howto

# The top-level latex file (without the .tex)
MAINFILE=howto

# Where to put generated output for submission
OUTPUTDIR=./output

# The base name of the user commands index file
USER_CMDS_IDX=user_cmds_index

# The base name of the internal command index file
INTERNAL_CMDS_IDX=internal_cmds_index

# USB board schematics directory
USBSCHDIR = schematics/usb

# Butterfly board schematics directory
BFLYSCHDIR = schematics/butterfly



#------------------------- Done with configuration ---------------------


help:
	@echo 'Makefile for the cgrlib howto                                  '
	@echo '                                                               '
	@echo 'Usage:                                                         '
	@echo '   make dvi                  Regenerate the dvi file           '
	@echo '   make preview              Fire up xdvi to view the dvi file '
	@echo '   make pdf                  Create the howto pdf in ./output  '
	@echo '   make comcheck             Check included remote commands    '
	@echo '   make clean                Clean up temporary files          '
	@echo '                                                               '



howto: $(OUTPUTDIR)\
	    $(OUTPUTDIR)/howto.pdf

$(OUTPUTDIR)/howto.pdf: $(OUTPUTDIR)\
			 $(MAINFILE).ps
	ps2pdf $(MAINFILE).ps
	mv $(MAINFILE).pdf $(OUTPUTDIR)/howto.pdf
	@echo "* howto.pdf output to "$(OUTPUTDIR)

pdf: $(MAINFILE).pdf
$(MAINFILE).pdf: $(OUTPUTDIR) \
                 $(MAINFILE).ps
	ps2pdf $(MAINFILE).ps $(OUTPUTDIR)/boxcom_howto.pdf

ps: $(MAINFILE).ps
$(MAINFILE).ps: $(MAINFILE).dvi
	dvips -t letter $(MAINFILE).dvi

.PHONY: preview
preview:
	xdvi $(MAINFILE).dvi &

# Make latex_manual.dvi a PHONY target so that latex can be run over and
# over to resove labels.
.PHONY : dvi
.PHONY : $(MAINFILE).dvi
dvi : $(MAINFILE).dvi
$(MAINFILE).dvi: 
	latex $(MAINFILE).tex


# The submission directory
$(OUTPUTDIR):
	mkdir -p $(OUTPUTDIR)



# ind files are generated from idx files with makeindex
%.ind : %.idx
	makeindex -o $@ $<


# The idx index files are generated when latex is run on the main
# file and multind.sty is pulled in.  But latex expects to find
# the ind files when it runs -- which are made from the idx files.
%.idx :
	touch $@



# The internal commands idx file has a cln extension
internal_cmds_index.ind: internal_cmds_index.cln
	makeindex $<



# LaTeX has a problem with index entries containing escaped characters
# when the entries occur inside macro arguments.  Need to remove all
# spaces in entries with escaped $ signs.
internal_cmds_index.cln: internal_cmds_index.idx
	cat $< | sed -e 's/ //' > $@

# The idx files are generated when the latex file is processed with the 
# multind.sty package included.
internal_cmds_index.idx: $(wildcard ./commands/*.tex)
	latex $(MAINFILE).tex



# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ Figure files ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

# Schematics
$(USBSCHDIR)/%.eps : $(USBSCHDIR)/%.ps
	@echo
	@echo 'Converting $< to eps...'
	ps2eps $<


# The current sense cable
figs/current_sense_cable.eps : figs/current_sense_cable.svg
	inkscape --export-eps=$@ $<

# The binding post cable
figs/post_cable.eps : figs/post_cable.svg
	inkscape --export-eps=$@ $<

# The butterfly power cable
figs/butterfly_power_cable.eps : figs/butterfly_power_cable.svg
	inkscape --export-eps=$@ $<

# The current sampling plot
figs/curout_plot.eps : figs/curout_plot.svg
	inkscape --export-eps=$@ $<

# Make the parse buffer flow diagram
./tikz/parse_cmd_flow.eps: ./tikz/parse_cmd_flow.tex\
                           ./doctools/latex/tikzstuff.tex
	cd tikz; pdflatex parse_cmd_flow.tex
	pdftops -eps ./tikz/parse_cmd_flow.pdf

# Make the parse buffer figure
./figs/prsbuffer.eps: ./figs/prsbuffer.fig
	fig2dev -L eps -m 1 ./figs/prsbuffer.fig ./figs/prsbuffer.eps


# Make the received character buffer figure
./figs/recbuffer.eps: ./figs/recbuffer.fig
	fig2dev -L eps -m 1 ./figs/recbuffer.fig ./figs/recbuffer.eps

# The received character flow diagram
./tikz/recv_cmd_flow.eps: ./tikz/recv_cmd_flow.tex\
                          ./doctools/latex/tikzstuff.tex
	cd tikz; pdflatex recv_cmd_flow.tex
	pdftops -eps ./tikz/recv_cmd_flow.pdf

# The panel switch wiring figure
figs/panel_switch_wiring.eps : figs/panel_switch_wiring.svg
	inkscape --export-eps=$@ $< 

# The usb board serial breakout cable
figs/usb_board_uart_to_db9.eps : figs/usb_board_uart_to_db9.svg
	inkscape --export-eps=$@ $<

# The serial loopback test setup figure
figs/serial_loopback_test.eps : figs/serial_loopback_test.svg
	inkscape --export-eps=$@ $<

# The current monitor test figure
figs/monitor_test.eps : figs/monitor_test.svg
	inkscape --export-eps=$@ $<

# Connections made to the AVR Butterfly
figs/butterfly_connect.eps : figs/butterfly_connect.svg
	inkscape --export-eps=$@ $<

# Making the UART cable
figs/uart_cable.eps : figs/uart_cable.svg
	inkscape --export-eps=$@ $<

# The pulsed waveform construction parameter figure
./figs/pulse_params.eps: ./figs/pulse_params.fig
	# ------- Making the pulsed waveform construction figure ----------
	fig2dev -L eps -m 1 $< $@

# The arbitrary waveform construction parameter figure
./figs/arb_params.eps: ./figs/arb_params.fig
	# ----- Making the arbitrary waveform construction figure ---------
	fig2dev -L eps -m 1 $< $@

# The arbitrary waveform example figure
./figs/arb_example.eps: ./figs/arb_example.fig
	# ----- Making the arbitrary waveform construction figure ---------
	fig2dev -L eps -m 1 $< $@

# The ramp waveform construction parameter figure
./figs/ramp_params.eps: ./figs/ramp_params.fig
	# ----- Making the ramp waveform construction figure --------
	fig2dev -L eps -m 1 $< $@

# The current interrupt timing figure
./figs/interrupt_plot.eps: ./figs/interrupt_plot.fig
	# ---------- Making the current interrupt timing figure -----------
	fig2dev -L eps -m 1 $< $@

# The current interrupt synchronization timing figure
./figs/cisync_timing.eps: ./figs/cisync_timing.fig
	# ---------- Making the CI synchronization timing figure ----------
	fig2dev -L eps -m 1 $< $@

# The current interrupt example figure
./figs/ci_example.eps: ./figs/ci_example.fig
	fig2dev -L eps -m 1 $< $@

# The streaming data packet figure
./figs/datapacket.eps: ./figs/datapacket.fig
	# ---------------- Making the data packet figure ------------------
	fig2dev -L eps -m 1 $< $@

# The normal pulse example figure
./figs/npulse_example.eps: ./figs/npulse_example.fig
	# ------------ Making the normal pulse example figure -------------
	fig2dev -L eps -m 1 $< $@

# The CV example figure
./figs/cv_example.eps: ./figs/cv_example.fig
	fig2dev -L eps -m 1 $< $@

# The status bits figure.
# To convert gifs to eps, you must specifiy the image resolution.  You can
# determine this with:
# identify -verbose <image file>
# Then use this resolution in the density flag.
./raster/status_bits.eps: ./raster/status_bits.gif
	convert -density 72x72 $< $@

# The SRS logo
./raster/srs_logo.eps: ./raster/srs_logo.png
	convert $< $@

# ---- The "sideby" figures for documenting the front and rear panels -----

# IR compensation
./figs/ircomp_sideby.eps: ./figs/ircomp_sideby.fig
	fig2dev -L eps -m 1 $< $@

# Rear panel auxiliary input BNCs
./figs/aux_adc_sideby.eps: ./figs/aux_adc_sideby.fig
	fig2dev -L eps -m 1 $< $@


# comcheck -- report missing commands
comcheck:
	cd scripts;python comcheck.py

clean:
	rm -f *.aux
	# Clean up pages created by pdfpage.sh
	rm -f $(MAINFILE)_page*.pdf
	rm -f figs/*.eps
	rm -f figs/*.bak
	rm -f output/howto_page*


