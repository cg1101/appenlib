#!/usr/bin/python

import os, sys

_script  = os.path.basename(sys.argv[0])
_version = "0.2"
_author  = "CHENG, Gang"
_history = """
  0.1  initial draft, use user homedir as tempdir
  0.2  use /home/.appenlib/ as tempdir
"""

if _script in ["-c", ""]: _script = "getdoc.py"

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
	print >> sys.stderr, \
		"Usage: %s [OPTIONS] DOC_ID [DOC_VER] FILE" % _script
	if verbose:
		print >> sys.stderr, \
"""Retrieve a local copy of document from on-line library.

Options:
    --help       print verbose help message
    --version    print program version

DOC_ID is the number of the document to be retrieved. FILE is output
filename. DOC_VER is the version of the document. If omitted, the latest
version will be retrieved.

Return code is 0 if success, 1 if document is not found in library and 2
if trouble.

Report bugs to <it@appen.com.au>."""
		sys.exit(0)
	sys.exit(2)

def escape_str(text):
	text = text.replace('\\', '\\\\')
	text = text.replace('"', '\\"')
	text = text.replace("'", "\\'")
	return text

def main():
	# parse options
	import getopt
	try:
		opts, args = getopt.getopt(sys.argv[1:], "", \
				["help", "version", ])
	except getopt.GetoptError, e:
		logging.error(e.msg)
		usage()

	logfile = None
	silent = False
	for o, a in opts:
		if o in ("-h", "--help"):
			usage(True)
		elif o in ("-v", "--version"):
			print_ver()

	# check commandline arguments
	if len(args) == 0:
		usage()
	if len(args) == 1:
		logging.error("too few arguments")
		usage()
	elif len(args) > 3:
		logging.error("too many arguments")
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

	import re
	doc_id = re.compile("^[dD]?\d+$")
	doc_ver = re.compile("^[vV]?\d+(?:\.\d+)+")
	if doc_id.match(args[0]):
		if args[0][0] in ['d', 'D']: args[0] = args[0][1:]
		doc_id = args[0]
	else:
		logging.error("invalid document id: %s" % args[0])
		sys.exit(2)
	if len(args) == 3:
		if doc_ver.match(args[1]):
			if args[1][0] in ['v', 'V']:
				args[1] = args[1][1:]
			doc_ver = "'{%s}'" % args[1].replace(".", ",")
		else:
			logging.error("invalid version: %s" % args[1])
			sys.exit(2)
	else:
		doc_ver = "NULL"
	target = args[-1]

	# log user info
	import getpass, pwd, shutil, stat
	user = getpass.getuser()
	homedir = pwd.getpwnam(user)[5]
	#tmpdir = os.path.join(homedir, ".appenlib.%d" % os.getpid())
	tmpdir = "/home/.appenlib"
	tmpfile = os.path.join(tmpdir, "dumpdoc.%d" % os.getpid())
	try:
		#os.mkdir(tmpdir, 0777)
		# due to umask, need to change mode
		#mode = os.stat(tmpdir).st_mode
		#mode |= 0777
		# following statement is futile
		#mode |= stat.S_ISUID | stat.S_ISGID
		#os.chmod(tmpdir, mode)
		try:
			# connect db to dump tempfile
			db = pg.DB(dbname='appenlib', host='dbserver', 
					user='staff')
			logging.debug("database connection established")
			sql = "SELECT get_doc_copy(%s, %s, '%s')" % \
				(doc_id, doc_ver, tmpfile)
			res = db.query(sql).getresult()

			# check result
			if res[0][0] == -1:
				logging.info("Sorry, document d%s "\
					"not found" % doc_id)
				sys.exit(1)

			# copy to target, clear temporary files
			shutil.copyfile(tmpfile, target)
			os.remove(tmpfile)
		except IOError, e:
			logging.error("%s: %s" % \
				(e.filename, e.strerror))
			sys.exit(2)
		except pg.InternalError, e:
			logging.error("cannot connect to database: "\
				"%s" % e)
			sys.exit(2)
		except pg.ProgrammingError, e:
			logging.error("database error:\n%s" % e)
			sys.exit(2)
	finally:
		pass
		#os.rmdir(tmpdir)

	# close DB connection
	db.close()
	logging.debug("database connection closed")

	sys.exit(0)
# end of main

if __name__ == "__main__":
	main()

# end of program

