#!/usr/bin/env python3
"""
字幕文本口语噪声清洗脚本

清洗 Bilibili 健身字幕 Markdown 文件中的口语填充词、冗余表达，
提升 Qdrant 向量嵌入质量和 BM25 检索精度。

用法:
    python clean_subtitle_text.py                          # 清洗全部文件(原地覆盖)
    python clean_subtitle_text.py --dry-run                # 仅预览，不写入
    python clean_subtitle_text.py --output-dir ./cleaned   # 输出到指定目录
    python clean_subtitle_text.py --file BV1xxx.md         # 只处理单个文件
"""

import argparse
import os
import re
import sys
from collections import Counter
from pathlib import Path

# ============================================================
# 清洗规则定义（优先级从高到低）
# ============================================================

# --- P0: 语气填充词（独立出现或句中插入） ---
# 匹配独立的填充词，注意不破坏"呃…"这种省略号表达
FILLER_PATTERNS = [
    # 独立填充词（前后为标点、空格或行首行尾）
    (re.compile(r'(?<=[，。！？、；：\s])呃(?=[，。！？、；：\s]|$)'), '', '呃'),
    (re.compile(r'(?<=[，。！？、；：\s])嗯(?=[，。！？、；：\s]|$)'), '', '嗯'),
    (re.compile(r'(?<=[，。！？、；：\s])哦(?=[，。！？、；：\s]|$)'), '', '哦'),
    (re.compile(r'(?<=[，。！？、；：\s])噢(?=[，。！？、；：\s]|$)'), '', '噢'),
    (re.compile(r'(?<=[，。！？、；：\s])唉(?=[，。！？、；：\s]|$)'), '', '唉'),
    # 句首填充词
    (re.compile(r'^呃\s*'), '', '呃(句首)'),
    (re.compile(r'^嗯\s*'), '', '嗯(句首)'),
    # 句中嵌入的填充词（前后紧跟汉字）
    (re.compile(r'(?<=[\u4e00-\u9fff])呃(?=[\u4e00-\u9fff])'), '', '呃(句中)'),
    (re.compile(r'(?<=[\u4e00-\u9fff])嗯(?=[\u4e00-\u9fff])'), '', '嗯(句中)'),
]

# --- P1: 重复语气词 ---
REPEATED_PARTICLE_PATTERNS = [
    (re.compile(r'啊啊+'), '啊', '啊啊+'),
    (re.compile(r'嗯嗯+'), '嗯', '嗯嗯+'),
    (re.compile(r'哈哈哈+'), '哈哈', '哈哈哈+'),
    (re.compile(r'对对对+'), '对', '对对对+'),
    (re.compile(r'好好好+'), '好', '好好好+'),
    (re.compile(r'是是是+'), '是', '是是是+'),
    (re.compile(r'呢呢+'), '呢', '呢呢+'),
]

# --- P2: 口语连接词/开场白 ---
# 注意：字幕文本以空格分隔短语，几乎无中文标点，边界条件必须包含 \s
ORAL_CONNECTOR_PATTERNS = [
    # "然后呢" 在空格/标点后 → 删除
    (re.compile(r'(?<=[，。\s])\s*然后呢\s*'), '', '然后呢'),
    # "然后呢" 在行首 → 删除
    (re.compile(r'^然后呢\s*'), '', '然后呢'),
    # "所以说呢" → "所以"
    (re.compile(r'所以说呢'), '所以', '所以说呢'),
    # "所以说" (不带呢) → "所以"（空格/标点后或行首）
    (re.compile(r'(?<=[\s，。])所以说(?=[\u4e00-\u9fff\s])'), '所以', '所以说'),
    (re.compile(r'^所以说(?=[\u4e00-\u9fff\s])'), '所以', '所以说'),
    # "那么呢" → 删除
    (re.compile(r'那么呢\s*'), '', '那么呢'),
    # "就是说呢" → 删除
    (re.compile(r'就是说呢\s*'), '', '就是说呢'),
    # "也就是说呢" → "即"
    (re.compile(r'也就是说呢'), '即', '也就是说呢'),
    # 口语开场白
    (re.compile(r'好我们(?=[\u4e00-\u9fff])'), '我们', '好我们'),
    (re.compile(r'好那么(?=[\u4e00-\u9fff])'), '那么', '好那么'),
    (re.compile(r'好接下来(?=[\u4e00-\u9fff])'), '接下来', '好接下来'),
    (re.compile(r'好往下看'), '往下看', '好往下看'),
    # "OK吧" → 删除（口语确认语气）
    (re.compile(r'OK吧\s*', re.IGNORECASE), '', 'OK吧'),
    # "OK" 作为口语过渡（空格/标点边界）
    (re.compile(r'(?<=[，。！？\s])OK\s*(?=[，。\s]|$)', re.IGNORECASE), '', 'OK(过渡)'),
]

