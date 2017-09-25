#!/usr/bin/python

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

def formatVerResult(res):
	if len(res) == 0: return ""
	result = """<DIV class="search_result">
<TABLE border=0 cellspacing=1 cellpadding=4 width="100%">
<TR class="ver_result">
  <TH width="30%">Version</TH>
  <TH width="40%">Updated On</TH>
  <TH width="30%">Updated By</TH>
</TR>"""
	for i in res:
		i["version"] = "v" + i["version"][1:-1].replace(",", ".")
		i["mtime"] = i["mtime"].split(".")[0]
		result += """
<TR class="ver_result">
  <TD><A href="/cgi-bin/getdoc.cgi/d%(doc_id)d?doc_id=d%(doc_id)d&doc_ver=%(version)s">%(version)s</A></TD>
  <TD>%(mtime)s</TD>
  <TD>%(muser)s</TD>
</TR>""" % i
	result += """
</TABLE>
</DIV>"""
	return result

import os, sys

# print page header
# document type definition is needed for proper rendering
# if omitted, table rendering will be incorrect
print """Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN"
   "http://www.w3.org/TR/REC-html40/strict.dtd">
<HTML>
<HEAD>
<TITLE>Document update history</TITLE>
<LINK rel="stylesheet" href="/appenlib/style.css">
<STYLE>
  TR.ver_result { background: #ffeeee; height=30 }
</STYLE>
</HEAD>
<BODY>
<H1><FONT color=blue>Document update history</FONT></H1>
<HR>"""

# decode query condition
query_str = os.getenv("QUERY_STRING")
argu_dict = getArgumentDict(query_str)

# perform db query
import pg
try:
	db = pg.DB(dbname='appenlib', host='dbserver', user='staff')
	if 'doc_id' in argu_dict:
		doc_id = argu_dict['doc_id']
		if doc_id[0] in ('D', 'd'): doc_id = doc_id[1:]
		sql = "select * from doc_list where doc_id=%s " \
			"order by version" % doc_id
	else:
		sql = ""
	# execute query
	res = db.query(sql).dictresult()
except:
	res = []

# DEBUG: output query condition
#print "<P>Query condition: %r<P>" % argu_dict

# print result summary
total = len(res)
if total == 0:
	msg = "Sorry, document d%s no found" % doc_id
elif total == 1:
	msg = "Found 1 version of document d%s in library" % doc_id
else:
	msg = "Found %d versions of document d%s in library" % (total, doc_id)
print "<P><FONT size=4>%s</FONT>" % msg

# iterate result
print formatVerResult(res)

# print page footer
#print """<HR>
#<FONT size=2>Send comments to <A href="mailto:it@appen.com.au">it@appen.com.au</A>.</FONT>
#"""
print """</BODY>
</HTML>"""
# !"#$&%'()*+,-./09:;<=>?@AZ[\]^_`az{|}~
