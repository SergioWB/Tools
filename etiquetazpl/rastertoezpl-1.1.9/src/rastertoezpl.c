/*
 * "$Id: rastertoezpl.c 2012-09-04 hamic $"
 * "$Id: rastertoezpl.c 2009-11-20 hamic $"
 *   Copyright 2009, 2012 by Godex Europe GmbH.
 *
 *   This file is based on rastertolabel.c from CUPS 1.3.8
 *
 * "$Id: rastertolabel.c 7721 2008-07-11 22:48:49Z mike $"
 *
 *   Label printer filter for the Common UNIX Printing System (CUPS).
 *
 *   Copyright 2007-2008 by Apple Inc.
 *   Copyright 2001-2007 by Easy Software Products.
 *
 *   These coded instructions, statements, and computer programs are the
 *   property of Apple Inc. and are protected by Federal copyright
 *   law.  Distribution and use rights are outlined in the file "LICENSE.txt"
 *   which should have been included with this file.  If this file is
 *   file is missing or damaged, see the license at "http://www.cups.org/".
 *
 *   This file is subject to the Apple OS-Developed Software exception.
 *
 * Contents:
 *
 *   Setup()        - Prepare the printer for printing.
 *   StartPage()    - Start a page of graphics.
 *   EndPage()      - Finish a page of graphics.
 *   CancelJob()    - Cancel the current job...
 *   OutputLine()   - Output a line of graphics.
 *   GDXCompress()  - Output compressed line for Godex printers
 *   main()         - Main entry and processing of driver.
 */

/*
 * Include necessary headers...
 */

#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <signal.h>
#include <errno.h>

#include <cups/cups.h>
#include <cups/ppd.h>
#include <cups/raster.h>
/*
 * on some system the CUPS is instaled without this header file :-( ...
 * #include <cups/i18n.h>
 */

/*
 * This driver filter currently supports Godex printers.
 *
 * The Godex portion of the driver has been developod for the EZ DT2, EZ DT4,
 * EZ-1200+, EZ-1300+, EZ-2200+, EZ-2300+, EZ-6200+ and EZ-6300+  label
 * printers; it may also work with other models.  The Godex printers support
 * printing at 203, and 300 DPI.
 *
 */

/*
 * Model number constants...
 */

#define GODEX_EZPL	0x30	/* Godex EZPL printers */

#define GDX_BUFFER_HEIGHT	8	/* number of lines in CompBuffer */

#define GDX_EOL		"\x0D"	/* EZPL end of command (line) == CR */

/*
 * preprocessor parameter VERSION may be defined by configure.
 */

/*
 * Globals...
 */

unsigned char	*Buffer;		/* Output buffer */
unsigned char	*CompBuffer;		/* Compression buffer */
unsigned char	*LastBuffer;		/* Last buffer */
int		LastSet;		/* Number of repeat characters */
int		ModelNumber,		/* cupsModelNumber attribute */
		Page,			/* Current page */
		Feed,			/* Number of lines to skip */
		Canceled;		/* Non-zero if job is canceled */


/*
 * Prototypes...
 */

void	Setup(ppd_file_t *ppd);
void	StartPage(ppd_file_t *ppd, cups_page_header2_t *header);
void	EndPage(ppd_file_t *ppd, cups_page_header2_t *header);
void	CancelJob(int sig);
void	OutputLine(ppd_file_t *ppd, cups_page_header2_t *header, int y);
void	GDXCompress(unsigned char *line, int length, int row);


/*
 * 'Setup()' - Prepare the printer for printing.
 */

void
Setup(ppd_file_t *ppd)			/* I - PPD file */
{
  int		i;			/* Looping var */


 /*
  * Get the model number from the PPD file...
  */

  if (ppd)
    ModelNumber = ppd->model_number;
    

 /*
  * Initialize based on the model number...
  */

  switch (ModelNumber)
  {
    case GODEX_EZPL :
      break;
  }
}


