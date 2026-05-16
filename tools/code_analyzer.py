import ast
import os
import re
from typing import List, Dict, Any


def is_test_file(file_path: str) -> bool:
    """判断文件是否为测试文件"""
    filename = os.path.basename(file_path).lower()
    dirname = os.path.dirname(file_path).lower()
    
    # 检查文件名模式
    if filename.startswith('test_') or filename.endswith('_test.py') or filename.endswith('_test.java') or filename.endswith('_test.go') or filename.endswith('_test.c'):
        return True
    
    # 检查目录路径
    if 'test' in dirname.split(os.sep) or 'tests' in dirname.split(os.sep):
        return True
    
    return False


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


def analyze_shell_file(file_path: str) -> Dict[str, Any]:
    """分析 Shell 脚本文件"""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()
    
    lines = content.splitlines()
    analysis = {
        'file_path': file_path,
        'language': 'Shell',
        'functions': [],
        'classes': [],
        'imports': [],
        'variables': [],
        'total_lines': len(lines)
    }
    
    # 提取函数定义
    func_pattern = re.compile(r'^\s*(\w+)\s*\(\s*\)')
    # 提取变量定义
    var_pattern = re.compile(r'^\s*(\w+)\s*=')
    # 提取 source/include 语句
    source_pattern = re.compile(r'^\s*(source|\.)\s+(\S+)')
    
    for i, line in enumerate(lines, 1):
        # 跳过注释和空行
        if line.strip().startswith('#') or line.strip() == '':
            continue
        
        # 提取函数
        match = func_pattern.match(line)
        if match:
            analysis['functions'].append({
                'name': match.group(1),
                'lineno': i
            })
        
        # 提取变量
        match = var_pattern.match(line)
        if match and '=' in line and not '==' in line:
            var_name = match.group(1)
            if var_name not in ['if', 'then', 'else', 'fi', 'for', 'do', 'done', 'while', 'case', 'esac']:
                analysis['variables'].append({
                    'name': var_name,
                    'lineno': i
                })
        
        # 提取 source/include
        match = source_pattern.match(line)
        if match:
            analysis['imports'].append(match.group(2))
    
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
                elif file.endswith('.sh') or file.startswith('.') and file != '.':
                    analysis = analyze_shell_file(file_path)
                    results.append(analysis)
            except Exception as e:
                print(f"分析 {file_path} 时出错: {e}")
    
    return results


def generate_analysis_report(analysis_results: List[Dict[str, Any]]) -> str:
    """生成代码分析报告（简化版）"""
    if not analysis_results:
        return "未找到任何支持的代码文件"
    
    # 统计语言分布和代码行数
    lang_stats = {}
    total_lines = 0
    for r in analysis_results:
        lang = r.get('language', 'Unknown')
        lang_stats[lang] = lang_stats.get(lang, 0) + 1
        total_lines += r.get('total_lines', 0)
    
    report = f"## 📊 代码分析统计\n\n"
    report += f"**文件数量:** {len(analysis_results)} 个\n"
    report += f"**代码行数:** {total_lines} 行\n\n"
    report += f"**🗂️ 语言分布:**\n"
    for lang, count in lang_stats.items():
        report += f"- {lang}: {count} 个文件\n"
    
    return report


def get_code_summary(analysis_results: List[Dict[str, Any]]) -> str:
    """生成代码详细摘要，供 AI 分析使用"""
    summary = []
    
    for r in analysis_results:
        file_info = f"文件: {os.path.basename(r['file_path'])} ({r.get('language', 'Unknown')})\n"
        
        # 类信息
        if r.get('classes'):
            file_info += f"  类: {', '.join(cls['name'] for cls in r['classes'])}\n"
        
        # 函数信息
        if r.get('functions'):
            func_names = [f["name"] for f in r['functions']]
            file_info += f"  函数: {', '.join(func_names[:10])}"
            if len(func_names) > 10:
                file_info += f" (+{len(func_names)-10} 个)"
            file_info += "\n"
        
        # Shell 变量信息
        if r.get('variables'):
            var_names = [v["name"] for v in r['variables']]
            file_info += f"  变量: {', '.join(var_names[:10])}"
            if len(var_names) > 10:
                file_info += f" (+{len(var_names)-10} 个)"
            file_info += "\n"
        
        summary.append(file_info)
    
    return "\n".join(summary)


def infer_project_purpose(analysis_results: List[Dict[str, Any]]) -> str:
    """根据代码内容推断项目用途"""
    keywords = {
        'web': ['flask', 'django', 'fastapi', 'http', 'server', 'api', 'route'],
        'cli': ['argparse', 'click', 'command', 'terminal', 'console'],
        'ai': ['llm', 'gpt', 'embedding', 'vector', 'rag', 'agent', 'prompt'],
        'database': ['sql', 'orm', 'db', 'mysql', 'postgres', 'sqlite'],
        'test': ['pytest', 'unittest', 'test_', '_test'],
        'game': ['pygame', 'game', 'render', 'sprite'],
        'data': ['pandas', 'numpy', 'dataframe', 'csv', 'json'],
        'bot': ['bot', 'robot', 'chat', 'messenger'],
    }
    
    purpose = "通用项目"
    scores = {k: 0 for k in keywords}
    
    for r in analysis_results:
        content = str(r)
        for category, terms in keywords.items():
            for term in terms:
                if term.lower() in content.lower():
                    scores[category] += 1
    
    max_score = max(scores.values())
    if max_score > 0:
        for category, score in scores.items():
            if score == max_score:
                purpose_map = {
                    'web': 'Web 应用/API 服务',
                    'cli': '命令行工具',
                    'ai': 'AI/机器学习项目',
                    'database': '数据库应用',
                    'test': '测试框架/工具',
                    'game': '游戏开发',
                    'data': '数据处理/分析',
                    'bot': '聊天机器人',
                }
                purpose = purpose_map.get(category, "通用项目")
                break
    
    return purpose
