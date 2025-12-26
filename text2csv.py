import csv
import re

# 入力テキストファイル
input_file = input("変換したいテキストファイルのパスを入力してください: ")

# 出力CSVファイル
output_file = input("出力したいCSVファイルのパスを入力してください: ")

# x: 123.45, y: 678.90 のパターンにマッチ
pattern = re.compile(r"x\s*:\s*([0-9.\-]+)\s*,\s*y\s*:\s*([0-9.\-]+)")

rows = []

with open(input_file, "r", encoding="utf-8") as f:
    for line in f:
        match = pattern.search(line)
        if match:
            x_val = match.group(1)
            y_val = match.group(2)
            rows.append([x_val, y_val])

# CSVとして書き出し
with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
    writer = csv.writer(csvfile)
    writer.writerow(["x", "y"])  # header
    writer.writerows(rows)

print("変換が完了しました！ ->", output_file)
