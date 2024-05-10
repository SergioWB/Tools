#                                               -*- Autoconf -*-
# Process this file with autoconf to produce a configure script.

AC_PREREQ([2.69])
AC_INIT([rastertoezpl],[1.1.9],[techgt@godexintl.com])
AM_INIT_AUTOMAKE([-Wall -Werror foreign])
AC_CONFIG_SRCDIR([src/rastertoezpl.c])
AC_CONFIG_HEADER([config.h])

# Checks for programs.
AC_PROG_CC
AC_PROG_LN_S
AC_PATH_PROG([FIND], [find])
AC_PATH_PROG([PPDC], [ppdc])
if test -z $PPDC; then
	AC_MSG_WARN([This program is required for build PPDs file!])
fi

dnl Check for cups-config
AC_PATH_PROG([CUPS_CONFIG], [cups-config])
if test -z $CUPS_CONFIG; then
	AC_MSG_ERROR([This program is required!])
fi


# Checks for libraries.
## AC_CHECK_LIB(cupsimage, cupsParseOptions)
## AC_CHECK_LIB set LIBS and too define HAVE_LIB<library> ...
dnl Libraries from CUPS_CONFIG
LIBS="$LIBS `\"$CUPS_CONFIG\" --image --libs 2>/dev/null`"
AC_MSG_NOTICE([LIBS: "$LIBS"])


# Checks for header files.
AC_HEADER_STDC
AC_CHECK_HEADERS([fcntl.h signal.h errno.h], [], AC_MSG_ERROR([This header file is required!]))
AC_CHECK_HEADERS([cups/cups.h cups/raster.h], [], AC_MSG_ERROR([This header file is required!]))


# Checks for typedefs, structures, and compiler characteristics.
AC_C_CONST
# Is it a good result, add flag from cups_config?
CFLAGS="$CFLAGS `\"$CUPS_CONFIG\" --cflags 2>/dev/null`"
AC_MSG_NOTICE([CFLAGS: "$CFLAGS"])

# Define VERSION
CPPFLAGS="$CPPFLAGS -DVERSION='\"$VERSION\"'"
AC_MSG_NOTICE([CPPFLAGS: "$CPPFLAGS"])

# Checks for library functions.
AC_FUNC_MALLOC
AC_FUNC_MEMCMP
AC_DIAGNOSE([obsolete],[your code may safely assume C89 semantics that RETSIGTYPE is void.
Remove this warning and the `AC_CACHE_CHECK' when you adjust the code.])dnl
AC_CACHE_CHECK([return type of signal handlers],[ac_cv_type_signal],[AC_COMPILE_IFELSE(
[AC_LANG_PROGRAM([#include <sys/types.h>
#include <signal.h>
],
		 [return *(signal (0, 0)) (0) == 1;])],
		   [ac_cv_type_signal=int],
		   [ac_cv_type_signal=void])])
AC_DEFINE_UNQUOTED([RETSIGTYPE],[$ac_cv_type_signal],[Define as the return type of signal handlers
		    (`int' or `void').])

AC_CHECK_FUNCS([memset])


dnl Use cups-config to find CUPS directories
if test -n "$CUPS_CONFIG" && test -z "$CUPS_SERVERBIN"; then
        CUPS_SERVERBIN=`"$CUPS_CONFIG" --serverbin 2>/dev/null`
fi
if test -n "$CUPS_SERVERBIN"; then
        CUPS=$CUPS_SERVERBIN
        CUPS_FILTERS="$CUPS_SERVERBIN/filter"
        CUPS_BACKENDS="$CUPS_SERVERBIN/backend"
        AC_SUBST([CUPS])
        AC_SUBST([CUPS_FILTERS])
        AC_SUBST([CUPS_BACKENDS])
else
        # Check for /usr/lib/cups/filter/
	if test -d "/usr/lib/cups/filter/"; then
        	CUPS_FILTERS="/usr/lib/cups/filter/"
	else
		AC_MSG_ERROR([Not found CUPS filter path! Use CUPS_SERVERBIN=/path/to/cups/ to set CUPS path.])
	fi
fi

dnl Directories for install PPD files
AC_MSG_CHECKING([for PPD directory])
if test -z "$PPDDIR"; then
	PPDDIR=${datarootdir}/ppd
	AC_SUBST([PPDDIR])
fi
AC_MSG_RESULT([$PPDDIR])


### The installation path of PPDs (/usr/local/share/ppd/) is default search by CUPS in Linux, but isn't search in Darwin.
### A symbolic path to system path of PPDs is created when CREATE_PPDLINK is defined or if system is Darwin.
dnl Find directory for links to PPDDIR
if test "`(uname -s) 2>/dev/null`" = "Darwin"; then
	SYSTEM_IS_DARWIN=1
else
	SYSTEM_IS_DARWIN=0
fi
if test -n "$PPDLINK" -o -n "$CREATE_PPDLINK" -o "$SYSTEM_IS_DARWIN" = 1; then
	AC_MSG_CHECKING([where create symbolick link to PPD])
	PPD_DIRS="/usr/share/ppd /usr/local/share/ppd /opt/share/ppd"
	if test "$SYSTEM_IS_DARWIN" = 1; then
		PPD_DIRS="/Library/Printers/PPDs/Contents/Resources/ $PPD_DIRS"
	fi
	if test -z "$PPDLINK"; then
		for dirfile in $PPD_DIRS; do
			echo test '${dirfile}' -ef '${PPDDIR}';
			# if the directory is the same
			test '${dirfile}' -ef '${PPDDIR}' && PPDLINK="X" && break;
			echo test -d "$dirfile" -a -n "$PPDDIR";
			test -d "$dirfile" -a -n "$PPDDIR" && PPDLINK="$dirfile" && break;
		done
	fi
	if test -z "$PPDLINK"; then
		AC_MSG_RESULT([no create])
		AC_MSG_WARN([Do not create symbolic link to PPD directory; nothing found.])
	fi
	if test "$PPDLINK" = "X"; then
		AC_MSG_RESULT([no create])
		AC_MSG_NOTICE([Do not create symbolic link to PPD directory; PPDDIR is the same as PPDLINK.])
		PPDLINK=""
	fi
	if test -n "$PPDLINK" -a ! -d "$PPDLINK"; then
		AC_MSG_RESULT([no create])
		AC_MSG_WARN([Do not create symbolic link to PPD directory; PPDLINK is not directory!])
		PPDLINK=""
	fi
	test -n "$PPDLINK" && AC_MSG_RESULT([$PPDLINK])
	AC_SUBST([PPDLINK])
	AC_SUBST([SYSTEM_IS_DARWIN])
	PPD_DIRS=
else
	AC_MSG_NOTICE([Do not create symbolic link to PPD directory; the link is not required.])
fi


AC_CONFIG_FILES([
	Makefile
	src/Makefile
])
AC_OUTPUT
