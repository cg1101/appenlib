#!/usr/bin/python

_author  = "Gang Cheng"
_version = "0.2"
_history = """
  0.1  initial version, redirect to temporary file
  0.2  use generic mime-type: application/data to return the file
"""

import os, sys
ESCAPED_CHAR = [' ', '!', '"', '#', '$', '%', '&', "'", '(', ')', 
		'+', ',', '/', 
		':', ';', '<', '=', '>', '?', '@', 
		'[', '\\', ']', '^', '`', 
		'{', '|', '}', '~']

def removeEscape(text):
	for c in ['&', '=']:
		if text.find(c) >= 0:
			raise ValueError, "input error at '%s'" % c
	todo = text.replace('+', ' ')
	done = ''
	n = todo.find('%')
	while n >= 0:
		done += todo[:n]
		t = todo[n:n+3]
		if len(t) < 3:
			raise ValueError, "input error at '%s'" % t
		try: c = chr(int(t[1:], 16))
		except: raise ValueError, "input error at '%s'" % t
		done += c
		todo = todo[n+3:]
		n = todo.find('%')
	done += todo
	return done
		
def getArgumentDict(text):
	"""Return argument dict."""
	if not text: return {}
	pairs = text.split('&')
	buf = []
	for kv in pairs:
		k, v = kv.split('=')
		k = removeEscape(k)
		v = removeEscape(v)
		buf.append((k, v))
	return dict(buf)

def escape_str(text):
	text = text.replace('\\', '\\\\')
	text = text.replace('"', '\\"')
	text = text.replace("'", "\\'")
	return text

# print page header
# document type definition is needed for proper rendering
# if omitted, table rendering will be incorrect
templ = """Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN"
   "http://www.w3.org/TR/REC-html40/strict.dtd">
<HTML>
<HEAD>
<TITLE>Appen library search results</TITLE>
<LINK rel="stylesheet" href="/appenlib/style.css">
</HEAD>
<BODY>
%s
</BODY>
</HTML>"""

# decode query condition
query_str = os.getenv("QUERY_STRING")
argu_dict = getArgumentDict(query_str)

doc_id = argu_dict.get("doc_id", "")
doc_ver = argu_dict.get("doc_ver", "")

if not doc_id:
	print templ % "Sorry, no document ID found in query conditions."
	sys.exit(0)

tmpf = "/var/www/appenlib/tmp/" + doc_id
f = os.popen("/usr/lib/cgi-bin/getdoc.py %s %s %s" % \
		(doc_id, doc_ver, tmpf), "r")
a = f.close()
if a:
	print templ % "Sorry, unable to get document %s, err: %s." \
			% (doc_id, a)
	sys.exit(0)
else:
	pass

print """Content-type: application/data
"""
f = open(tmpf, "rb")
sys.stdout.write(f.read())
f.close()
# !"#$&%'()*+,-./09:;<=>?@AZ[\]^_`az{|}~