# --- P3: 冗余表达 ---
REDUNDANT_PATTERNS = [
    # "我们说" / "我们看" / "大家看" 作为口语引导 → 删除（空格/标点后）
    (re.compile(r'(?<=[，。\s])\s*我们说\s*'), ' ', '我们说'),
    (re.compile(r'(?<=[，。\s])\s*我们看\s*'), ' ', '我们看'),
    (re.compile(r'(?<=[，。\s])\s*大家看\s*'), ' ', '大家看'),
    # "就是说" → "即"（汉字或空格边界）
    (re.compile(r'(?<=[\u4e00-\u9fff\s])就是说(?=[\u4e00-\u9fff\s])'), '即', '就是说'),
    # "也就是说" → "即"
    (re.compile(r'也就是说'), '即', '也就是说'),
    # "是不是啊" → 删除（先匹配带啊的，避免被下面的规则拆开）
    (re.compile(r'是不是啊'), '', '是不是啊'),
    # "是不是" 独立口语确认（空格/标点边界） → 删除
    (re.compile(r'(?<=[\u4e00-\u9fff])是不是(?=[\s，。]|$)'), '', '是不是'),
    # "是吧" 口语确认 → 删除
    (re.compile(r'是吧(?=[\s，。]|$)'), '', '是吧'),
    # "对不对" / "对吧" → 删除
    (re.compile(r'对不对'), '', '对不对'),
    (re.compile(r'对吧(?=[\s，。]|$)'), '', '对吧'),
    # "等等等等" → "等"
    (re.compile(r'等等等等+'), '等', '等等等等'),
    # "说白了" → 删除
    (re.compile(r'说白了\s*'), '', '说白了'),
    # "其实呢" → "其实"
    (re.compile(r'其实呢'), '其实', '其实呢'),
    # "那么" 在句首作为纯过渡（保守：只处理"那么"后紧跟"呢"的情况已在上面处理）
]

# --- P4: 句尾多余语气词（保守处理） ---
TRAILING_PARTICLE_PATTERNS = [
    # 句尾 "啊" 在逗号/句号/空格前（但保留"吗"等有语法功能的）
    (re.compile(r'啊(?=[，。\s]|$)'), '', '啊(句尾)'),
    # 句尾 "哈" 在逗号/句号/空格前
    (re.compile(r'哈(?=[，。\s]|$)'), '', '哈(句尾)'),
    # 句尾 "呀" 在空格/标点前（口语变体的"啊"）
    (re.compile(r'呀(?=[，。\s]|$)'), '', '呀(句尾)'),
    # 句尾 "呢" 在空格前（保守：仅匹配 "X的话呢" / "X东西呢" / "X时候呢" 等口语模式）
    (re.compile(r'(?<=的话)呢(?=[\s]|$)'), '', '呢(的话呢)'),
    (re.compile(r'(?<=时候)呢(?=[\s]|$)'), '', '呢(时候呢)'),
    (re.compile(r'(?<=东西)呢(?=[\s]|$)'), '', '呢(东西呢)'),
    (re.compile(r'(?<=地方)呢(?=[\s]|$)'), '', '呢(地方呢)'),
    (re.compile(r'(?<=问题)呢(?=[\s]|$)'), '', '呢(问题呢)'),
    (re.compile(r'(?<=方面)呢(?=[\s]|$)'), '', '呢(方面呢)'),
    (re.compile(r'(?<=部分)呢(?=[\s]|$)'), '', '呢(部分呢)'),
    (re.compile(r'(?<=情况)呢(?=[\s]|$)'), '', '呢(情况呢)'),
]

