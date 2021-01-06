# 蓝图的衍生类，挂在蓝图下
class YellowPrint:
    # url拼接为"声明时url" + "注册时url" + "@route的url"
    def __init__(self, name, url_prefix=''):
        self.name = name
        self.mound = []
        self.url_prefix = url_prefix

    def route(self, rule, **options):
        def decorator(f):
            endpoint = options.pop("endpoint", f.__name__)
            self.mound.append((f, rule, endpoint, options))
            return f

        return decorator

    def register(self, bp, url_prefix=''):
        for f, rule, endpoint, options in self.mound:
            endpoint = options.pop("endpoint", f.__name__)
            rule = self.url_prefix + url_prefix + rule
            bp.add_url_rule(rule, endpoint, f, **options)
        return f
