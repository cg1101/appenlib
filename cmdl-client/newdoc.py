#!/usr/bin/python

import os, sys

_script  = os.path.basename(sys.argv[0])
_version = "0.1"
_author  = "CHENG, Gang"
_history = """
"""

if _script in ["-c", ""]: _script = "newdoc.py"

# set up default logging
import logging
logging.getLogger("").setLevel(logging.DEBUG)
handler = logging.StreamHandler()
handler.setLevel(logging.WARNING)
handler.setFormatter(logging.Formatter(_script + ": %(message)s"))
logging.getLogger("").addHandler(handler)

# postgresql module is mandatory
try:
	import pg
except ImportError:
	logging.error("cannot proceed without postgresql module")
	sys.exit(1)

# define helper functions
def print_ver():
	print >> sys.stderr, "%s %s\nWritten by \033[4m%s\033[0m.\n" % \
			(_script, _version, _author)
	sys.exit(0)

def usage(verbose=False):
	print >> sys.stderr, "Usage: %s [OPTIONS]" % _script
	if verbose:
		print >> sys.stderr, \
"""Create a new document in Appen library.

Options:
    --help       print verbose help message
    --version    print program version

    --author  a  add an author
    --keyword k  add a keyword
    --title   t  document title (default: untitled)
    --verstr  v  document version string (default version: v0.1)
    --doctype d  document type (default: Misc)
    --memo    m  comments for this document
    --file    f  file path of input file

Create a new document in Appen library and return document ID. If a 
mandatory argument is omitted, user will be prompted to input one.

Report bugs to <it@appen.com.au>."""
		sys.exit(0)
	sys.exit(2)

def escape_str(text):
	text = text.replace('\\', '\\\\')
	text = text.replace('"', '\\"')
	text = text.replace("'", "\\'")
	return text

import re
_verpattern = re.compile(r"[Vv]?\d+\.\d+(?:\.\d+)*")
def formatVerstr(text):
	if not _verpattern.match(text): return ""
	if text[0] in ["V", "v"]: text = text[1:]
	return "'{" + text.replace(".", ",") + "}'"

def formatFpath(text):
	if not (os.path.isfile(text) and os.access(text, os.R_OK)):
		return ""
	text = os.path.normpath(text)
	text = text.replace(r"\'", r"\\\'")
	return "'" + text + "'"

def main():
	# parse options
	import getopt
	try:
		opts, args = getopt.gnu_getopt(sys.argv[1:], "", \
				["help", "version", \
				"doctype=", "verstr=", "title=", "author=", \
				"keyword=", "memo=", "file=", "baselined"])
	except getopt.GetoptError, e:
		logging.error(e.msg)
		usage()

	logfile = None
	silent = False

	doctype = "Misc"
	verstr = "'{0,1}'"
	title = ""
	author = []
	keyword = []
	memo = None
	fpath = ""
	baselined = False

	for o, a in opts:
		if o in ("--help"):
			usage(True)
		elif o in ("--version"):
			print_ver()
		elif o in ("--doctype"):
			if not a.strip(): a = "Misc"
			doctype = a
		elif o in ("--verstr"):
			verstr = formatVerstr(a)
			if not verstr:
				logging.error("invalid version format: '%s'" % a)
				sys.exit(2)
		elif o in ("--title"):
			if not a.strip(): a = "untitled"
			title = a
		elif o in ("--author"):
			a = a.strip()
			if a: author.append(a)
		elif o in ("--keyword"):
			a = a.split()
			if a: keyword.extend(a)
		elif o in ("--memo"):
			memo = a
		elif o in ("--file"):
			fpath = formatFpath(a)
			if not fpath:
				logging.error("cannot read file: '%s'" % a)
				sys.exit(2)
		elif o in ("--baselined"):
			baselined = True

	# check commandline arguments
	if len(args) > 0:
		usage()

	# set up extended logging options
	if not silent:
		class InfoOnlyFilter(logging.Filter):
			def filter(self, record):
				if record.levelno == logging.INFO:
					return 1
				return 0
		verboser = logging.StreamHandler()
		verboser.setLevel(logging.INFO)
		verboser.addFilter(InfoOnlyFilter())
		formatter = logging.Formatter("%(message)s")
		verboser.setFormatter(formatter)
		logging.getLogger("").addHandler(verboser)
	if logfile:
		flogger = logging.FileHandler(logfile, "a")
		flogger.setLevel(logging.DEBUG)
		formatter = logging.Formatter(\
			fmt='%(asctime)s %(levelname)-8s %(message)s', 
			datefmt='%Y-%m-%d %H:%M')
		flogger.setFormatter(formatter)
		logging.getLogger("").addHandler(flogger)

	# check user info
	import getpass, pwd
	try:
		user = getpass.getuser()
		pwddbentry = pwd.getpwnam(user)
		fullname = pwddbentry[4].split(",")[0]
		def_auth = "(%s <%s@appen.com.au>)" % (fullname, user)
	except:
		def_auth = ""

	try:
		while not title:
			title = raw_input("Please enter document title-> ")
			if not title.strip(): title = "untitled"
		title = "'%s'" % escape_str(title)
		while not author:
			a = raw_input("Please enter author%s-> " % def_auth)
			a = a.strip()
			if not a: a = def_auth[1:-1]
			if a: author.append(a)
			while True:
				a = raw_input("Please enter additional author-> ")
				a = a.strip()
				if not a: break
				author.append(a)
		author = "'{\"%s\"}'" % '","'.join([escape_str(i) \
				for i in author])
		while not keyword:
			a = raw_input("Please enter keyword-> ")
			keyword = a.split()
		keyword = "'{\"%s\"}'" % '","'.join([escape_str(i) \
				for i in keyword])
		if not memo:
			memo = "NULL"
		else:
			memo = "'" + memo + "'"
		while not fpath:
			a = raw_input("Please enter input file-> ")
			fpath = formatFpath(a)
			if not fpath:
				logging.error("cannot read file: '%s'" % a)
				logging.info("try again...")
		db = pg.DB(dbname='appenlib', host='dbserver', 
				user='staff')
		logging.debug("database connection established")
		sql = "SELECT create_doc('%s', %s, %s, "\
			"%s, %s, %s, %s)" % (doctype, verstr, title, \
			author, keyword, memo, fpath)
		#logging.info(sql)
		res = db.query(sql).getresult()
		doc_id = res[0][0]
		if doc_id > 0:
			print "New document created: d%d" % res[0][0]
		else:
			print "Document creation failed"
			sys.exit(2)
	except KeyboardInterrupt:
		logging.error("user canceled operation")
		sys.exit(126)
	except pg.InternalError, e:
		logging.error("cannot connect to database: %s" % e)
		sys.exit(1)
	except pg.ProgrammingError, e:
		logging.error("database error occurred, update failed")
		sys.exit(1)
	else:
		# close DB connection
		db.close()
		logging.debug("database connection closed")
	sys.exit(0)
# end of main

if __name__ == "__main__":
	main()

# end of program

