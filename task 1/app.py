from flask import Flask, render_template, request

from password_generator import generate_password


app = Flask(__name__)


@app.route("/", methods=["GET", "POST"])
def index():
    password = None
    error = None
    length = ""

    if request.method == "POST":
        length = request.form.get("length", "").strip()

        try:
            length = int(length)
            password = generate_password(length)
        except ValueError as e:
            error = str(e)

    return render_template(
        "index.html",
        password=password,
        error=error,
        length=length,
    )


if __name__ == "__main__":
    app.run(debug=True)