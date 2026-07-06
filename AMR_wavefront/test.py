from core.application import Application


class Test(Application):

    def initialize(self):
        print("Đang khởi tạo chương trình...")

    def update(self):
        pass


Test().run()
