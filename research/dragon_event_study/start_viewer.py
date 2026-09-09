# -*- coding: utf-8 -*-
"""一键打开 6.5年动态回看表:本地起 http.server + 开浏览器。双击 打开6.5年回看表.bat 调用本脚本。"""
import http.server, socketserver, webbrowser, threading, os, urllib.parse, functools
HERE=os.path.dirname(os.path.abspath(__file__)); VIEWER=os.path.join(HERE,'viewer')
PORT=8799; FN='龙头候选池forward回看表_6.5年.html'
url='http://localhost:%d/%s'%(PORT,urllib.parse.quote(FN))
print('打开:',url,'\n(关闭本窗口即停止服务)')
threading.Timer(1.0,lambda:webbrowser.open(url)).start()
Handler=functools.partial(http.server.SimpleHTTPRequestHandler,directory=VIEWER)
socketserver.TCPServer.allow_reuse_address=True
with socketserver.TCPServer(('127.0.0.1',PORT),Handler) as h:
    try: h.serve_forever()
    except KeyboardInterrupt: pass