/*
 * 'StartPage()' - Start a page of graphics.
 */

void
StartPage(ppd_file_t         *ppd,	/* I - PPD file */
          cups_page_header2_t *header)	/* I - Page header */
{
  ppd_choice_t	*choice;		/* Marked choice */
  int		length;			/* Actual label length */
  int		itmp;


 /*
  * Show page device dictionary...
  */

  fprintf(stderr, "DEBUG: StartPage...\n");
  fprintf(stderr, "DEBUG: MediaClass = \"%s\"\n", header->MediaClass);
  fprintf(stderr, "DEBUG: MediaColor = \"%s\"\n", header->MediaColor);
  fprintf(stderr, "DEBUG: MediaType = \"%s\"\n", header->MediaType);
  fprintf(stderr, "DEBUG: OutputType = \"%s\"\n", header->OutputType);

  fprintf(stderr, "DEBUG: AdvanceDistance = %d\n", header->AdvanceDistance);
  fprintf(stderr, "DEBUG: AdvanceMedia = %d\n", header->AdvanceMedia);
  fprintf(stderr, "DEBUG: Collate = %d\n", header->Collate);
  fprintf(stderr, "DEBUG: CutMedia = %d\n", header->CutMedia);
  fprintf(stderr, "DEBUG: Duplex = %d\n", header->Duplex);
  fprintf(stderr, "DEBUG: HWResolution = [ %d %d ]\n", header->HWResolution[0],
          header->HWResolution[1]);
  fprintf(stderr, "DEBUG: ImagingBoundingBox = [ %d %d %d %d ]\n",
          header->ImagingBoundingBox[0], header->ImagingBoundingBox[1],
          header->ImagingBoundingBox[2], header->ImagingBoundingBox[3]);
  fprintf(stderr, "DEBUG: InsertSheet = %d\n", header->InsertSheet);
  fprintf(stderr, "DEBUG: Jog = %d\n", header->Jog);
  fprintf(stderr, "DEBUG: LeadingEdge = %d\n", header->LeadingEdge);
  fprintf(stderr, "DEBUG: Margins = [ %d %d ]\n", header->Margins[0],
          header->Margins[1]);
  fprintf(stderr, "DEBUG: ManualFeed = %d\n", header->ManualFeed);
  fprintf(stderr, "DEBUG: MediaPosition = %d\n", header->MediaPosition);
  fprintf(stderr, "DEBUG: MediaWeight = %d\n", header->MediaWeight);
  fprintf(stderr, "DEBUG: MirrorPrint = %d\n", header->MirrorPrint);
  fprintf(stderr, "DEBUG: NegativePrint = %d\n", header->NegativePrint);
  fprintf(stderr, "DEBUG: NumCopies = %d\n", header->NumCopies);
  fprintf(stderr, "DEBUG: Orientation = %d\n", header->Orientation);
  fprintf(stderr, "DEBUG: OutputFaceUp = %d\n", header->OutputFaceUp);
  fprintf(stderr, "DEBUG: PageSize = [ %d %d ]\n", header->PageSize[0],
          header->PageSize[1]);
  fprintf(stderr, "DEBUG: Separations = %d\n", header->Separations);
  fprintf(stderr, "DEBUG: TraySwitch = %d\n", header->TraySwitch);
  fprintf(stderr, "DEBUG: Tumble = %d\n", header->Tumble);
  fprintf(stderr, "DEBUG: cupsWidth = %d\n", header->cupsWidth);
  fprintf(stderr, "DEBUG: cupsHeight = %d\n", header->cupsHeight);
  fprintf(stderr, "DEBUG: cupsMediaType = %d\n", header->cupsMediaType);
  fprintf(stderr, "DEBUG: cupsBitsPerColor = %d\n", header->cupsBitsPerColor);
  fprintf(stderr, "DEBUG: cupsBitsPerPixel = %d\n", header->cupsBitsPerPixel);
  fprintf(stderr, "DEBUG: cupsBytesPerLine = %d\n", header->cupsBytesPerLine);
  fprintf(stderr, "DEBUG: cupsColorOrder = %d\n", header->cupsColorOrder);
  fprintf(stderr, "DEBUG: cupsColorSpace = %d\n", header->cupsColorSpace);
  fprintf(stderr, "DEBUG: cupsCompression = %d\n", header->cupsCompression);
  fprintf(stderr, "DEBUG: cupsRowCount = %d\n", header->cupsRowCount);
  fprintf(stderr, "DEBUG: cupsRowFeed = %d\n", header->cupsRowFeed);
  fprintf(stderr, "DEBUG: cupsRowStep = %d\n", header->cupsRowStep);

  switch (ModelNumber)
  {
    case GODEX_EZPL :
      /*
       * Setup printer/job attributes...
       */
   
      /*
       * Set Paper length and type
       * (^Q{width},{gap length}   or
       *  ^Q{width},0,{feed length}   or
       *  ^Q{width},{mark length},{mark position}{sign})
       *  - gap label:  gap length > 0
       *  - cont paper: gap length == 0
       *  - black mark: mark length > 0
       */
      length = (header->PageSize[1] + 1) * 127 / 360;
      printf("^Q%d", length);
      if ((choice = ppdFindMarkedChoice(ppd, "gdxBlackMark")) != NULL
        && strcmp(choice->choice, "none")) { /* black mark labels */
        printf(",%d", atoi(choice->choice));
        if ((choice = ppdFindMarkedChoice(ppd, "gdxBlackPos")) != NULL
          && strcmp(choice->choice, "none")) {
          itmp = atoi(choice->choice);
          printf(",%d%c" GDX_EOL, abs(itmp), itmp>=0?'+':'-');
        } else 
          printf(",0+" GDX_EOL);
      } else {
        if ((choice = ppdFindMarkedChoice(ppd, "gdxGapLength")) != NULL) {
          itmp = atoi(choice->choice);
          if (itmp != 0) /* labels */
            printf(",%d" GDX_EOL, atoi(choice->choice));
          else {/* plain paper */
            printf(",%d,0" GDX_EOL, atoi(choice->choice));
          }
        } else /* nothing entered, must any send */
          printf(",2" GDX_EOL);
      }
   
      /*
       * Set paper width
       */
      /* length (label width) is need for rotate*/
      length = (header->PageSize[0] + 1) * 127 / 360;
      printf("^W%d" GDX_EOL, length);
   
   
      /*
       * Set orientations (180deg only)
       * (~Rx, x in mm; for rotate: x={label width}, normal: x>{head width})
       */
      switch (header->Orientation) {
        case CUPS_ORIENT_0: /* 0deg */
          printf("~R200" GDX_EOL);
          break;
        case CUPS_ORIENT_180: /* 180deg */
          printf("~R%d" GDX_EOL, length);
          break;
      }
   
      /*
       * Set Printing mode
       */
      if ((choice = ppdFindMarkedChoice(ppd, "gdxMedia")) != NULL
        && strcmp(choice->choice, "none")) {
        if (strcmp(choice->choice, "tt") == 0)
          printf("^AT" GDX_EOL);
        else if (strcmp(choice->choice, "dt") == 0)
          printf("^AD" GDX_EOL);
      }
   
      /*
       * Set print rate...
       */
   
      if ((choice = ppdFindMarkedChoice(ppd, "gdxRate")) != NULL
        && strcmp(choice->choice, "none"))
        printf("^S%d" GDX_EOL, atoi(choice->choice));
   
      /*
       * Set darkness...
       *   ?? on another printers cupsCompression use 0-100
       */
      if (header->cupsCompression > 0 && header->cupsCompression <= 19)
        printf("^H%02d" GDX_EOL, header->cupsCompression);
   
      /*
       * Set stop position
       *   gdxOffest 0-40mm
       */
      if ((choice = ppdFindMarkedChoice(ppd, "gdxOffset")) != NULL
        && strcmp(choice->choice, "none"))
        printf("^E%d" GDX_EOL, atoi(choice->choice));
   
      /*
       * Set top position (+/-100 dots)
       */
      if ((choice = ppdFindMarkedChoice(ppd, "gdxTop")) != NULL
        && strcmp(choice->choice, "none"))
        printf("~Q%+d" GDX_EOL, atoi(choice->choice));
   
      /*
       * Set left margin (0 - 399 dots)
       */
      if ((choice = ppdFindMarkedChoice(ppd, "gdxLeft")) != NULL
        && strcmp(choice->choice, "none"))
        printf("^R%d" GDX_EOL, atoi(choice->choice));
   
      /*
       * Set after print, and number of labels for cutter
       */
      if ((choice = ppdFindMarkedChoice(ppd, "gdxMode")) != NULL
        && strcmp(choice->choice, "none")
        && header->CutMedia == CUPS_CUT_NONE) {
        if (strcmp(choice->choice, "rew") == 0) /* rewind */
          printf("^D0" GDX_EOL "^O0" GDX_EOL);
        else if (strcmp(choice->choice, "str") == 0) /* stripper */
          printf("^D0" GDX_EOL "^O1" GDX_EOL);
        else if (strcmp(choice->choice, "app") == 0) /* applicator */
          printf("^D0" GDX_EOL "^O2" GDX_EOL);
      }
      if (header->CutMedia == CUPS_CUT_PAGE) /* cut page */
        printf("^D1" GDX_EOL "^O0" GDX_EOL);
      else if (header->CutMedia == CUPS_CUT_SET) /* cut set */
        printf("^D%d" GDX_EOL "^O0" GDX_EOL, header->NumCopies);
      /* TODO: cut files */
      /*else if (header->CutMedia == CUPS_CUT_FILE)
        printf("^D1" GDX_EOL "^O0" GDX_EOL);
      */
   
      /*
       * Set Number of copies
       */
      printf("^P%d" GDX_EOL, header->NumCopies);
   
      /*
       * Set start label, label format (inverse, mirror)
       */
      printf("^L");
      if (header->NegativePrint)
        printf("I");
      if (header->MirrorPrint)
        printf("M");
      printf(GDX_EOL);
   
      CompBuffer = malloc(GDX_BUFFER_HEIGHT * header->cupsBytesPerLine);
      if (CompBuffer == NULL) {
        fputs("WARNING: failed to allocate compress buffer. ", stderr);
        fputs("Current page will not be optimized.\n", stderr);
      }
      break;
  }

 /*
  * Allocate memory for a line of graphics...
  */

  Buffer = malloc(header->cupsBytesPerLine);
  Feed   = 0;
}


