import os
import click
from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)

DB_HOST = os.getenv("DB_HOST")
DB_NAME = os.getenv("DB_NAME")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")


def get_db_connection():
    conn = psycopg2.connect(
        host=DB_HOST,
        database=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )
    return conn


def init_db():
    print("Tentando inicializar a tabela 'flags'...")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS flags (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) UNIQUE NOT NULL,
                is_enabled BOOLEAN NOT NULL DEFAULT false,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        cur.close()
        conn.close()
        print("Tabela 'flags' inicializada com sucesso.")
    except psycopg2.OperationalError as e:
        print(f"Erro de conexão ao inicializar o banco de dados: {e}")
    except Exception as e:
        print(f"Um erro inesperado ocorreu durante a inicialização do DB: {e}")


@app.cli.command("init-db")
def init_db_command():
    init_db()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "Toggle Master API online V1.0",
        "endpoints": {
            "health": "/health",
            "list_flags": "/flags",
            "get_flag": "/flags/<name>",
            "create_flag": "POST /flags",
            "update_flag": "PUT /flags/<name>"
        }
    }), 200


@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "ok"}), 200


@app.route("/flags", methods=["POST"])
def create_flag():
    data = request.get_json()

    if not data or "name" not in data:
        return jsonify({"error": "O campo 'name' é obrigatório"}), 400

    name = data["name"]

    # Aceita 'enabled' como padrão da API e 'is_enabled' como compatibilidade
    if "enabled" in data:
        enabled = data["enabled"]
    else:
        enabled = data.get("is_enabled", False)

    if not isinstance(enabled, bool):
        return jsonify({"error": "O campo 'enabled' deve ser booleano"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO flags (name, is_enabled) VALUES (%s, %s)",
            (name, enabled)
        )
        conn.commit()
    except psycopg2.IntegrityError:
        if "conn" in locals() and not conn.closed:
            conn.rollback()
        return jsonify({"error": f"A flag '{name}' já existe"}), 409
    except Exception as e:
        return jsonify({
            "error": "Erro interno no servidor ao criar a flag",
            "details": str(e)
        }), 500
    finally:
        if "cur" in locals() and not cur.closed:
            cur.close()
        if "conn" in locals() and not conn.closed:
            conn.close()

    return jsonify({
        "message": f"Flag '{name}' criada com sucesso",
        "flag": {
            "name": name,
            "enabled": enabled
        }
    }), 201


@app.route("/flags", methods=["GET"])
def get_flags():
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, is_enabled FROM flags ORDER BY name")
        rows = cur.fetchall()
    except Exception as e:
        return jsonify({
            "error": "Erro interno no servidor ao buscar as flags",
            "details": str(e)
        }), 500
    finally:
        if "cur" in locals() and not cur.closed:
            cur.close()
        if "conn" in locals() and not conn.closed:
            conn.close()

    flags = [
        {
            "name": row["name"],
            "enabled": row["is_enabled"]
        }
        for row in rows
    ]

    return jsonify(flags), 200


@app.route("/flags/<string:name>", methods=["GET"])
def get_flag_status(name):
    try:
        conn = get_db_connection()
        cur = conn.cursor(cursor_factory=RealDictCursor)
        cur.execute("SELECT name, is_enabled FROM flags WHERE name = %s", (name,))
        row = cur.fetchone()
    except Exception as e:
        return jsonify({
            "error": "Erro interno no servidor ao buscar a flag",
            "details": str(e)
        }), 500
    finally:
        if "cur" in locals() and not cur.closed:
            cur.close()
        if "conn" in locals() and not conn.closed:
            conn.close()

    if not row:
        return jsonify({"error": "Flag não encontrada"}), 404

    flag = {
        "name": row["name"],
        "enabled": row["is_enabled"]
    }

    return jsonify(flag), 200


@app.route("/flags/<string:name>", methods=["PUT"])
def update_flag(name):
    data = request.get_json()

    if data is None:
        return jsonify({"error": "Body JSON é obrigatório"}), 400

    # Aceita 'enabled' como padrão da API e 'is_enabled' como compatibilidade
    if "enabled" in data:
        enabled = data["enabled"]
    elif "is_enabled" in data:
        enabled = data["is_enabled"]
    else:
        return jsonify({"error": "O campo 'enabled' (booleano) é obrigatório"}), 400

    if not isinstance(enabled, bool):
        return jsonify({"error": "O campo 'enabled' deve ser booleano"}), 400

    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE flags SET is_enabled = %s WHERE name = %s",
            (enabled, name)
        )

        if cur.rowcount == 0:
            conn.rollback()
            return jsonify({"error": "Flag não encontrada"}), 404

        conn.commit()
    except Exception as e:
        return jsonify({
            "error": "Erro interno no servidor ao atualizar a flag",
            "details": str(e)
        }), 500
    finally:
        if "cur" in locals() and not cur.closed:
            cur.close()
        if "conn" in locals() and not conn.closed:
            conn.close()

    return jsonify({
        "message": f"Flag '{name}' atualizada com sucesso",
        "flag": {
            "name": name,
            "enabled": enabled
        }
    }), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)