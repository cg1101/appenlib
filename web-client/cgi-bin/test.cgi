#!/usr/bin/python

print """Content-type: image/png
"""
f = open("/var/www/appenlib/images/appen.png", "rb")
print f.read()
f.close()

