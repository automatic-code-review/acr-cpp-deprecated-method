import os
import re

import automatic_code_review_commons as commons


def review(config):
    path_source = config['path_source']
    data_config = config['data']
    message = data_config['message']
    changes = config['merge']['changes']
    paths_deprecated_method = data_config['pathsDeprecatedMethod']

    comments = []
    deprecated_methods = []

    for path in paths_deprecated_method:
        deprecated_methods.extend(__find_deprecated_methods(path_source + path))

    for change in changes:
        if change['deleted_file']:
            continue

        comment_path = change['new_path']

        if not comment_path.endswith(('.h', '.cpp')):
            continue

        occurrences = __find_usages(path_source + "/" + comment_path, deprecated_methods)

        lines = []

        for occurrence in occurrences:
            lines.append(f"- Linha: `{occurrence['line']}`")
            lines.append(f"- Método: `{occurrence['method']}`")
            lines.append(f"- Código: `{occurrence['content']}`")
            lines.append("")

        comment_description = message
        comment_description = comment_description.replace("${FILE_PATH}", comment_path)
        comment_description = comment_description.replace("${OCCURRENCES}", "<br>".join(lines))

        comments.append(commons.comment_create(
            comment_id=commons.comment_generate_id(comment_description),
            comment_path=comment_path,
            comment_description=comment_description,
            comment_snipset=True,
            comment_end_line=1,
            comment_start_line=1,
            comment_language="c++",
        ))

    return comments


def __find_deprecated_methods(root_directory):
    deprecated_pattern = re.compile(
        r'\[\[deprecated\("([^"]+)"\)]]\s*(?:\n\s*)?([^\n;]+);'
    )

    results = []

    for root, _, files in os.walk(root_directory):
        for file_name in files:
            if file_name.endswith(('.h', '.cpp')):
                file_path = os.path.join(root, file_name)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()

                for match in deprecated_pattern.finditer(content):
                    message = match.group(1).strip()
                    signature = match.group(2).strip()
                    line = content[:match.start()].count('\n') + 1

                    results.append({
                        'file': file_path,
                        'line': line,
                        'message': message,
                        'signature': signature
                    })

    return results


def __extract_method_name(signature):
    match = re.search(r'\b(\w+)\s*\(', signature)
    return match.group(1) if match else None


def __group_occurrences_by_file(occurrences):
    result = {}

    for occurrence in occurrences:
        path = occurrence['file']

        if path in result:
            entries = result[path]
        else:
            entries = []

        entries.append(occurrence)
        result[path] = entries

    return result


def __find_usages(file_path, deprecated_methods):
    method_names = [__extract_method_name(m['signature']) for m in deprecated_methods if
                    __extract_method_name(m['signature'])]
    patterns = [re.compile(rf'[.-]>{name}\s*\(') for name in method_names] + \
               [re.compile(rf'\.{name}\s*\(') for name in method_names]

    occurrences = []

    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        for i, line in enumerate(f, 1):
            for name, pattern in zip(method_names, patterns):
                if pattern.search(line):
                    occurrences.append({
                        'file': file_path,
                        'line': i,
                        'method': name,
                        'content': line.strip()
                    })

    return occurrences
