# -*- coding: utf-8 -*-
# python 3.8+bottle 0.13-dev
import os

from bottle import request, route, run


@route("/")
def form():
    return """<form action="/upload" method="post" enctype="multipart/form-data">
  Password:      <input type="password" name="password" />
  Select a file: <input type="file" name="upload" />
  <input type="submit" value="Start upload" />
</form>"""


@route("/upload", method="POST")
def do_upload():
    password = request.POST["password"]
    if password not in ["111", "222", "333"]:
        return "incorrect password!"
    upload = request.files.get("upload")
    name, ext = os.path.splitext(upload.filename)
    if ext not in [".py"]:
        return "File extension not allowed."
    os.remove("e://test.py")
    upload.save("e://test.py")

    import subprocess

    p = subprocess.Popen("c:/python27/python.exe e:/test.py", stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    return p.stdout.read() + p.stderr.read()


run(host="localhost", port=8080)