/*
 * 'EndPage()' - Finish a page of graphics.
 */

void
EndPage(ppd_file_t *ppd,		/* I - PPD file */
        cups_page_header2_t *header)	/* I - Page header */
{
  int		val;			/* Option value */
  ppd_choice_t	*choice;		/* Marked choice */


  switch (ModelNumber)
  {
  case GODEX_EZPL :
    GDXCompress(NULL, header->cupsBytesPerLine, -1);
    printf("E" GDX_EOL);
    free(CompBuffer);
    break;
  }

  fflush(stdout);

  /*
   * Free memory...
   */

  free(Buffer);
}


/*
 * 'CancelJob()' - Cancel the current job...
 */

	void
CancelJob(int sig)			/* I - Signal */
{
  /*
   * Tell the main loop to stop...
   */

  (void)sig;

  Canceled = 1;
}


/*
 * 'OutputLine()' - Output a line of graphics...
 */

	void
OutputLine(ppd_file_t         *ppd,	/* I - PPD file */
		cups_page_header2_t *header,	/* I - Page header */
		int                y)	/* I - Line number */
{
  switch (ModelNumber)
  {
    case GODEX_EZPL :
      GDXCompress(Buffer, header->cupsBytesPerLine, y);
      break;
  }
}


/*
 * 'GDXCompress()' - create block of lines
 *   when the block is full, send only non zeros columns.
 *
 * Data from line is stored in global defined CompBuffer. When CompBuffer is
 * full or parameter line is NULL (end of paper), data from CompBuffer in
 * optimalized form is send to stdout.
 * 
 * If CompBuffer is NULL, data from line is send in raw format.
 *
 * Needed size of CompBuffer is (GDX_BUFFER_HEIGHT * length);
 *
 * The parameter length have to have the same value in one compressed cycle.
 *
 */

	void
