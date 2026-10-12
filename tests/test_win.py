from lezi.platform.win import _rect_covers

SCREEN = (0, 0, 1920, 1080)


def test_rect_covers_equal_is_true():
    assert _rect_covers((0, 0, 1920, 1080), SCREEN) is True


def test_rect_covers_slightly_smaller_is_false():
    assert _rect_covers((0, 0, 1919, 1080), SCREEN) is False


def test_rect_covers_larger_is_true():
    assert _rect_covers((-10, -10, 1930, 1090), SCREEN) is True


def test_rect_covers_negative_and_slightly_smaller():
    # 任务栏占位：窗口略矮（底部留出任务栏）应判为非全屏
    assert _rect_covers((0, 0, 1920, 1040), (0, 0, 1920, 1080)) is False
    # 负坐标显示器：窗口刚好覆盖负坐标显示器应判为全屏
    assert _rect_covers((-1920, 0, 0, 1080), (-1920, 0, 0, 1080)) is True