import ast
import os
from typing import List, Dict, Any


def analyze_python_file(file_path: str) -> Dict[str, Any]:
    """分析 Python 文件，提取结构信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    analysis = {
        'file_path': file_path,
        'functions': [],
        'classes': [],
        'imports': [],
        'docstring': ast.get_docstring(tree) or "",
        'total_lines': len(content.splitlines())
    }
    
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                analysis['imports'].append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                analysis['imports'].append(f"{module}.{alias.name}".strip('.'))
    
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef):
            func_info = {
                'name': node.name,
                'args': [arg.arg for arg in node.args.args],
                'docstring': ast.get_docstring(node) or "",
                'lineno': node.lineno,
                'returns': ast.unparse(node.returns) if node.returns else None,
                'is_async': isinstance(node, ast.AsyncFunctionDef)
            }
            analysis['functions'].append(func_info)
        elif isinstance(node, ast.ClassDef):
            class_info = {
                'name': node.name,
                'methods': [],
                'docstring': ast.get_docstring(node) or "",
                'lineno': node.lineno,
                'bases': [ast.unparse(base) for base in node.bases]
            }
            for subnode in node.body:
                if isinstance(subnode, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    class_info['methods'].append({
                        'name': subnode.name,
                        'args': [arg.arg for arg in subnode.args.args],
                        'docstring': ast.get_docstring(subnode) or "",
                        'lineno': subnode.lineno
                    })
            analysis['classes'].append(class_info)
    
    return analysis


def analyze_project(project_path: str) -> List[Dict[str, Any]]:
    """分析整个项目的所有 Python 文件"""
    results = []
    project_path = os.path.abspath(project_path)
    
    if not os.path.isdir(project_path):
        raise ValueError(f"路径 '{project_path}' 不是有效的目录")
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            if file.endswith('.py') and not file.startswith('_'):
                file_path = os.path.join(root, file)
                try:
                    analysis = analyze_python_file(file_path)
                    results.append(analysis)
                except Exception as e:
                    print(f"分析 {file_path} 时出错: {e}")
    
    return results


def generate_analysis_report(analysis_results: List[Dict[str, Any]]) -> str:
    """生成代码分析报告"""
    if not analysis_results:
        return "未找到任何 Python 文件"
    
    report = f"## 项目代码分析报告\n\n"
    report += f"### 📊 概览\n"
    report += f"- 文件数量: {len(analysis_results)} 个\n"
    
    total_lines = sum(r['total_lines'] for r in analysis_results)
    total_funcs = sum(len(r['functions']) for r in analysis_results)
    total_classes = sum(len(r['classes']) for r in analysis_results)
    
    report += f"- 代码行数: {total_lines} 行\n"
    report += f"- 函数数量: {total_funcs} 个\n"
    report += f"- 类数量: {total_classes} 个\n\n"
    
    for idx, file_info in enumerate(analysis_results, 1):
        rel_path = file_info['file_path']
        report += f"---\n\n"
        report += f"### 📄 {idx}. {rel_path}\n\n"
        
        if file_info['docstring']:
            report += f"**文档说明:** {file_info['docstring'][:150]}...\n\n"
        
        if file_info['classes']:
            report += f"**类定义 ({len(file_info['classes'])}):**\n"
            for cls in file_info['classes']:
                bases = f"({', '.join(cls['bases'])})" if cls['bases'] else ""
                report += f"- `class {cls['name']}{bases}` (行 {cls['lineno']})\n"
                if cls['methods']:
                    for method in cls['methods']:
                        args = ', '.join(method['args'])
                        report += f"  - `{method['name']}({args})` (行 {method['lineno']})\n"
        
        if file_info['functions']:
            report += f"\n**函数定义 ({len(file_info['functions'])}):**\n"
            for func in file_info['functions']:
                args = ', '.join(func['args'])
                returns = f" -> {func['returns']}" if func['returns'] else ""
                async_tag = "async " if func['is_async'] else ""
                report += f"- `{async_tag}def {func['name']}({args}){returns}` (行 {func['lineno']})\n"
    
    return report