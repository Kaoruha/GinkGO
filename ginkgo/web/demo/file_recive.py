import tornado.web
import tornado.ioloop


class UploadHandler(tornado.web.RequestHandler):
    def get(self, *args, **kwargs):
        pass

    def post(self, *args, **kwargs):
        # 获取前端上传的file，名称为img1
        img1 = self.request.files['img1']
        print(img1)

        for i in img1:
            body = i.get('body', '')
            content_type = i.get('content_type', '')
            filename = i.get('filename', '')

        # 将图片存储
        import os
        dir = os.path.join(os.getcwd(), 'files', filename)

        with open(dir, 'wr') as fw:
            fw.write(body)

        # 将图片显示在网页中
        # 设置响应头
        self.set_header('Content-Type',content_type)
        self.write(body)


app = tornado.web.Application([(r'/upload', UploadHandler)])

app.listen(8080)

app.ioloop.IOLoop.current().start()