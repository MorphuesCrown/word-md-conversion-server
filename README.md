# Pandoc文档转换工具

这个Python脚本用于将Word文档（.docx）、Markdown格式相互转换。

### 安装Pandoc

**Ubuntu/Debian:**
```bash
sudo apt-get install pandoc
```

## 使用方法

### 1. 运行脚本

```bash
uv run uvicorn main:app --reload

```

## 测试

```bash
curl -X POST "http://localhost:8000/word-to-md" \
  -F "file=@test.docx" \
  --output result.md

curl -X POST "http://localhost:8000/md-to-word" \
  -F "file=@test.md" \
  --output result.docx
  
```