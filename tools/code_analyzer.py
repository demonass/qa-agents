import ast
import os
import re
from typing import List, Dict, Any


def analyze_python_file(file_path: str) -> Dict[str, Any]:
    """分析 Python 文件，提取结构信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tree = ast.parse(content)
    
    analysis = {
        'file_path': file_path,
        'language': 'Python',
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


def analyze_java_file(file_path: str) -> Dict[str, Any]:
    """分析 Java 文件，提取结构信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.splitlines()
    analysis = {
        'file_path': file_path,
        'language': 'Java',
        'functions': [],
        'classes': [],
        'imports': [],
        'interfaces': [],
        'total_lines': len(lines)
    }
    
    import_pattern = re.compile(r'^\s*import\s+([\w.]+);')
    package_pattern = re.compile(r'^\s*package\s+([\w.]+);')
    
    for i, line in enumerate(lines, 1):
        match = import_pattern.match(line)
        if match:
            analysis['imports'].append(match.group(1))
        match = package_pattern.match(line)
        if match:
            analysis['package'] = match.group(1)
    
    class_pattern = re.compile(r'\b(class|interface)\s+(\w+)\s*(extends\s+\w+)?\s*(implements\s+[\w,]+)?')
    method_pattern = re.compile(r'\b(public|private|protected|static|final|\s)+\s*(\w+)\s+(\w+)\s*\(')
    
    for i, line in enumerate(lines, 1):
        match = class_pattern.search(line)
        if match:
            type_name = match.group(1)
            name = match.group(2)
            if type_name == 'interface':
                analysis['interfaces'].append({
                    'name': name,
                    'lineno': i
                })
            else:
                analysis['classes'].append({
                    'name': name,
                    'methods': [],
                    'lineno': i
                })
        
        match = method_pattern.search(line)
        if match and not line.strip().startswith('//') and '=' not in line.split('(')[0]:
            return_type = match.group(2)
            method_name = match.group(3)
            analysis['functions'].append({
                'name': method_name,
                'return_type': return_type,
                'lineno': i
            })
    
    return analysis


def analyze_go_file(file_path: str) -> Dict[str, Any]:
    """分析 Go 文件，提取结构信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.splitlines()
    analysis = {
        'file_path': file_path,
        'language': 'Go',
        'functions': [],
        'classes': [],
        'imports': [],
        'package': '',
        'total_lines': len(lines)
    }
    
    package_pattern = re.compile(r'^\s*package\s+(\w+)')
    for line in lines:
        match = package_pattern.match(line)
        if match:
            analysis['package'] = match.group(1)
            break
    
    in_import_block = False
    import_pattern = re.compile(r'\s*"([^"]+)"')
    
    for line in lines:
        if 'import (' in line:
            in_import_block = True
        elif ')' in line and in_import_block:
            in_import_block = False
        elif in_import_block:
            match = import_pattern.search(line)
            if match:
                analysis['imports'].append(match.group(1))
        elif line.startswith('import "'):
            match = import_pattern.search(line)
            if match:
                analysis['imports'].append(match.group(1))
    
    func_pattern = re.compile(r'^\s*func\s+(\([^)]+\))?\s*(\w+)\s*\(')
    
    for i, line in enumerate(lines, 1):
        match = func_pattern.match(line)
        if match:
            receiver = match.group(1) or ''
            func_name = match.group(2)
            analysis['functions'].append({
                'name': func_name,
                'receiver': receiver,
                'lineno': i
            })
    
    type_pattern = re.compile(r'^\s*type\s+(\w+)\s+(struct|interface)\s*\{')
    
    for i, line in enumerate(lines, 1):
        match = type_pattern.match(line)
        if match:
            name = match.group(1)
            type_kind = match.group(2)
            analysis['classes'].append({
                'name': name,
                'type': type_kind,
                'lineno': i
            })
    
    return analysis


def analyze_c_file(file_path: str) -> Dict[str, Any]:
    """分析 C 文件，提取结构信息"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.splitlines()
    analysis = {
        'file_path': file_path,
        'language': 'C',
        'functions': [],
        'classes': [],
        'imports': [],
        'macros': [],
        'total_lines': len(lines)
    }
    
    include_pattern = re.compile(r'^\s*#include\s+[<"]([^>"]+)[>"]')
    
    for i, line in enumerate(lines, 1):
        match = include_pattern.match(line)
        if match:
            analysis['imports'].append(match.group(1))
    
    macro_pattern = re.compile(r'^\s*#define\s+(\w+)')
    
    for i, line in enumerate(lines, 1):
        match = macro_pattern.match(line)
        if match:
            analysis['macros'].append({
                'name': match.group(1),
                'lineno': i
            })
    
    func_pattern = re.compile(r'^\s*(\w+\s+)+(\w+)\s*\(')
    
    for i, line in enumerate(lines, 1):
        if line.strip().startswith('//') or '/*' in line:
            continue
        match = func_pattern.match(line)
        if match and ';' not in line:
            func_name = match.group(2)
            if func_name not in ['if', 'for', 'while', 'switch', 'return', 'sizeof']:
                analysis['functions'].append({
                    'name': func_name,
                    'lineno': i
                })
    
    struct_pattern = re.compile(r'^\s*struct\s+(\w+)\s*\{')
    
    for i, line in enumerate(lines, 1):
        match = struct_pattern.match(line)
        if match:
            analysis['classes'].append({
                'name': match.group(1),
                'type': 'struct',
                'lineno': i
            })
    
    return analysis


