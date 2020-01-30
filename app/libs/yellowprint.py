# 蓝图的衍生类，挂在蓝图下
class YellowPrint:
    # url拼接为"声明时url" + "注册时url" + "@route的url"
    def __init__(self, name, url_prefix=''):
        self.name = name
        self.mound = []
        self.url_prefix = url_prefix

    def route(self, rule, **options):
        def decorator(f):
            self.mound.append((f, rule, options))
            return f

        return decorator

    def register(self, bp, url_prefix=''):
        for f, rule, options in self.mound:
            endpoint = options.pop("endpoint", f.__name__)
            bp.add_url_rule(self.url_prefix + url_prefix + rule, endpoint, f, **options)
            return f
