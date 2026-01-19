import requests
import re
import os

BASE_URL = "https://raw.githubusercontent.com/v2fly/domain-list-community/master/data/"

class RuleConverter:
    def __init__(self, exclude_includes=None):
        self.processed_files = set()
        self.exclude_includes = exclude_includes or []
        # 使用 set 保证去重
        self.rules = {
            "DOMAIN": set(),
            "DOMAIN-SUFFIX": set(),
            "URL-REGEX": set(),
            "DOMAIN-KEYWORD": set()
        }
        self.header_comments = set()
    
    def read_tasks(self, file_path):
        """
        读取指定格式的txt文件。
        格式: typea, typeb1, typeb2...
        忽略空行和以 # 开头的行。
        返回: List[Tuple[str, List[str]]]
        """
        result = []
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            print(f"错误: 文件 {file_path} 未找到。")
            return result

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    # 2. 处理：去除行首尾的空白字符
                    clean_line = line.strip()
                    
                    # 忽略空行或以 # 开头的行
                    if not clean_line or clean_line.startswith('#'):
                        continue
                    
                    # 按逗号分割并处理每个元素的空格
                    parts = [p.strip() for p in clean_line.split(',')]
                    
                    # 1 & 4. 处理逻辑：
                    # 第一个元素为 typea
                    # 剩余所有元素放入列表作为 typeb 部分
                    type_a = parts[0]
                    
                    # 3. 如果不存在 typeb，则 parts[1:] 会自然返回一个空列表 []
                    type_b_list = parts[1:]
                    
                    # 将结果以元组形式存入列表 [("typea", ["typeb1", "typeb2"])]
                    result.append((type_a, type_b_list))
                    
        except Exception as e:
            print(f"读取文件时发生错误: {e}")
            return result
        self.tasks = result

    def fetch_content(self, filename):
        url = BASE_URL + filename
        print(f"Fetching: {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"Error fetching {filename}: {e}")
            return ""

    def process_line(self, line):
        raw_line = line.strip()
        
        # 1. 处理空行
        if not raw_line:
            return

        # 2. 处理单行注释（保留在 header_comments）
        if raw_line.startswith("#"):
            self.header_comments.add(raw_line)
            return

        # 3. 处理规则后的行内注释 (例如: domain.com # comment -> domain.com)
        if "#" in raw_line:
            line_content = raw_line.split("#")[0].strip()
        else:
            line_content = raw_line

        # 如果剔除注释后为空，则跳过
        if not line_content:
            return

        # 4. 移除属性 @...
        line_content = re.sub(r'\s*@\S+', '', line_content).strip()

        # 5. 处理包含 include:
        if line_content.startswith("include:"):
            include_file = line_content.split(":", 1)[1].strip()
            # 如果在排除列表中，跳过
            if include_file in self.exclude_includes:
                print(f"Skipping excluded include: {include_file}")
                return
            self.convert(include_file)
            return

        # 6. 转换逻辑
        if line_content.startswith("full:"):
            domain = line_content.split(":", 1)[1].strip()
            self.rules["DOMAIN"].add(f"DOMAIN,{domain}")
        elif line_content.startswith("keyword:"):
            keyword = line_content.split(":", 1)[1].strip()
            self.rules["DOMAIN-KEYWORD"].add(f"DOMAIN-KEYWORD,{keyword}")
        elif line_content.startswith("regexp:"):
            regex = line_content.split(":", 1)[1].strip()
            self.rules["URL-REGEX"].add(f"URL-REGEX,{regex}")
        else:
            # 默认处理为 DOMAIN-SUFFIX
            domain = line_content
            if line_content.startswith("domain:"):
                domain = line_content.split(":", 1)[1].strip()
            self.rules["DOMAIN-SUFFIX"].add(f"DOMAIN-SUFFIX,{domain}")

    def convert(self, filename):
        if filename in self.processed_files:
            return
        self.processed_files.add(filename)
        
        content = self.fetch_content(filename)
        for line in content.splitlines():
            self.process_line(line)

    def save_to_file(self, output_name):
        order = ["DOMAIN", "DOMAIN-SUFFIX", "URL-REGEX", "DOMAIN-KEYWORD"]
        
        with open(output_name, "w", encoding="utf-8") as f:
            # 首先写入收集到的单行注释，按字母排序
            if self.header_comments:
                for comment in sorted(list(self.header_comments)):
                    f.write(f"{comment}\n")
            
            # 按顺序写入规则
            for category in order:
                sorted_rules = sorted(list(self.rules[category]))
                for rule in sorted_rules:
                    f.write(f"{rule}\n")

def main():   
    temp_converter = RuleConverter()
    temp_converter.read_tasks(file_path="a/tasks.txt")
    tasks = temp_converter.tasks
    print(tasks)
    # return
    for source, excludes in tasks:
        print(f"\n--- Processing Task: {source} ---")
        converter = RuleConverter(exclude_includes=excludes)
        converter.convert(source)
        filepath = f"txt/{source.replace('!', 'not-')}.txt"
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        converter.save_to_file(filepath)
        print(f"Done: {source}")

if __name__ == "__main__":
    main()
