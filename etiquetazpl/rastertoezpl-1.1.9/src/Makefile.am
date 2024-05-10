
# Paths for CUPS
CUPS=@CUPS@
CUPS_FILTERS=@CUPS_FILTERS@
CUPS_BACKENDS=@CUPS_BACKENDS@


filterexecdir = "$(libexecdir)/$(PACKAGE_TARNAME)"
filterexec_PROGRAMS = rastertoezpl
rastertoezpl_SOURCES = rastertoezpl.c

# create symbolic link in CUPS filters
install-exec-hook:
	@( test -n "$(CUPS_FILTERS)" -a \
		\( ! -L "$(DESTDIR)$(CUPS_FILTERS)/rastertoezpl" \) \
	&& echo $(LN_S) "$(filterexecdir)/rastertoezpl" "$(DESTDIR)$(CUPS_FILTERS)" \
	&& $(LN_S) "$(filterexecdir)/rastertoezpl" "$(DESTDIR)$(CUPS_FILTERS)" ) \
	|| true

# remove symbolic link in CUPS filters
uninstall-hook:
	@( test -n "$(CUPS_FILTERS)" \
	&& echo rm -f "$(DESTDIR)$(CUPS_FILTERS)/rastertoezpl" \
	&& rm -f "$(DESTDIR)$(CUPS_FILTERS)/rastertoezpl" ) \
	|| true
	test -d "$(filterexecdir)" && rmdir "$(filterexecdir)"