def analyze_project(project_path: str) -> List[Dict[str, Any]]:
    """分析整个项目的所有支持的文件"""
    results = []
    project_path = os.path.abspath(project_path)
    
    if not os.path.isdir(project_path):
        raise ValueError(f"路径 '{project_path}' 不是有效的目录")
    
    for root, dirs, files in os.walk(project_path):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '__pycache__']
        
        for file in files:
            file_path = os.path.join(root, file)
            
            try:
                if file.endswith('.py') and not file.startswith('_'):
                    analysis = analyze_python_file(file_path)
                    results.append(analysis)
                elif file.endswith('.java'):
                    analysis = analyze_java_file(file_path)
                    results.append(analysis)
                elif file.endswith('.go'):
                    analysis = analyze_go_file(file_path)
                    results.append(analysis)
                elif file.endswith('.c'):
                    analysis = analyze_c_file(file_path)
                    results.append(analysis)
            except Exception as e:
                print(f"分析 {file_path} 时出错: {e}")
    
    return results


def generate_analysis_report(analysis_results: List[Dict[str, Any]]) -> str:
    """生成代码分析报告"""
    if not analysis_results:
        return "未找到任何支持的代码文件"
    
    report = f"## 项目代码分析报告\n\n"
    report += f"### 📊 概览\n"
    report += f"- 文件数量: {len(analysis_results)} 个\n"
    
    lang_stats = {}
    total_lines = 0
    total_funcs = 0
    total_classes = 0
    
    for r in analysis_results:
        lang = r.get('language', 'Unknown')
        lang_stats[lang] = lang_stats.get(lang, 0) + 1
        total_lines += r.get('total_lines', 0)
        total_funcs += len(r.get('functions', []))
        total_classes += len(r.get('classes', []))
    
    report += f"- 代码行数: {total_lines} 行\n"
    report += f"- 函数数量: {total_funcs} 个\n"
    report += f"- 类/结构体数量: {total_classes} 个\n\n"
    
    report += f"### 🗂️ 语言分布\n"
    for lang, count in lang_stats.items():
        report += f"- {lang}: {count} 个文件\n"
    report += "\n"
    
    for idx, file_info in enumerate(analysis_results, 1):
        rel_path = file_info['file_path']
        lang = file_info.get('language', '')
        report += f"---\n\n"
        report += f"### 📄 {idx}. {rel_path} ({lang})\n\n"
        
        if file_info.get('docstring'):
            report += f"**文档说明:** {file_info['docstring'][:150]}...\n\n"
        
        if file_info.get('interfaces'):
            report += f"**接口定义 ({len(file_info['interfaces'])}):**\n"
            for iface in file_info['interfaces']:
                report += f"- `interface {iface['name']}` (行 {iface['lineno']})\n"
        
        if file_info['classes']:
            report += f"\n**类/结构体定义 ({len(file_info['classes'])}):**\n"
            for cls in file_info['classes']:
                cls_type = cls.get('type', '')
                type_tag = f" ({cls_type})" if cls_type else ""
                bases = f"({', '.join(cls.get('bases', []))})" if cls.get('bases') else ""
                report += f"- `{cls['name']}{bases}`{type_tag} (行 {cls['lineno']})\n"
                if cls.get('methods'):
                    for method in cls['methods']:
                        args = ', '.join(method['args'])
                        report += f"  - `{method['name']}({args})` (行 {method['lineno']})\n"
        
        if file_info['functions']:
            report += f"\n**函数定义 ({len(file_info['functions'])}):**\n"
            for func in file_info['functions']:
                args = ', '.join(func.get('args', [])) if func.get('args') else ''
                returns = f" -> {func['returns']}" if func.get('returns') else ''
                receiver = func.get('receiver', '')
                if receiver:
                    report += f"- `func {receiver} {func['name']}({args}){returns}` (行 {func['lineno']})\n"
                else:
                    report += f"- `{func['name']}({args}){returns}` (行 {func['lineno']})\n"
        
        if file_info.get('macros'):
            report += f"\n**宏定义 ({len(file_info['macros'])}):**\n"
            for macro in file_info['macros']:
                report += f"- `#define {macro['name']}` (行 {macro['lineno']})\n"
    
    return report
