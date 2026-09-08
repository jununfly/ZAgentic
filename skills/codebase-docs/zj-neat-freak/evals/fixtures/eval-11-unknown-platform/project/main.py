"""flasknotes：极简笔记 API。"""

import csv
import io

from flask import Flask, jsonify, request, Response

app = Flask(__name__)

# 内存存储，重启即清空
NOTES: list[dict] = []


@app.get("/notes")
def list_notes():
    return jsonify(NOTES)


@app.post("/notes")
def add_note():
    note = {"id": len(NOTES) + 1, "text": request.json.get("text", "")}
    NOTES.append(note)
    return jsonify(note), 201


@app.get("/export")
def export_notes():
    # 导出 CSV，2026-06 新增
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "text"])
    for note in NOTES:
        writer.writerow([note["id"], note["text"]])
    return Response(buf.getvalue(), mimetype="text/csv")


if __name__ == "__main__":
    app.run(port=5000)
