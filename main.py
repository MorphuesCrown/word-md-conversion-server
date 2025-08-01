from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import tempfile
import subprocess
import os
import base64
import re
import shutil

app = FastAPI()

class MarkdownRequest(BaseModel):
    content: str

@app.post("/md-to-word")
async def md_to_word(request: MarkdownRequest):
    with tempfile.TemporaryDirectory() as tmpdir:
        input_path = os.path.join(tmpdir, "input.md")
        
        # 使用 NamedTemporaryFile 创建输出文件，这样文件会在进程结束时自动清理
        with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp_output:
            output_path = tmp_output.name

        # 保存 Markdown 内容到文件
        with open(input_path, "w", encoding="utf-8") as f:
            f.write(request.content)

        # 调用 pandoc 进行转换
        try:
            subprocess.run([
                "pandoc",
                input_path,
                "-f", "markdown",
                "-t", "docx",
                "-o", output_path
            ], check=True)
        except subprocess.CalledProcessError as e:
            # 清理临时文件
            os.unlink(output_path)
            raise HTTPException(status_code=500, detail=f"Pandoc 转换失败：{e}")

        # 确保输出文件生成成功
        if not os.path.exists(output_path):
            raise HTTPException(status_code=500, detail="转换失败，未生成 Word 文件")

        # 返回 Word 文件，文件会在进程结束时自动清理
        return FileResponse(
            output_path,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            filename="result.docx"
        )

@app.post("/word-to-md")
async def word_to_md(file: UploadFile = File(...)):
    print("word-to-md")
    if not file.filename.endswith(".docx") and not file.filename.endswith(".doc"):
        raise HTTPException(status_code=400, detail="仅支持 .docx 或 .doc 文件")

    with tempfile.TemporaryDirectory() as tmpdir:
        input_filename = "input.docx" if file.filename.endswith(".docx") else "input.doc"
        input_path = os.path.join(tmpdir, input_filename)

         # 使用 NamedTemporaryFile 创建输出文件，这样文件会在进程结束时自动清理
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as tmp_output:
            output_path = tmp_output.name
        
        # 保存上传的 Word 文件
        with open(input_path, "wb") as f:
            f.write(await file.read())

        if input_path.endswith(".doc"):
            subprocess.run([
                "libreoffice",
                "--headless",
                "--convert-to", "docx",
                input_path,
                "--outdir", os.path.dirname(input_path)
                
            ], check=True)
            input_path = input_path.replace(".doc", ".docx")

        media_dir = os.path.join(tmpdir, "media")

        # 调用 pandoc 进行转换
        try:
            subprocess.run([
                "pandoc",
                input_path,
                "-o", output_path,
                f"--extract-media={media_dir}"
            ], check=True)
        except subprocess.CalledProcessError as e:
            # 清理临时文件
            os.unlink(output_path)
            raise HTTPException(status_code=500, detail=f"Pandoc 转换失败：{e}")

        # 读取 markdown 内容
        with open(output_path, "r", encoding="utf-8") as f:
            md_content = f.read()

        # 替换所有图片路径为 base64
        if os.path.exists(media_dir):
            for root, _, files in os.walk(media_dir):
                for file in files:
                    img_path = os.path.join(root, file)
                    ext = os.path.splitext(file)[1][1:].lower()  # png, jpg 等

                    with open(img_path, "rb") as img_file:
                        b64_str = base64.b64encode(img_file.read()).decode("utf-8")

                    data_uri = f"data:image/{ext};base64,{b64_str}"
                    pattern = re.escape(file)
                    md_content = re.sub(rf'\(([^)]*{pattern})\)', f'({data_uri})', md_content)

            # 清除media目录
            shutil.rmtree(media_dir)

        # 返回 Markdown 字符串
        return {"content": md_content}
