"""PyInstaller 打包入口：以绝对导入调用 lezi.app.main。

`src/lezi/__main__.py` 用的是相对导入（`from .app import main`），只在
`python -m lezi` 下有效；打包时入口脚本会被当成顶层脚本执行，相对导入会
直接报错，因此单独提供本文件作为打包入口。
"""

import sys

from lezi.app import main

if __name__ == "__main__":
    sys.exit(main())