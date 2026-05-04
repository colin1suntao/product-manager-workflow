"""Markdown 格式化器

将文档内容格式化为标准的 Markdown 文档。
"""

import re


class MarkdownFormatter:
    """Markdown 格式化器
    
    提供 Markdown 文档的格式化、校验和优化功能。
    """
    
    @staticmethod
    def format(document: str) -> str:
        """格式化 Markdown 文档
        
        Args:
            document: 原始 Markdown
            
        Returns:
            格式化后的 Markdown
        """
        # 清理多余的空行（最多保留两个连续空行）
        document = re.sub(r'\n{4,}', '\n\n\n', document)
        
        # 确保标题前后有空行
        document = re.sub(r'([^\n])\n(#{1,6}\s)', r'\1\n\n\2', document)
        document = re.sub(r'(#{1,6}\s[^\n]+)\n([^\n#])', r'\1\n\n\2', document)
        
        # 确保表格格式正确
        document = MarkdownFormatter._format_tables(document)
        
        # 清理行尾空格
        document = re.sub(r'  +\n', '\n', document)
        
        # 确保文件以换行结尾
        if document and not document.endswith('\n'):
            document += '\n'
        
        return document
    
    @staticmethod
    def _format_tables(document: str) -> str:
        """格式化表格"""
        lines = document.split('\n')
        result = []
        in_table = False
        table_lines = []
        
        for line in lines:
            if '|' in line and line.strip().startswith('|'):
                in_table = True
                table_lines.append(line.strip())
            else:
                if in_table and table_lines:
                    result.extend(MarkdownFormatter._align_table(table_lines))
                    table_lines = []
                    in_table = False
                result.append(line)
        
        # 处理末尾的表格
        if table_lines:
            result.extend(MarkdownFormatter._align_table(table_lines))
        
        return '\n'.join(result)
    
    @staticmethod
    def _align_table(lines: list[str]) -> list[str]:
        """对齐表格列"""
        if len(lines) < 2:
            return lines
        
        # 解析每列
        rows = []
        for line in lines:
            cells = [cell.strip() for cell in line.split('|')[1:-1]]
            rows.append(cells)
        
        if not rows:
            return lines
        
        # 计算每列最大宽度
        col_widths = []
        for row in rows:
            while len(col_widths) < len(row):
                col_widths.append(0)
            for i, cell in enumerate(row):
                col_widths[i] = max(col_widths[i], len(cell))
        
        # 重新构建表格
        result = []
        for i, row in enumerate(rows):
            cells = []
            for j, cell in enumerate(row):
                width = col_widths[j] if j < len(col_widths) else len(cell)
                cells.append(f" {cell.ljust(width)} ")
            result.append("|" + "|".join(cells) + "|")
        
        # 确保分隔行格式正确
        if len(result) > 1:
            separator_cells = []
            for width in col_widths:
                separator_cells.append(" " + "-" * width + " ")
            result[1] = "|" + "|".join(separator_cells) + "|"
        
        return result
    
    @staticmethod
    def validate(document: str) -> list[str]:
        """校验 Markdown 文档
        
        Args:
            document: Markdown 文档
            
        Returns:
            问题列表
        """
        issues = []
        lines = document.split('\n')
        
        # 检查标题层级跳跃
        heading_levels = []
        for line in lines:
            match = re.match(r'^(#{1,6})\s', line)
            if match:
                level = len(match.group(1))
                heading_levels.append(level)
        
        for i in range(1, len(heading_levels)):
            if heading_levels[i] > heading_levels[i-1] + 1:
                issues.append(
                    f"标题层级跳跃：第{i+1}个标题从H{heading_levels[i-1]}跳到H{heading_levels[i]}"
                )
        
        # 检查未闭合的粗体/斜体
        bold_count = len(re.findall(r'\*\*[^*]+\*\*', document))
        italic_count = len(re.findall(r'\*[^*]+\*', document))
        
        # 检查链接格式
        broken_links = re.findall(r'\[([^\]]+)\]\(([^\)]*)\)', document)
        for text, url in broken_links:
            if not url.strip():
                issues.append(f"空链接: [{text}]()")
        
        # 检查图片格式
        broken_images = re.findall(r'!\[([^\]]*)\]\(([^\)]*)\)', document)
        for alt, url in broken_images:
            if not url.strip():
                issues.append(f"空图片: ![{alt}]()")
        
        return issues
    
    @staticmethod
    def extract_headings(document: str) -> list[dict]:
        """提取文档标题结构
        
        Args:
            document: Markdown 文档
            
        Returns:
            标题列表，每个包含 level, text, line_number
        """
        headings = []
        lines = document.split('\n')
        
        for i, line in enumerate(lines, 1):
            match = re.match(r'^(#{1,6})\s+(.+)$', line)
            if match:
                level = len(match.group(1))
                text = match.group(2).strip()
                headings.append({
                    "level": level,
                    "text": text,
                    "line": i,
                })
        
        return headings
    
    @staticmethod
    def extract_toc(document: str, max_level: int = 3) -> str:
        """生成目录
        
        Args:
            document: Markdown 文档
            max_level: 最大标题级别
            
        Returns:
            Markdown 格式的目录
        """
        headings = MarkdownFormatter.extract_headings(document)
        
        toc_lines = []
        for heading in headings:
            if heading["level"] > max_level:
                continue
            
            indent = "  " * (heading["level"] - 1)
            anchor = heading["text"].lower().replace(" ", "-")
            anchor = re.sub(r'[^\w\-]', '', anchor)
            toc_lines.append(f"{indent}- [{heading['text']}](#{anchor})")
        
        return "\n".join(toc_lines)
