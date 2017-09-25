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

def formatRecord(rec):
	return """<DIV class="search_result">
<TABLE width="100%%" border=0 cellspacing=1 cellpadding=4>
<TR class="search_result">
  <TD class="doc_id">d%(doc_id)d</TD>
  <TD width="15%%"><a href="/cgi-bin/dispver.cgi?doc_id=d%(doc_id)d" title="Check versions">Versions</A></TD>
  <TD><A href="/cgi-bin/getdoc.cgi/d%(doc_id)d?doc_id=d%(doc_id)d" title="Get latest version">Get File</A></TD>
</TR>
<TR class="search_result">
  <TH class="search_result">Title:</TH>
  <TD colspan="2">%(title)s</TD>
</TR>
<TR class="search_result">
  <TH class="search_result">Author(s):</TH>
  <TD colspan="2">%(author)s</TD>
</TR>
<TR class="search_result">
  <TH class="search_result">Keyword:</TH>
  <TD colspan="2">%(keyword)s</TD>
</TR>
<TR class="search_result">
  <TH class="search_result">Version:</TH>
  <TD colspan="2">%(version)s</TD>
</TR>
<TR class="search_result">
  <TH class="search_result">Document Date:</TH>
  <TD colspan="2">%(mtime)s</TD>
</TR>
<TR class="search_result">
  <TH class="search_result">Comment:</TH>
  <TD colspan="2">%(memo)s</TD>
</TR>
</TABLE>
</DIV>
<P>""" % rec

import os, sys

# print page header
# document type definition is needed for proper rendering
# if omitted, table rendering will be incorrect
print """Content-type: text/html

<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0//EN"
   "http://www.w3.org/TR/REC-html40/strict.dtd">
<HTML>
<HEAD>
<TITLE>Appen library search results</TITLE>
<LINK rel="stylesheet" href="/appenlib/style.css">
</HEAD>
<BODY>
<H1><FONT color=blue>Appen Library Search Results</FONT></H1>
<HR>"""

# decode query condition
query_str = os.getenv("QUERY_STRING")
argu_dict = getArgumentDict(query_str)

# perform db query
import pg
try:
	db = pg.DB(dbname='appenlib', host='dbserver', user='staff')
	if 'keyword' in argu_dict:
		kw = " ".join(argu_dict['keyword'].split())
		kw = escape_str(kw)
		sql = "select * from search_by_keywords("\
			"string_to_array('%s', ' '))" % kw
	elif 'doc_id' in argu_dict:
		doc_id = argu_dict['doc_id']
		if doc_id[0] in ('D', 'd'): doc_id = doc_id[1:]
		sql = "select * from doc_list where doc_id=%s " \
			"order by version desc limit 1" % doc_id
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
	msg = "Sorry, no match found"
elif total == 1:
	msg = "There is 1 match to your search."
else:
	msg = "There are %d matches to your search." % total
print "<P><FONT size=4>%s</FONT>" % msg

# iterate result
for i in res:
	print formatRecord(i)

# print page footer
#print """<HR>
#<FONT size=2>Send comments to <A href="mailto:it@appen.com.au">it@appen.com.au</A>.</FONT>
#"""
print """</BODY>
</HTML>"""
# !"#$&%'()*+,-./09:;<=>?@AZ[\]^_`az{|}~
