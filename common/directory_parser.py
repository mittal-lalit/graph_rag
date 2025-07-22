import os
import json
import re
import pandas as pd
import shutil

class DirectoryParser:
    def __init__(self, root_path='test_cases', output_path='temp_data'):
        self.root_path = root_path
        self.output_path = output_path
        self.reset_output_dir()

    def reset_output_dir(self):
        if os.path.exists(self.output_path):
            shutil.rmtree(self.output_path)
        os.makedirs(self.output_path)

    @staticmethod
    def clean_text(text, indent_width=4):
        text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
        text = re.sub(r'\[.*?\]\(.*?\)', '', text)
        lines = text.splitlines()
        new_lines = []

        for line in lines:
            line = line.rstrip()
            heading_match = re.match(r'^(#{1,6})\s+(.*)', line)
            if heading_match:
                hashes, content = heading_match.groups()
                level = len(hashes)
                new_lines.append(f"H{level}: {content.strip()}")
                continue

            list_match = re.match(r'^(\s*)-\s+(.*)', line)
            if list_match:
                spaces, content = list_match.groups()
                level = len(spaces) // indent_width + 1
                new_lines.append(f"L{level}: {content.strip()}")
                continue

            cleaned_line = re.sub(r'[>*]', '', line).strip()
            if cleaned_line:
                new_lines.append(cleaned_line)

        return '\n'.join(new_lines)

    def parse(self):
        for directory_path, sub_directories, file_names in os.walk(self.root_path):
            self.process_directory(directory_path, sub_directories, file_names)

    def process_directory(self, directory_path, sub_directories, file_names):
        children = []

        for sub_dir in sub_directories:
            if sub_dir.startswith('.'):
                continue
            entry_path = os.path.join(directory_path, sub_dir)
            children.append({
                "name": sub_dir,
                "type": "directory",
                "path": os.path.relpath(entry_path, self.root_path).replace('\\', '/')
            })

        for file in file_names:
            if file.startswith('.'):
                continue

            entry_path = os.path.join(directory_path, file)
            name = os.path.splitext(file)[0]
            rel_path = os.path.relpath(entry_path, self.root_path).replace('\\', '/')

            if file.endswith('.md'):
                children.append({
                    "name": name,
                    "type": "file",
                    "path": rel_path
                })
                self.process_markdown_file(entry_path)

            elif file.endswith('.xlsx') or file.endswith('.xls'):
                self.process_excel_file(entry_path)

        if children:
            dir_json = {
                "name": os.path.basename(directory_path),
                "type": "directory",
                "content": "",
                "children": children,
                "path": os.path.relpath(directory_path, self.root_path).replace('\\', '/')
            }
            rel_path = os.path.relpath(directory_path, self.root_path).replace('\\', '/')
            json_filename = rel_path.replace('/', '_') + '.json'
            output_path = os.path.join(self.output_path, json_filename)
            self.save_json(dir_json, output_path)
            print(f" Saved directory: {output_path}")

    def process_markdown_file(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                raw_content = f.read()

            cleaned_content = self.clean_text(raw_content)
            rel_path = os.path.relpath(file_path, self.root_path).replace('\\', '/')

            json_data = {
                "name": os.path.splitext(os.path.basename(file_path))[0],
                "type": "file",
                "content": cleaned_content,
                "children": [],
                "path": rel_path
            }

            filename_base = os.path.splitext(rel_path)[0]
            json_filename = filename_base.replace('/', '_') + '.json'
            output_file_path = os.path.join(self.output_path, json_filename)
            self.save_json(json_data, output_file_path)
            print(f" Processed markdown: {output_file_path}")
        except Exception as e:
            print(f" Failed to process markdown {file_path}: {e}")

    def process_excel_file(self, file_path):
        try:
            df = pd.read_excel(file_path)
            df.columns = df.columns.str.strip()
            col_map = {col.strip().lower(): col for col in df.columns}
            has_steps_col = "test step" in col_map

            required_cols = [
                "requirement id", "requirement name",
                "acceptance criteria id", "acceptance criteria name",
                "test case id", "test case name", "test case description"
            ]
            for col in required_cols:
                if col not in col_map:
                    raise ValueError(f"Missing column: {col}")

            df.fillna("", inplace=True)
            hierarchy = {}

            for _, row in df.iterrows():
                req_id = str(row[col_map['requirement id']]).strip()
                req_name = str(row[col_map['requirement name']]).strip()
                ac_id = str(row[col_map['acceptance criteria id']]).strip()
                ac_name = str(row[col_map['acceptance criteria name']]).strip()
                tc_id = str(row[col_map['test case id']]).strip()
                tc_name = str(row[col_map['test case name']]).strip()
                tc_desc = str(row[col_map['test case description']]).replace('\n', '\\n').strip()
                tc_step = str(row[col_map['test step']]).strip() if has_steps_col else ""

                if req_id not in hierarchy:
                    hierarchy[req_id] = {
                        "id": req_id,
                        "name": req_name,
                        "children": {}
                    }

                if ac_id not in hierarchy[req_id]["children"]:
                    hierarchy[req_id]["children"][ac_id] = {
                        "id": ac_id,
                        "name": ac_name,
                        "children": {}
                    }

                if tc_id not in hierarchy[req_id]["children"][ac_id]["children"]:
                    hierarchy[req_id]["children"][ac_id]["children"][tc_id] = {
                        "id": tc_id,
                        "name": tc_name,
                        "type": "testcase",
                        "description": tc_desc,
                        "steps": []
                    }

                if tc_step:
                    hierarchy[req_id]["children"][ac_id]["children"][tc_id]["steps"].append(tc_step)

            for req in hierarchy.values():
                self.save_json({
                    "file_id": req["id"],
                    "name": req["name"],
                    "type": "requirement",
                    "path": f"{file_path}/{req['id']}",
                    "children": list(req["children"].keys())
                }, os.path.join(self.output_path, f"{req['id']}.json"))

                for ac in req["children"].values():
                    self.save_json({
                        "file_id": ac["id"],
                        "name": ac["name"],
                        "type": "criteria",
                        "path": f"{file_path}/{ac['id']}",
                        "children": list(ac["children"].keys())
                    }, os.path.join(self.output_path, f"{ac['id']}.json"))

                    for tc in ac["children"].values():
                        self.save_json({
                            "file_id": tc["id"],
                            "name": tc["name"],
                            "type": tc["type"],
                            "path": f"{file_path}/{tc['id']}",
                            "description": tc["description"],
                          "content": "\n".join(tc["steps"])
                        }, os.path.join(self.output_path, f"{tc['id']}.json"))

            print(" Created JSON files with test case 'content' included.")

        except Exception as e:
            print(f" Error processing Excel file {file_path}: {e}")

    def save_json(self, data, output_file_path):
        try:
            with open(output_file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f" Error saving JSON to {output_file_path}: {e}")

if __name__ == "__main__":
    parser = DirectoryParser()
    parser.parse()
    print(" Directory parsing complete. Check the 'temp_data' folder.")