GDXCompress(unsigned char *line,	/* line to commpress, if NULL, send all data from buffer*/
		int		length,	/* length of line */
		int		row)		/* row on paper */
{
  int i, j;
  int begin,  /* begin of not null column */
      zeros;  /* count of zeros column */
  static int count=0,    /* number of lines in CompBuffer*/
             firstRow=0; /* position of first row in CompBuffer*/
#define GDX_MIN_ZERO_COLUMNS 3 /* when number of zeros column in row is */
                               /* smaller, send it as data */
  
  if (CompBuffer == NULL && line != NULL) { /* no CompBuffer ... */
    printf("Q0,%d,%d,1" GDX_EOL, row, length);
    fwrite(line, 1, length, stdout);
    printf(GDX_EOL);
    return;
  }

  /* when CompBuffer is full or is end of paper, print CompBuffer */
  if (count == GDX_BUFFER_HEIGHT || line == NULL) {
    begin = -1;
    zeros = 0;
    /* check all columns */
    for (i = 0; i < length; i++) {
      for (j = 0; j < count; j++) {
        if (CompBuffer[i + j * length] != 0)
          break;
      }
      if (j == count) { /* column is from zeros */
        zeros++;
      } else {
        if (begin < 0) { /* same zeros, begin is move */
          begin = i;
          zeros = 0;
        /* zero's columns are few */
        } else if (zeros < GDX_MIN_ZERO_COLUMNS)
          zeros = 0;
      }
      /* non zeros place OR end loop with data */
      if ((zeros >= GDX_MIN_ZERO_COLUMNS && begin >= 0)
        || (i + 1 == length && begin >= 0)
        ) {
        /* todo: we can check and remove first and last empty lines .... */
        printf("Q%d,%d,%d,%d" GDX_EOL, begin * 8, 
          firstRow,
          i - begin - zeros + 1, count);
        for (j = 0; j < count; j++)
          fwrite(CompBuffer + begin + j*length,
            1, i - begin - zeros + 1, stdout);
    	printf(GDX_EOL);
        begin = -1;
        zeros = 0;
      }
    }
    count = 0;
  }

  if (line != NULL) {
    i = 0;
    if (count == 0) {
      /* Is the first line empty? */
      for (i=0; i < length && line[i] == 0; i++)
        ;
      if (i < length)
        firstRow = row;
    }
    if (i < length) {
      memcpy(CompBuffer + (length*(count)), line, length);
      (count)++;
    }
  }
#undef GDX_MIN_ZERO_COLUMNS
}


