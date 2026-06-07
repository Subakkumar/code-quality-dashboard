import os
import ast
from typing import Dict, List

class PythonAnalyzer:
    def __init__(self, code_path: str):
        self.code_path = code_path
        self.metrics = {
            'total_files':      0,
            'total_lines':      0,
            'total_functions':  0,
            'total_classes':    0,
            'long_functions':   [],
            'missing_docstrings': [],
            'files_analysis':   [],
            'syntax_errors':    []
        }
        self.issues = []

    def analyze(self) -> Dict:
        self._analyze_directory()
        self._identify_issues()
        return {
            'metrics': self.metrics,
            'issues':  self.issues,
            'score':   self.calculate_score()
        }

    def _analyze_directory(self):
        skip = {'venv','env','.git','__pycache__','node_modules',
                '.pytest_cache','dist','build','.eggs'}
        for root, dirs, files in os.walk(self.code_path):
            dirs[:] = [d for d in dirs if d not in skip]
            for file in files:
                if file.endswith('.py'):
                    self._analyze_file(os.path.join(root, file))

    def _analyze_file(self, filepath: str):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            lines = content.split('\n')
            self.metrics['total_lines']  += len(lines)
            self.metrics['total_files']  += 1

            tree = ast.parse(content)

            file_analysis = {
                'filepath':  filepath,
                'lines':     len(lines),
                'functions': 0,
                'classes':   0,
            }

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    self.metrics['total_functions'] += 1
                    file_analysis['functions']      += 1

                    func_lines = (node.end_lineno - node.lineno
                                  if hasattr(node, 'end_lineno') else 0)
                    if func_lines > 50:
                        self.metrics['long_functions'].append({
                            'file':     filepath,
                            'function': node.name,
                            'lines':    func_lines
                        })

                    if ast.get_docstring(node) is None:
                        self.metrics['missing_docstrings'].append({
                            'file':     filepath,
                            'function': node.name,
                            'line':     node.lineno
                        })

                elif isinstance(node, ast.ClassDef):
                    self.metrics['total_classes']    += 1
                    file_analysis['classes']         += 1

            self.metrics['files_analysis'].append(file_analysis)

        except SyntaxError as e:
            self.metrics['syntax_errors'].append({
                'file':    filepath,
                'message': str(e)
            })
        except Exception:
            pass

    def _identify_issues(self):
        # Long functions
        if self.metrics['long_functions']:
            self.issues.append({
                'type':        'long_functions',
                'severity':    'high',
                'count':       len(self.metrics['long_functions']),
                'description': f"{len(self.metrics['long_functions'])} functions exceed 50 lines — should be refactored",
                'examples':    self.metrics['long_functions'][:3]
            })

        # Missing docstrings
        if self.metrics['missing_docstrings']:
            count = len(self.metrics['missing_docstrings'])
            self.issues.append({
                'type':        'missing_docstrings',
                'severity':    'low',
                'count':       count,
                'description': f"{count} functions are missing docstrings",
                'examples':    self.metrics['missing_docstrings'][:5]
            })

        # Large files
        large_files = [f for f in self.metrics['files_analysis'] if f['lines'] > 300]
        if large_files:
            self.issues.append({
                'type':        'large_files',
                'severity':    'medium',
                'count':       len(large_files),
                'description': f"{len(large_files)} files exceed 300 lines — consider splitting",
                'files':       [f['filepath'] for f in large_files[:5]]
            })

        # Syntax errors
        if self.metrics['syntax_errors']:
            self.issues.append({
                'type':        'syntax_errors',
                'severity':    'critical',
                'count':       len(self.metrics['syntax_errors']),
                'description': f"{len(self.metrics['syntax_errors'])} files have syntax errors",
                'examples':    self.metrics['syntax_errors'][:3]
            })

        # No classes in large project
        if self.metrics['total_files'] > 5 and self.metrics['total_classes'] == 0:
            self.issues.append({
                'type':        'no_oop',
                'severity':    'low',
                'count':       0,
                'description': 'No classes found — consider OOP for better organisation'
            })

        # Empty project
        if self.metrics['total_files'] == 0:
            self.issues.append({
                'type':        'no_python_files',
                'severity':    'critical',
                'count':       0,
                'description': 'No Python files found in the uploaded project'
            })

    def calculate_score(self) -> float:
        score = 10.0

        # Long functions penalty
        if self.metrics['long_functions']:
            score -= min(len(self.metrics['long_functions']) * 0.3, 2.0)

        # Missing docstrings penalty
        if self.metrics['missing_docstrings']:
            score -= min(len(self.metrics['missing_docstrings']) * 0.05, 1.5)

        # Large files penalty
        large = [f for f in self.metrics['files_analysis'] if f['lines'] > 300]
        score -= len(large) * 0.4

        # Syntax errors — big penalty
        score -= len(self.metrics['syntax_errors']) * 1.5

        # Bonus: well-documented code
        if self.metrics['total_functions'] > 0:
            doc_ratio = 1 - (len(self.metrics['missing_docstrings'])
                             / self.metrics['total_functions'])
            if doc_ratio > 0.8:
                score += 0.5

        # Bonus: has classes (OOP)
        if self.metrics['total_classes'] > 0:
            score += 0.3

        return round(max(1.0, min(10.0, score)), 2)