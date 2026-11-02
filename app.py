import os
import pymysql
from flask import Flask, request, redirect, url_for, render_template, abort

app = Flask(__name__)


def get_conn():
    kwargs = dict(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", 3306)),
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"],
        database=os.environ["DB_NAME"],
        cursorclass=pymysql.cursors.DictCursor,
    )
    # Azure MySQL mewajibkan TLS; di lokal (docker compose) DB_SSL tidak diisi
    if os.environ.get("DB_SSL", "").lower() == "true":
        kwargs["ssl"] = {"ca": "/etc/ssl/certs/ca-certificates.crt"}
    return pymysql.connect(**kwargs)


def init_db():
    conn = get_conn()
    with conn.cursor() as cur:
        cur.execute(
            """CREATE TABLE IF NOT EXISTS tugas (
                id INT AUTO_INCREMENT PRIMARY KEY,
                mata_kuliah VARCHAR(100) NOT NULL,
                judul VARCHAR(255) NOT NULL,
                deadline DATE NULL,
                selesai TINYINT(1) NOT NULL DEFAULT 0,
                dibuat TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )"""
        )
    conn.commit()
    conn.close()


@app.route("/")
def index():
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, mata_kuliah, judul, deadline, selesai "
                "FROM tugas ORDER BY selesai ASC, deadline IS NULL, deadline ASC, id DESC"
            )
            rows = cur.fetchall()
    finally:
        conn.close()
    total = len(rows)
    selesai = sum(1 for r in rows if r["selesai"])
    return render_template("index.html", rows=rows, total=total, selesai=selesai)


@app.route("/tambah", methods=["POST"])
def tambah():
    mk = request.form.get("mata_kuliah", "").strip()
    judul = request.form.get("judul", "").strip()
    deadline = request.form.get("deadline") or None
    if mk and judul:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO tugas (mata_kuliah, judul, deadline) VALUES (%s, %s, %s)",
                    (mk, judul, deadline),
                )
            conn.commit()
        finally:
            conn.close()
    return redirect(url_for("index"))


@app.route("/edit/<int:tugas_id>", methods=["GET", "POST"])
def edit(tugas_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            if request.method == "POST":
                mk = request.form.get("mata_kuliah", "").strip()
                judul = request.form.get("judul", "").strip()
                deadline = request.form.get("deadline") or None
                if mk and judul:
                    cur.execute(
                        "UPDATE tugas SET mata_kuliah = %s, judul = %s, deadline = %s WHERE id = %s",
                        (mk, judul, deadline, tugas_id),
                    )
                    conn.commit()
                return redirect(url_for("index"))
            cur.execute(
                "SELECT id, mata_kuliah, judul, deadline FROM tugas WHERE id = %s",
                (tugas_id,),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    if not row:
        abort(404)
    return render_template("edit.html", r=row)


@app.route("/selesai/<int:tugas_id>", methods=["POST"])
def toggle_selesai(tugas_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE tugas SET selesai = 1 - selesai WHERE id = %s", (tugas_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("index"))


@app.route("/hapus/<int:tugas_id>", methods=["POST"])
def hapus(tugas_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM tugas WHERE id = %s", (tugas_id,))
        conn.commit()
    finally:
        conn.close()
    return redirect(url_for("index"))


init_db()