# --- P5: 空白规范化 ---
WHITESPACE_PATTERNS = [
    # 多个连续空格 → 单空格
    (re.compile(r'  +'), ' ', '多余空格'),
    # 连续标点修复：多个逗号 → 单逗号
    (re.compile(r'，，+'), '，', '重复逗号'),
    # 空格+逗号 → 逗号
    (re.compile(r'\s+，'), '，', '空格+逗号'),
    # 逗号+空格+逗号 → 逗号
    (re.compile(r'，\s*，'), '，', '逗号间空白'),
]

# 所有规则按优先级排列
ALL_RULE_GROUPS = [
    ('P0-填充词', FILLER_PATTERNS),
    ('P1-重复语气', REPEATED_PARTICLE_PATTERNS),
    ('P2-口语连接', ORAL_CONNECTOR_PATTERNS),
    ('P3-冗余表达', REDUNDANT_PATTERNS),
    ('P4-句尾语气', TRAILING_PARTICLE_PATTERNS),
    ('P5-空白规范', WHITESPACE_PATTERNS),
]


# ============================================================
# 核心清洗逻辑
# ============================================================

def parse_markdown(text: str) -> tuple[str, list[dict]]:
    """
    解析 Markdown 文件，分离 frontmatter、段落标记和正文。
    返回 (frontmatter, sections) 其中 sections 是 [{type, content}] 列表。
    type: 'frontmatter' | 'heading' | 'paragraph_marker' | 'body'
    """
    sections = []
    lines = text.split('\n')
    i = 0

    # 解析 YAML frontmatter
    frontmatter = ''
    if lines and lines[0].strip() == '---':
        end_idx = -1
        for j in range(1, len(lines)):
            if lines[j].strip() == '---':
                end_idx = j
                break
        if end_idx > 0:
            frontmatter = '\n'.join(lines[:end_idx + 1])
            i = end_idx + 1

    # 解析剩余内容
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # 空行
        if not stripped:
            sections.append({'type': 'empty', 'content': ''})
            i += 1
            continue

        # 一级标题（文档标题）
        if stripped.startswith('# ') and not stripped.startswith('## '):
            sections.append({'type': 'heading', 'content': line})
            i += 1
            continue

        # 段落标记 ## 段落N (timestamp)
        if re.match(r'^##\s+段落\d+', stripped):
            sections.append({'type': 'paragraph_marker', 'content': line})
            i += 1
            continue

        # 正文行
        sections.append({'type': 'body', 'content': line})
        i += 1

    return frontmatter, sections


def clean_text(text: str, stats: Counter) -> str:
    """对一段正文文本应用所有清洗规则，统计每条规则的命中次数。"""
    result = text
    for group_name, patterns in ALL_RULE_GROUPS:
        for pattern, replacement, label in patterns:
            matches = pattern.findall(result)
            if matches:
                stats[label] += len(matches)
                result = pattern.sub(replacement, result)
    return result


def clean_file(filepath: Path) -> tuple[str, dict]:
    """
    清洗单个文件，返回 (cleaned_text, file_stats)。
    file_stats 包含 original_len, cleaned_len, compression_ratio, rule_hits。
    """
    raw = filepath.read_text(encoding='utf-8')
    original_len = len(raw)

    frontmatter, sections = parse_markdown(raw)
    stats = Counter()

    # 只清洗 body 类型的 section
    cleaned_sections = []
    for sec in sections:
        if sec['type'] == 'body':
            cleaned = clean_text(sec['content'], stats)
            # 清洗后如果只剩空白/标点，跳过该行
            if cleaned.strip() and not re.match(r'^[，。！？、；：\s]+$', cleaned.strip()):
                cleaned_sections.append({'type': 'body', 'content': cleaned})
        else:
            cleaned_sections.append(sec)

    # 重组文件
    parts = []
    if frontmatter:
        parts.append(frontmatter)

    for sec in cleaned_sections:
        parts.append(sec['content'])

    cleaned_text = '\n'.join(parts)
    # 确保文件以换行符结尾
    if not cleaned_text.endswith('\n'):
        cleaned_text += '\n'

    cleaned_len = len(cleaned_text)
    compression = (1 - cleaned_len / original_len) * 100 if original_len > 0 else 0

    file_stats = {
        'original_len': original_len,
        'cleaned_len': cleaned_len,
        'compression_ratio': compression,
        'rule_hits': dict(stats),
    }

    return cleaned_text, file_stats