/*
 * 'main()' - Main entry and processing of driver.
 */

int					/* O - Exit status */
main(int  argc,				/* I - Number of command-line arguments */
     char *argv[])			/* I - Command-line arguments */
{
  int			fd;		/* File descriptor */
  cups_raster_t		*ras;		/* Raster stream for printing */
  cups_page_header2_t	header;		/* Page header from file */
  int			y;		/* Current line */
  ppd_file_t		*ppd;		/* PPD file */
  int			num_options;	/* Number of options */
  cups_option_t		*options;	/* Options */
#if defined(HAVE_SIGACTION) && !defined(HAVE_SIGSET)
  struct sigaction action;		/* Actions for POSIX signals */
#endif /* HAVE_SIGACTION && !HAVE_SIGSET */


 /*
  * Make sure status messages are not buffered...
  */

  setbuf(stderr, NULL);

 /*
  * Check command-line...
  */

  if (argc < 6 || argc > 7)
  {
   /*
    * We don't have the correct number of arguments; write an error message
    * and return.
    */

    fprintf(stderr,
                    "Usage: %s job-id user title copies options [file]\n",
                    argv[0]);
#ifdef VERSION
    fprintf(stderr, "Version: %s\n", VERSION);
#endif
    return (1);
  }

 /*
  * Open the page stream...
  */

  if (argc == 7)
  {
    if ((fd = open(argv[6], O_RDONLY)) == -1)
    {
//      _cupsLangPrintf(stderr, _("ERROR: Unable to open raster file - \n"));
      fprintf(stderr, "ERROR: Unable to open raster file - %s\n",
                      strerror(errno));
      sleep(1);
      return (1);
    }
  }
  else
    fd = 0;

  ras = cupsRasterOpen(fd, CUPS_RASTER_READ);

 /*
  * Register a signal handler to eject the current page if the
  * job is cancelled.
  */

  Canceled = 0;

#ifdef HAVE_SIGSET /* Use System V signals over POSIX to avoid bugs */
  sigset(SIGTERM, CancelJob);
#elif defined(HAVE_SIGACTION)
  memset(&action, 0, sizeof(action));

  sigemptyset(&action.sa_mask);
  action.sa_handler = CancelJob;
  sigaction(SIGTERM, &action, NULL);
#else
  signal(SIGTERM, CancelJob);
#endif /* HAVE_SIGSET */

 /*
  * Open the PPD file and apply options...
  */

  num_options = cupsParseOptions(argv[5], 0, &options);

  if ((ppd = ppdOpenFile(getenv("PPD"))) != NULL)
  {
    ppdMarkDefaults(ppd);
    cupsMarkOptions(ppd, num_options, options);
  }

 /*
  * Initialize the print device...
  */

  Setup(ppd);

 /*
  * Process pages as needed...
  */

  Page = 0;

  while (cupsRasterReadHeader2(ras, &header))
  {
   /*
    * Write a status message with the page number and number of copies.
    */

    if (Canceled)
      break;

    Page ++;

    fprintf(stderr, "PAGE: %d 1\n", Page);

   /*
    * Start the page...
    */

    StartPage(ppd, &header);

   /*
    * Loop for each line on the page...
    */

    for (y = 0; y < header.cupsHeight && !Canceled; y ++)
    {
     /*
      * Let the user know how far we have progressed...
      */

      if (Canceled)
        break;

      if ((y & 15) == 0)
        fprintf(stderr, "INFO: Printing page %d, %d%% complete...\n",
                        Page, 100 * y / header.cupsHeight);

     /*
      * Read a line of graphics...
      */

      if (cupsRasterReadPixels(ras, Buffer, header.cupsBytesPerLine) < 1)
        break;

     /*
      * Write it to the printer...
      */

      OutputLine(ppd, &header, y);
    }

   /*
    * Eject the page...
    */

    EndPage(ppd, &header);

    if (Canceled)
      break;
  }

 /*
  * Close the raster stream...
  */

  cupsRasterClose(ras);
  if (fd != 0)
    close(fd);

 /*
  * Close the PPD file and free the options...
  */

  ppdClose(ppd);
  cupsFreeOptions(num_options, options);

 /*
  * If no pages were printed, send an error message...
  */

  if (Page == 0)
    fputs("ERROR: No pages found!\n", stderr);
  else
    fputs("INFO: Ready to print.\n", stderr);

  return (Page == 0);
}


/*
 * End of "$Id: rastertolabel.c 7721 2008-07-11 22:48:49Z mike $".
 * End of "$Id: rastertoezpl.c 20091120".
 */
