# -*- coding: utf-8 -*-
"""
JSON序列化补丁 - 修复datetime对象序列化问题
"""

import json
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    """自定义JSON编码器，处理datetime对象"""

    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def safe_json_dumps(obj, ensure_ascii=False):
    """安全的JSON序列化函数"""
    return json.dumps(obj, ensure_ascii=ensure_ascii, cls=DateTimeEncoder)