# ============================================================
# CLI 入口
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description='清洗 Bilibili 健身字幕 Markdown 文件中的口语噪声'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='仅预览清洗结果，不写入文件',
    )
    parser.add_argument(
        '--output-dir',
        type=str,
        default=None,
        help='输出目录（默认原地覆盖）',
    )
    parser.add_argument(
        '--file',
        type=str,
        default=None,
        help='只处理指定文件（文件名或完整路径）',
    )
    args = parser.parse_args()

    # 确定输入目录
    script_dir = Path(__file__).resolve().parent
    input_dir = script_dir / 'data' / 'knowledge_texts'

    if not input_dir.exists():
        print(f'[错误] 输入目录不存在: {input_dir}')
        sys.exit(1)

    # 收集待处理文件
    if args.file:
        target = Path(args.file)
        if not target.is_absolute():
            target = input_dir / target
        if not target.exists():
            print(f'[错误] 文件不存在: {target}')
            sys.exit(1)
        files = [target]
    else:
        files = sorted([
            f for f in input_dir.glob('*.md')
            if f.name != 'README.md'
        ])

    if not files:
        print('[警告] 没有找到待处理的 .md 文件')
        sys.exit(0)

    # 输出目录
    output_dir = None
    if args.output_dir:
        output_dir = Path(args.output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

    # 处理文件
    total_stats = Counter()
    all_file_stats = []
    total_original = 0
    total_cleaned = 0

    print(f'{"=" * 60}')
    print(f'字幕口语噪声清洗 {"[DRY-RUN 模式]" if args.dry_run else ""}')
    print(f'输入目录: {input_dir}')
    print(f'文件数量: {len(files)}')
    print(f'输出方式: {"预览(不写入)" if args.dry_run else (str(output_dir) if output_dir else "原地覆盖")}')
    print(f'{"=" * 60}\n')

    for filepath in files:
        cleaned_text, file_stats = clean_file(filepath)

        total_original += file_stats['original_len']
        total_cleaned += file_stats['cleaned_len']
        for label, count in file_stats['rule_hits'].items():
            total_stats[label] += count

        all_file_stats.append((filepath.name, file_stats))

        # 写入
        if not args.dry_run:
            out_path = (output_dir / filepath.name) if output_dir else filepath
            out_path.write_text(cleaned_text, encoding='utf-8')

        # 单文件摘要
        hits = sum(file_stats['rule_hits'].values())
        if hits > 0:
            print(f'  {filepath.name}: {file_stats["compression_ratio"]:.1f}% 压缩, {hits} 处清洗')

    # ---- 汇总报告 ----
    print(f'\n{"=" * 60}')
    print('清洗报告汇总')
    print(f'{"=" * 60}')

    total_compression = (1 - total_cleaned / total_original) * 100 if total_original > 0 else 0
    print(f'文件总数: {len(files)}')
    print(f'原始总字符: {total_original:,}')
    print(f'清洗后字符: {total_cleaned:,}')
    print(f'总压缩率:   {total_compression:.2f}%')
    print(f'总清洗次数: {sum(total_stats.values()):,}')

    # Top-10 命中规则
    print(f'\nTop-10 命中规则:')
    print(f'{"-" * 40}')
    for label, count in total_stats.most_common(10):
        print(f'  {label:<20s} {count:>6,} 次')

    # 压缩率最高的5个文件
    sorted_files = sorted(all_file_stats, key=lambda x: x[1]['compression_ratio'], reverse=True)
    print(f'\n压缩率最高的文件 (Top-5):')
    print(f'{"-" * 40}')
    for name, fs in sorted_files[:5]:
        print(f'  {name}: {fs["compression_ratio"]:.1f}%')

    print(f'\n{"=" * 60}')
    if args.dry_run:
        print('DRY-RUN 完成，未写入任何文件。')
    else:
        dest = str(output_dir) if output_dir else '原地覆盖'
        print(f'清洗完成，输出: {dest}')


if __name__ == '__main__':
    main()
