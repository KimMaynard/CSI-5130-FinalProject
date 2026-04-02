from flask import Flask, jsonify, request
from flask_cors import CORS

from athena_quiz_engine import AthenaQuizError, generate_quiz_for_topic, grade_quiz

app = Flask(__name__)
CORS(app)


@app.route("/api/quiz", methods=["POST"])
def create_quiz():
    try:
        data = request.get_json() or {}

        topic = data.get("topic", "")
        difficulty = data.get("difficulty", "easy")
        num_questions = int(data.get("num_questions", 3))

        quiz_data = generate_quiz_for_topic(
            topic=topic,
            difficulty=difficulty,
            num_questions=num_questions,
        )

        return jsonify(quiz_data), 200

    except AthenaQuizError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Server error: {error}"}), 500


@app.route("/api/grade", methods=["POST"])
def grade_generated_quiz():
    try:
        data = request.get_json() or {}

        quiz_data = data.get("quiz_data")
        user_answers = data.get("user_answers", [])

        if not quiz_data:
            return jsonify({"error": "Missing quiz_data."}), 400

        graded_results = grade_quiz(quiz_data, user_answers)
        return jsonify(graded_results), 200

    except AthenaQuizError as error:
        return jsonify({"error": str(error)}), 400
    except Exception as error:
        return jsonify({"error": f"Server error: {error}"}), 500


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Athena backend is running."}), 200


if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)