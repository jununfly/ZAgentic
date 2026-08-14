# flasknotes

极简笔记 API，个人自用。

## 运行

```bash
pip install -r requirements.txt
python main.py
# http://localhost:5000
```

## 技术栈

Flask 3，内存 list 存储（重启即清空）。

## 功能

- `GET /notes` 列出全部笔记
- `POST /notes` 新增笔记

## 约定

- 单文件 main.py，先不拆模块
- 中文注释
