def with_metaclass(meta, *bases):
    """
    通过源类创造一个基类
    :param meta: 需要传入的元类
    :param bases: 一些参数
    :return: 通过元类返回一个临时的基类，用作类声明时的模板
    """

    class MetaClass(meta):

        def __new__(cls, name, this_bases, d):
            return meta(name, bases, d)

    return type.__new__(MetaClass, str('temporary_class'), (), {})
