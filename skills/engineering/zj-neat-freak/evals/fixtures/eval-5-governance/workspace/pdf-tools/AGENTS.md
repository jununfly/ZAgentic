# pdf-tools

PDF 工具集。

## 启动

```bash
pip install -r requirements.txt
uvicorn app:api --port 3001
```

## 约定

- 输出文件统一落 `output/` 目录
- 大文件（>50MB）走流式处理，别整个读进内存
