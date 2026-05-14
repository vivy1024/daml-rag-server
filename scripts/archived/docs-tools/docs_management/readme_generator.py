"""
README生成器

负责生成和更新README索引文件
"""

from pathlib import Path
from typing import List, Dict
from dataclasses import dataclass
from datetime import datetime


@dataclass
class Document:
    """文档信息"""
    path: str
    title: str
    description: str = ""


class ReadmeGenerator:
    """README生成器"""
    
    def __init__(self, base_path: str):
        """
        初始化README生成器
        
        Args:
            base_path: 基础路径（如 daml-rag-server/docs）
        """
        self.base_path = Path(base_path)
        
    def generate_module_readme(
        self,
        module_name: str,
        module_description: str,
        documents: List[Document],
        sub_modules: List[str] = None
    ) -> str:
        """
        生成模块README内容
        
        Args:
            module_name: 模块名称
            module_description: 模块描述
            documents: 文档列表
            sub_modules: 子模块列表
            
        Returns:
            README内容
        """
        content = f"""# {module_name}

{module_description}

"""
        
        # 添加子模块部分
        if sub_modules:
            content += "## 子模块\n\n"
            for sub_module in sub_modules:
                content += f"- [{sub_module}](./{sub_module}/README.md)\n"
            content += "\n"
            
        # 添加文档列表
        if documents:
            content += "## 文档列表\n\n"
            for doc in documents:
                # 提取文件名
                doc_path = Path(doc.path)
                doc_name = doc_path.name
                
                if doc.description:
                    content += f"- [{doc.title}](./{doc_name}) - {doc.description}\n"
                else:
                    content += f"- [{doc.title}](./{doc_name})\n"
            content += "\n"
            
        # 添加相关链接
        content += """## 相关链接

- [返回上级目录](../README.md)

---

"""
        
        # 添加元数据
        today = datetime.now().strftime("%Y-%m-%d")
        content += f"""**维护者**: 薛小川  
**最后更新**: {today}
"""
        
        return content
        
    def generate_main_readme(
        self,
        title: str,
        description: str,
        structure: Dict[str, List[str]]
    ) -> str:
        """
        生成主README内容
        
        Args:
            title: 标题
            description: 描述
            structure: 目录结构 {目录名: [子目录列表]}
            
        Returns:
            README内容
        """
        content = f"""# {title}

{description}

## 📁 目录结构

```
docs/
"""
        
        # 生成目录树
        for main_dir, sub_dirs in structure.items():
            content += f"├─ {main_dir}/\n"
            for i, sub_dir in enumerate(sub_dirs):
                if i < len(sub_dirs) - 1:
                    content += f"│   ├─ {sub_dir}/\n"
                else:
                    content += f"│   └─ {sub_dir}/\n"
                    
        content += """```

## 🚀 快速导航

### 核心架构
- [系统架构](./02-核心架构/01-系统架构/README.md)
- [数据层](./02-核心架构/02-数据层/README.md)
- [编排层](./02-核心架构/03-编排层/README.md)

### 代码参考
- [工作流程步骤](./03-代码参考/01-工作流程步骤/README.md)
- [核心组件](./03-代码参考/02-核心组件/README.md)

### 开发指南
- [快速上手](./04-开发指南/01-快速上手/README.md)
- [工具使用](./04-开发指南/02-工具使用/README.md)

## 📚 文档分类说明

### 02-核心架构（What & Why）
回答"是什么"和"为什么"，侧重设计决策和架构理念。

### 03-代码参考（How - 实现）
回答"怎么实现"，侧重代码细节和算法。

### 04-开发指南（How - 使用）
回答"怎么使用"，侧重操作步骤和配置。

---

"""
        
        # 添加元数据
        today = datetime.now().strftime("%Y-%m-%d")
        content += f"""**维护者**: 薛小川  
**最后更新**: {today}
"""
        
        return content
        
    def update_readme_index(
        self,
        readme_path: str,
        documents: List[Document]
    ) -> None:
        """
        更新README中的文档索引
        
        Args:
            readme_path: README文件路径
            documents: 文档列表
        """
        readme_path = Path(readme_path)
        
        if not readme_path.exists():
            print(f"⚠️  README不存在: {readme_path}")
            return
            
        try:
            content = readme_path.read_text(encoding='utf-8')
        except Exception as e:
            print(f"❌ 读取README失败: {e}")
            return
            
        # 查找文档列表部分
        doc_list_start = content.find("## 文档列表")
        if doc_list_start == -1:
            print(f"⚠️  未找到文档列表部分: {readme_path}")
            return
            
        # 查找下一个##标题
        next_section = content.find("##", doc_list_start + 10)
        if next_section == -1:
            next_section = len(content)
            
        # 生成新的文档列表
        new_doc_list = "\n\n"
        for doc in documents:
            doc_path = Path(doc.path)
            doc_name = doc_path.name
            
            if doc.description:
                new_doc_list += f"- [{doc.title}](./{doc_name}) - {doc.description}\n"
            else:
                new_doc_list += f"- [{doc.title}](./{doc_name})\n"
                
        # 替换文档列表
        new_content = (
            content[:doc_list_start + len("## 文档列表")] +
            new_doc_list +
            content[next_section:]
        )
        
        # 写回文件
        try:
            readme_path.write_text(new_content, encoding='utf-8')
            print(f"✅ 更新README索引: {readme_path}")
        except Exception as e:
            print(f"❌ 写入README失败: {e}")
            
    def extract_documents_from_dir(self, directory: str) -> List[Document]:
        """
        从目录中提取文档信息
        
        Args:
            directory: 目录路径
            
        Returns:
            文档列表
        """
        dir_path = Path(directory)
        documents = []
        
        if not dir_path.exists():
            return documents
            
        # 扫描.md文件（排除README.md）
        for doc_path in sorted(dir_path.glob("*.md")):
            if doc_path.name == "README.md":
                continue
                
            # 尝试提取标题
            title = self._extract_title(doc_path)
            
            documents.append(Document(
                path=str(doc_path),
                title=title or doc_path.stem
            ))
            
        return documents
        
    def _extract_title(self, doc_path: Path) -> str:
        """
        从文档中提取标题
        
        Args:
            doc_path: 文档路径
            
        Returns:
            标题
        """
        try:
            with open(doc_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith('# '):
                        return line[2:].strip()
        except Exception:
            pass
            
        return doc_path.stem
        
    def create_readme_if_not_exists(
        self,
        readme_path: str,
        module_name: str,
        module_description: str
    ) -> None:
        """
        如果README不存在则创建
        
        Args:
            readme_path: README路径
            module_name: 模块名称
            module_description: 模块描述
        """
        readme_path = Path(readme_path)
        
        if readme_path.exists():
            print(f"⚠️  README已存在: {readme_path}")
            return
            
        # 提取目录中的文档
        documents = self.extract_documents_from_dir(readme_path.parent)
        
        # 生成README内容
        content = self.generate_module_readme(
            module_name,
            module_description,
            documents
        )
        
        # 写入文件
        try:
            readme_path.write_text(content, encoding='utf-8')
            print(f"✅ 创建README: {readme_path}")
        except Exception as e:
            print(f"❌ 创建README失败: {e}")
