SUBDIRS = src
dist_doc_DATA = doc/beginner_readme doc/FAQ doc/README doc/README_macOS doc/printing-on-unix usb/godex.usb-quirks

# Path for PPD source and PPD
PPDS_FILES = ${srcdir}/ppds/godex.drv
PPD_OUT_DIR = ${srcdir}/ppds/ppd

PPDDIR = @PPDDIR@

# build PPD files
build-ppd:
	@if test -z '$(PPDC)' ; then \
	  echo "No Cups PPD Compiler: cannot build PPD files."; \
	  exit 1; \
	fi
	$(PPDC) -d "$(PPD_OUT_DIR)" "$(PPDS_FILES)";

# clean PPD files
clean-ppd:
	@if test -z '$(PPDC)' ; then \
	  echo "No Cups PPD Compiler: don't clean PPD files!"; \
	  exit 1; \
	fi
	$(RM) "$(PPD_OUT_DIR)/"*.ppd;

install-data-local:
	@if test -z "$(PPDDIR)" ; then \
	  echo "No directory for install PPD files: don't install PPD files"; \
	  exit 1; \
	fi
	@if test \! -d "$(DESTDIR)$(PPDDIR)/godex"; then \
	  echo $(MKDIR_P) "$(DESTDIR)$(PPDDIR)/godex"; \
	  $(MKDIR_P) "$(DESTDIR)$(PPDDIR)/godex"; \
	fi
	$(INSTALL) -m a=r,u=rw "$(PPD_OUT_DIR)/"* "$(DESTDIR)$(PPDDIR)/godex"
	@if test -z '$(PPDLINK)'; then \
	  echo "No path (PPDLINK) for symbolic link to PPD files."; \
	else \
	  if test "$(SYSTEM_IS_DARWIN)" = "1"; then \
	    echo $(LN_S) "$(DESTDIR)$(PPDDIR)/godex/*" "$(PPDLINK)"; \
	    $(LN_S) "$(DESTDIR)$(PPDDIR)/godex/"* "$(PPDLINK)" || true; \
	  else \
	    echo $(LN_S) "$(DESTDIR)$(PPDDIR)/godex" "$(PPDLINK)"; \
	    $(LN_S) "$(DESTDIR)$(PPDDIR)/godex" "$(PPDLINK)" || true; \
	  fi \
	fi

# unistall PPD files
uninstall-local:
	@if test -z "$(PPDDIR)" ; then \
	  echo "No directory for install PPD files: Cannot uninstall PPD files."; \
	  exit 1; \
	fi
	@if test -L "$(PPDLINK)/godex"; then \
	  echo $(RM) $(PPDLINK)/godex; \
	  $(RM) $(PPDLINK)/godex; \
	fi
	@cd "$(PPD_OUT_DIR)" \
	&& for testfile in *; do \
	  if test -f "$(DESTDIR)$(PPDDIR)/godex/$$testfile"; then \
	    echo $(RM) "$(DESTDIR)$(PPDDIR)/godex/$$testfile"; \
	    $(RM) "$(DESTDIR)$(PPDDIR)/godex/"$$testfile; \
	  fi; \
	  if test $(SYSTEM_IS_DARWIN) = 1 -a -L "$(PPDLINK)/$$testfile"; then \
	    echo $(RM) "$(PPDLINK)/$$testfile"; \
	    $(RM) "$(PPDLINK)/$$testfile"; \
	  fi; \
	done \
	&& rmdir "$(DESTDIR)$(PPDDIR)/godex" \
	|| exit 0

uninstall-hook:
	test -d $(DESTDIR)$(docdir) && rmdir $(DESTDIR)$(docdir)


# copy ppd files
dist-hook:
	cp -pR ${srcdir}/ppds ${distdir}/ppds
#	$(MKDIR_P) $(distdir)/ppds
#	for dirfile in $(srcdir)/ppds/*; do \
#	  if test -f $$dirfile ; then \
#	    cp -p $$dirfile $(distdir)/ppds/; \
#	  fi \
#	done
#	$(MKDIR_P) "$(PPD_DIST_DIR)"
#	for dirfile in "$(PPD_SRC_DIR)"/*; do \
#	  if test -f $$dirfile ; then \
#	    cp -p $$dirfile "$(PPD_DIST_DIR)"; \
#	  fi \
#	done
# Remove any backup files found in distdir
	$(FIND) $(distdir) -name '.*' -print | xargs $(RM) -rf
	$(FIND) $(distdir) -name '#*' -print | xargs $(RM) -rf
	$(FIND) $(distdir) -name '*~' -print | xargs $(RM) -rf
	$(FIND) $(distdir) -name '_README' -print | xargs $(RM) -rf

