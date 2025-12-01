import os
from pathlib import Path

def count_lines_in_file(filepath):
    """Cuenta líneas en un archivo."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return len(f.readlines())
    except:
        return 0

def count_project_lines(root_dir, extensions=['.py'], exclude_dirs=['__pycache__', '.git', 'venv', 'env', 'test_data']):
    """Cuenta líneas de código en el proyecto."""
    total_lines = 0
    total_files = 0
    file_details = []
    
    for root, dirs, files in os.walk(root_dir):
        # Excluir directorios
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        
        for file in files:
            if any(file.endswith(ext) for ext in extensions):
                filepath = os.path.join(root, file)
                lines = count_lines_in_file(filepath)
                total_lines += lines
                total_files += 1
                file_details.append((filepath, lines))
    
    return total_lines, total_files, file_details

# Ejecutar
root = '.'  # Directorio actual
total, files, details = count_project_lines(root, extensions=['.py'])

print(f"\n{'='*60}")
print(f"COREF SUITE - Estadísticas de Código")
print(f"{'='*60}")
print(f"Total de archivos Python: {files}")
print(f"Total de líneas de código: {total:,}")
print(f"Promedio por archivo: {total//files if files > 0 else 0:,} líneas")
print(f"{'='*60}\n")

# Ordenar por líneas (descendente)
details.sort(key=lambda x: x[1], reverse=True)

print("Top 15 archivos más grandes:")
for i, (path, lines) in enumerate(details[:15], 1):
    print(f"{i:2}. {lines:5,} líneas - {path}")

# Por directorio
from collections import defaultdict
by_dir = defaultdict(int)
by_dir_files = defaultdict(int)

for path, lines in details:
    parts = path.split(os.sep)
    if len(parts) > 1:
        dir_name = parts[0] if parts[0] != '.' else parts[1] if len(parts) > 1 else 'root'
    else:
        dir_name = 'root'
    by_dir[dir_name] += lines
    by_dir_files[dir_name] += 1

print(f"\n{'='*60}")
print("Líneas por directorio:")
print(f"{'Directorio':<20} {'Archivos':>8} {'Líneas':>10}")
print(f"{'-'*20} {'-'*8} {'-'*10}")
for dir_name, lines in sorted(by_dir.items(), key=lambda x: x[1], reverse=True):
    num_files = by_dir_files[dir_name]
    print(f"{dir_name:<20} {num_files:>8} {lines:>10,}")

print(f"\n{'='*60}")
print(f"Directorios excluidos: __pycache__, .git, venv, env, test_data")
print(f"{'='*60}\n")