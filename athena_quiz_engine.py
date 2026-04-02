import json
import os
import random
import re
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import nltk
import requests
from nltk.corpus import stopwords
from nltk.tokenize import sent_tokenize, word_tokenize
from openai import OpenAI
from sklearn.feature_extraction.text import TfidfVectorizer


# keeping the main quiz engine in one file for now
# this makes it easier to test in terminal before hooking it into the frontend

nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)

WIKIPEDIA_API_URL = "https://en.wikipedia.org/w/api.php"
STOP_WORDS = set(stopwords.words("english"))
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")


class AthenaQuizError(Exception):
    """custom error for quiz generation problems"""


def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise AthenaQuizError(
            "OPENAI_API_KEY is not set. In terminal, run: export OPENAI_API_KEY='your_key_here'"
        )
    return OpenAI(api_key=api_key)


# user should type something short like "Golf" or "Ancient Greece"
def validate_topic_input(topic: str) -> str:
    cleaned = (topic or "").strip()
    if not cleaned:
        raise AthenaQuizError("Please enter a topic like 'Golf' or 'Ancient Greece'.")
    if len(cleaned.split()) > 6:
        raise AthenaQuizError("Please enter a short topic name, not a full sentence request.")
    if not re.search(r"[A-Za-z]", cleaned):
        raise AthenaQuizError("Your topic must include letters.")
    return cleaned


# gets plain text from wikipedia for the chosen topic
def fetch_wikipedia_text(topic: str, max_chars: int = 8000) -> str:
    if not topic or not topic.strip():
        raise AthenaQuizError("Please enter a topic before generating a quiz.")

    normalized_topic = topic.strip().replace(" ", "_")
    params = {
        "action": "query",
        "format": "json",
        "prop": "extracts",
        "explaintext": True,
        "redirects": 1,
        "titles": normalized_topic,
    }
    headers = {"User-Agent": "Athena-AI-Quiz-App/1.0 (student final project)"}

    try:
        response = requests.get(WIKIPEDIA_API_URL, params=params, headers=headers, timeout=12)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as exc:
        raise AthenaQuizError(f"Could not reach Wikipedia: {exc}") from exc

    pages = data.get("query", {}).get("pages", {})
    for page in pages.values():
        if "missing" in page:
            raise AthenaQuizError(f"Wikipedia could not find a page for '{topic}'.")
        extract = page.get("extract", "").strip()
        if not extract:
            raise AthenaQuizError(f"Wikipedia returned no usable text for '{topic}'.")
        return extract[:max_chars]

    raise AthenaQuizError("No page data was returned from Wikipedia.")


# cleaning some wikipedia leftovers before using the text
def normalize_text(text: str) -> str:
    text = re.sub(r"==+\s*[^=]+\s*==+", " ", text)
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\([^)]*listen[^)]*\)", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# splitting into sentences and filtering obvious junk / fragments
def split_into_sentences(text: str) -> List[str]:
    sentences = sent_tokenize(text)
    cleaned = []

    for sentence in sentences:
        sentence = sentence.strip()

        if len(sentence.split()) < 8:
            continue
        if not re.search(r"[.!?]$", sentence):
            continue
        if "==" in sentence:
            continue
        if sentence.count(":") > 1:
            continue
        if re.match(r"^[^A-Za-z]*$", sentence):
            continue

        cleaned.append(sentence)

    return cleaned


# token cleanup for tf-idf
def _tokenize_for_keywords(text: str) -> List[str]:
    text = re.sub(r"[^a-zA-Z\s-]", " ", text.lower())
    words = word_tokenize(text)

    banned_words = {
        "known", "also", "used", "called", "name", "many", "made", "make",
        "become", "became", "found", "according", "including", "during",
        "among", "would", "could", "often", "later", "early", "associated"
    }

    filtered = [
        word
        for word in words
        if word not in STOP_WORDS
        and word not in banned_words
        and len(word) > 2
        and re.fullmatch(r"[a-zA-Z-]+", word)
    ]
    return filtered


# ranking words by tf-idf so we can find important concepts
def extract_ranked_keywords(text: str, top_k: int = 60) -> List[Tuple[str, float]]:
    filtered_words = _tokenize_for_keywords(text)
    if not filtered_words:
        raise AthenaQuizError("The article did not contain enough clean text to build a quiz.")

    clean_text = " ".join(filtered_words)
    vectorizer = TfidfVectorizer(ngram_range=(1, 1))
    tfidf = vectorizer.fit_transform([clean_text])

    ranked = list(zip(vectorizer.get_feature_names_out(), tfidf.toarray()[0]))
    ranked.sort(key=lambda item: item[1], reverse=True)
    return ranked[:top_k]


# difficulty changes which part of the ranked keyword list we use
def choose_keywords_by_difficulty(ranked_keywords: List[Tuple[str, float]], difficulty: str) -> List[str]:
    if not ranked_keywords:
        raise AthenaQuizError("No keywords were available for this topic.")

    difficulty = difficulty.lower().strip()
    total = len(ranked_keywords)

    easy_cut = max(8, total // 4)
    medium_cut = max(16, total // 2)

    if difficulty == "easy":
        selection = ranked_keywords[:easy_cut]
    elif difficulty == "medium":
        selection = ranked_keywords[easy_cut:medium_cut]
    elif difficulty == "hard":
        selection = ranked_keywords[medium_cut:max(medium_cut + 10, int(total * 0.8))]
    else:
        raise AthenaQuizError("Difficulty must be 'easy', 'medium', or 'hard'.")

    keywords = [word for word, _ in selection]
    keywords = [word for word in keywords if len(word) > 2]

    if not keywords:
        raise AthenaQuizError(f"Could not build keyword pool for difficulty '{difficulty}'.")

    return keywords


def sentence_contains_keyword(sentence: str, keyword: str) -> bool:
    pattern = rf"\b{re.escape(keyword)}\b"
    return re.search(pattern, sentence, flags=re.IGNORECASE) is not None


def mask_keyword_in_sentence(sentence: str, keyword: str) -> str:
    pattern = rf"\b{re.escape(keyword)}\b"
    return re.sub(pattern, "_____", sentence, count=1, flags=re.IGNORECASE)


# gives a sentence a score so we can pick stronger source lines
def score_sentence_for_question(sentence: str, keyword: str) -> int:
    score = 0
    word_count = len(sentence.split())

    if 10 <= word_count <= 22:
        score += 4
    elif 23 <= word_count <= 30:
        score += 2

    if sentence_contains_keyword(sentence, keyword):
        score += 4

    if re.search(r"[.!?]$", sentence):
        score += 3

    if "==" in sentence or "|" in sentence:
        score -= 5
    if any(char.isdigit() for char in sentence):
        score -= 2
    if sentence.lower().startswith(("see also", "references", "external links")):
        score -= 5

    return score


def find_best_sentence(sentences: List[str], keyword: str, used_sentences: set) -> Optional[str]:
    candidates = [s for s in sentences if s not in used_sentences and sentence_contains_keyword(s, keyword)]
    if not candidates:
        return None

    ranked = sorted(candidates, key=lambda s: score_sentence_for_question(s, keyword), reverse=True)
    return ranked[0]


# distractors for the fallback non-AI mode
def build_distractors(correct_answer: str, keyword_pool: List[str], difficulty: str, num_distractors: int = 3) -> List[str]:
    pool = [word for word in keyword_pool if word.lower() != correct_answer.lower()]
    if not pool:
        return []

    def distractor_rank(word: str) -> Tuple[int, int, int]:
        same_start = 0 if word[:1].lower() == correct_answer[:1].lower() else 1
        length_gap = abs(len(word) - len(correct_answer))
        overlap = len(set(word.lower()) & set(correct_answer.lower()))
        overlap_score = -overlap
        return same_start, length_gap, overlap_score

    if difficulty == "easy":
        candidates = pool[:]
        random.shuffle(candidates)
    elif difficulty == "medium":
        candidates = sorted(pool, key=lambda word: (abs(len(word) - len(correct_answer)), distractor_rank(word)))
    else:
        candidates = sorted(pool, key=distractor_rank)

    unique = []
    seen = set()
    for word in candidates:
        lowered = word.lower()
        if lowered not in seen and lowered != correct_answer.lower():
            unique.append(word)
            seen.add(lowered)
        if len(unique) == num_distractors:
            break

    return unique


def get_sentence_complexity_label(sentence: str) -> str:
    word_count = len(sentence.split())
    if word_count <= 12:
        return "simple"
    if word_count <= 22:
        return "moderate"
    return "complex"


def sentence_matches_difficulty(sentence: str, difficulty: str) -> bool:
    complexity = get_sentence_complexity_label(sentence)
    if difficulty == "easy":
        return complexity == "simple"
    if difficulty == "medium":
        return complexity in {"simple", "moderate"}
    return complexity in {"moderate", "complex"}


def looks_like_natural_sentence(sentence: str) -> bool:
    weird_patterns = [
        r"\bfirst on a course\b",
        r"\bknown as known\b",
        r"\balso of\b",
        r"\bthe the\b",
        r"\ba a\b",
        r"\ban an\b",
    ]

    if len(sentence.split()) < 8:
        return False
    if not re.search(r"[.!?]$", sentence):
        return False

    lowered = sentence.lower()
    for pattern in weird_patterns:
        if re.search(pattern, lowered):
            return False

    return True


# ---------- fallback rule-based question builders ----------

def build_multiple_choice_question(
    keyword: str,
    sentence: str,
    keyword_pool: List[str],
    difficulty: str,
    question_number: int,
) -> Optional[Dict]:
    question_text = mask_keyword_in_sentence(sentence, keyword)

    if "_____" not in question_text:
        return None
    if not re.search(r"[.!?]$", question_text):
        return None

    distractors = build_distractors(keyword, keyword_pool, difficulty)
    if len(distractors) < 3:
        return None

    options = distractors + [keyword]
    random.shuffle(options)

    return {
        "question_number": question_number,
        "question_type": "multiple_choice",
        "question": f"Choose the best word to complete the sentence. {question_text}",
        "correct_answer": keyword,
        "options": options,
        "difficulty": difficulty,
        "explanation": "",
    }


def build_true_false_question(
    sentence: str,
    correct_answer: str,
    keyword_pool: List[str],
    difficulty: str,
    question_number: int,
) -> Optional[Dict]:
    sentence = sentence.strip()

    if len(sentence.split()) < 8:
        return None
    if not re.search(r"[.!?]$", sentence):
        return None
    if not looks_like_natural_sentence(sentence):
        return None

    make_true = random.choice([True, False])
    shown_statement = sentence
    correct_option = "True"

    if not make_true:
        replacement_options = build_distractors(correct_answer, keyword_pool, difficulty, num_distractors=4)
        replacement = None
        pattern = rf"\b{re.escape(correct_answer)}\b"

        for option in replacement_options:
            candidate = re.sub(pattern, option, sentence, count=1, flags=re.IGNORECASE)
            if candidate != sentence and looks_like_natural_sentence(candidate):
                replacement = option
                shown_statement = candidate
                break

        if replacement is None:
            return None

        correct_option = "False"

    return {
        "question_number": question_number,
        "question_type": "true_false",
        "question": f"True or False: {shown_statement}",
        "correct_answer": correct_option,
        "options": ["True", "False"],
        "difficulty": difficulty,
        "explanation": "",
    }


def build_definition_question(
    keyword: str,
    sentences: List[str],
    keyword_pool: List[str],
    difficulty: str,
    question_number: int,
) -> Optional[Dict]:
    sentence = next(
        (
            s for s in sentences
            if sentence_contains_keyword(s, keyword)
            and 10 <= len(s.split()) <= 24
            and re.search(r"[.!?]$", s)
        ),
        None,
    )

    if not sentence:
        return None

    masked = mask_keyword_in_sentence(sentence, keyword)
    if not re.search(r"[.!?]$", masked):
        return None

    prompt = f"Choose the term that best completes the sentence. {masked}"

    distractors = build_distractors(keyword, keyword_pool, difficulty)
    if len(distractors) < 3:
        return None

    options = distractors + [keyword]
    random.shuffle(options)

    return {
        "question_number": question_number,
        "question_type": "definition",
        "question": prompt,
        "correct_answer": keyword,
        "options": options,
        "difficulty": difficulty,
        "explanation": "",
    }


# ---------- AI source selection ----------

def select_source_sentences_for_ai(text: str, difficulty: str, max_sentences: int = 10) -> List[str]:
    normalized = normalize_text(text)
    sentences = split_into_sentences(normalized)
    ranked_keywords = extract_ranked_keywords(normalized)
    keyword_pool = choose_keywords_by_difficulty(ranked_keywords, difficulty)

    selected = []
    used_sentences = set()

    for keyword in keyword_pool:
        sentence = find_best_sentence(sentences, keyword, used_sentences)
        if not sentence:
            continue
        if len(sentence.split()) < 8:
            continue
        selected.append(sentence)
        used_sentences.add(sentence)

        if len(selected) >= max_sentences:
            break

    if len(selected) < max_sentences:
        for sentence in sentences:
            if sentence not in used_sentences and len(sentence.split()) >= 8:
                selected.append(sentence)
                used_sentences.add(sentence)
            if len(selected) >= max_sentences:
                break

    return selected


# ---------- AI quiz generation ----------

def generate_ai_quiz_from_text(
    topic: str,
    text: str,
    difficulty: str = "easy",
    num_questions: int = 5,
) -> List[Dict]:
    client = get_openai_client()

    source_sentences = select_source_sentences_for_ai(text, difficulty, max_sentences=12)
    if not source_sentences:
        raise AthenaQuizError("Could not find enough clean source material for AI question generation.")

    joined_source = "\n".join(f"- {sentence}" for sentence in source_sentences)

    difficulty_rules = {
        "easy": "Use very clear wording, obvious concepts, and simple answer choices.",
        "medium": "Use moderately challenging wording and believable distractors.",
        "hard": "Use more advanced wording, less obvious concepts, and stronger distractors.",
    }

    prompt = f"""
You are helping build an educational AI quiz app called Athena.

Create exactly {num_questions} quiz questions about the topic: "{topic}".

Difficulty: {difficulty}
Difficulty guidance: {difficulty_rules.get(difficulty, difficulty_rules["easy"])}

Rules:
- Use ONLY the source material below.
- Write questions in clear, student-friendly English.
- Avoid awkward wording, fragments, and vague pronouns unless fully clear.
- Make the quiz feel natural, not robotic.
- Include a mix of:
  - multiple_choice
  - true_false
  - definition
- If true/false would sound awkward, use multiple_choice or definition instead.
- Every question must be fully understandable on its own.
- For multiple_choice and definition, provide exactly 4 answer choices.
- For true_false, provide exactly 2 answer choices: ["True", "False"].
- The correct answer must exactly match one of the answer choices.
- Return valid JSON only.

Source material:
{joined_source}
""".strip()

    response = client.responses.create(
        model=OPENAI_MODEL,
        input=prompt,
        text={
            "format": {
                "type": "json_schema",
                "name": "athena_quiz_schema",
                "strict": True,
                "schema": {
                    "type": "object",
                    "properties": {
                        "questions": {
                            "type": "array",
                            "minItems": num_questions,
                            "maxItems": num_questions,
                            "items": {
                                "type": "object",
                                "properties": {
                                    "question_type": {
                                        "type": "string",
                                        "enum": ["multiple_choice", "true_false", "definition"]
                                    },
                                    "question": {"type": "string"},
                                    "options": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                        "minItems": 2,
                                        "maxItems": 4
                                    },
                                    "correct_answer": {"type": "string"},
                                    "explanation": {"type": "string"}
                                },
                                "required": [
                                    "question_type",
                                    "question",
                                    "options",
                                    "correct_answer",
                                    "explanation"
                                ],
                                "additionalProperties": False
                            }
                        }
                    },
                    "required": ["questions"],
                    "additionalProperties": False
                }
            }
        }
    )

    content = json.loads(response.output_text)
    questions = content["questions"]

    cleaned_questions = []
    for idx, question in enumerate(questions, start=1):
        q_type = question["question_type"]
        options = [opt.strip() for opt in question["options"]]
        correct_answer = question["correct_answer"].strip()

        if q_type == "true_false":
            options = ["True", "False"]
            if correct_answer.lower() == "true":
                correct_answer = "True"
            elif correct_answer.lower() == "false":
                correct_answer = "False"
            else:
                raise AthenaQuizError("AI returned an invalid true/false answer.")
        elif len(options) != 4:
            raise AthenaQuizError("AI returned a question with an invalid number of answer choices.")

        if correct_answer not in options:
            raise AthenaQuizError("AI returned a correct answer that does not match the answer choices.")

        cleaned_questions.append(
            {
                "question_number": idx,
                "question_type": q_type,
                "question": question["question"].strip(),
                "options": options,
                "correct_answer": correct_answer,
                "difficulty": difficulty,
                "explanation": question["explanation"].strip(),
            }
        )

    return cleaned_questions


# ---------- fallback rule-based generation ----------

def generate_quiz_from_text(
    text: str,
    difficulty: str = "easy",
    num_questions: int = 5,
    question_types: Optional[List[str]] = None,
) -> List[Dict]:
    normalized = normalize_text(text)

    if len(normalized) < 500:
        raise AthenaQuizError(
            "This topic did not return enough Wikipedia content to build a strong quiz. "
            "Try a more specific topic."
        )

    sentences = split_into_sentences(normalized)
    if len(sentences) < 5:
        raise AthenaQuizError("Not enough sentence data was found to generate quiz questions.")

    ranked_keywords = extract_ranked_keywords(normalized)
    keyword_pool = choose_keywords_by_difficulty(ranked_keywords, difficulty)

    filtered_sentences = [sentence for sentence in sentences if sentence_matches_difficulty(sentence, difficulty)]
    if len(filtered_sentences) < 3:
        filtered_sentences = sentences

    if question_types is None:
        question_types = ["multiple_choice", "definition", "multiple_choice", "true_false"]

    quiz = []
    used_keywords = set()
    used_sentences = set()
    question_type_index = 0

    for keyword in keyword_pool:
        if len(quiz) >= num_questions:
            break
        if keyword.lower() in used_keywords:
            continue

        sentence = find_best_sentence(filtered_sentences, keyword, used_sentences)
        if not sentence:
            continue

        question_type = question_types[question_type_index % len(question_types)]
        question_number = len(quiz) + 1
        built_question = None

        if question_type == "multiple_choice":
            built_question = build_multiple_choice_question(keyword, sentence, keyword_pool, difficulty, question_number)
        elif question_type == "true_false":
            built_question = build_true_false_question(sentence, keyword, keyword_pool, difficulty, question_number)
        elif question_type == "definition":
            built_question = build_definition_question(keyword, filtered_sentences, keyword_pool, difficulty, question_number)

        if built_question is None:
            fallback_order = ["multiple_choice", "definition", "true_false"]
            for fallback_type in fallback_order:
                if fallback_type == question_type:
                    continue

                if fallback_type == "multiple_choice":
                    built_question = build_multiple_choice_question(keyword, sentence, keyword_pool, difficulty, question_number)
                elif fallback_type == "definition":
                    built_question = build_definition_question(keyword, filtered_sentences, keyword_pool, difficulty, question_number)
                elif fallback_type == "true_false":
                    built_question = build_true_false_question(sentence, keyword, keyword_pool, difficulty, question_number)

                if built_question is not None:
                    break

        if built_question is None:
            continue

        quiz.append(built_question)
        used_keywords.add(keyword.lower())
        used_sentences.add(sentence)
        question_type_index += 1

    if not quiz:
        raise AthenaQuizError("Athena could not generate any quiz questions for this topic.")

    if len(quiz) < num_questions:
        raise AthenaQuizError(
            f"Athena could only generate {len(quiz)} question(s) for this topic. "
            f"Try another topic or lower the question count."
        )

    return quiz


# ---------- top-level generation ----------

def generate_quiz_for_topic(
    topic: str,
    difficulty: str = "easy",
    num_questions: int = 5,
    question_types: Optional[List[str]] = None,
) -> Dict:
    topic = validate_topic_input(topic)

    if num_questions < 1 or num_questions > 15:
        raise AthenaQuizError("Please choose between 1 and 15 questions.")

    source_text = fetch_wikipedia_text(topic)

    try:
        questions = generate_ai_quiz_from_text(
            topic=topic,
            text=source_text,
            difficulty=difficulty,
            num_questions=num_questions,
        )
    except Exception as exc:
        print(f"AI generation failed, falling back to rule-based generation: {exc}")
        questions = generate_quiz_from_text(
            source_text,
            difficulty=difficulty,
            num_questions=num_questions,
            question_types=question_types,
        )

    return {
        "topic": topic,
        "difficulty": difficulty,
        "num_questions": len(questions),
        "question_types": question_types or ["multiple_choice", "definition", "true_false"],
        "questions": questions,
        "generated_at": datetime.now().isoformat(),
    }


def regenerate_quiz(quiz_data: Dict) -> Dict:
    return generate_quiz_for_topic(
        topic=quiz_data.get("topic", ""),
        difficulty=quiz_data.get("difficulty", "easy"),
        num_questions=quiz_data.get("num_questions", 5),
        question_types=quiz_data.get(
            "question_types",
            ["multiple_choice", "definition", "true_false"],
        ),
    )


# grading now accepts A/B/C/D and also A/B for true/false
def grade_quiz(quiz_data: Dict, user_answers: List[str]) -> Dict:
    questions = quiz_data.get("questions", [])
    if len(user_answers) != len(questions):
        raise AthenaQuizError("Number of answers does not match number of questions.")

    results = []
    score = 0

    for question, user_answer in zip(questions, user_answers):
        correct = question["correct_answer"]
        cleaned_user_answer = str(user_answer).strip()

        if question.get("question_type") in {"multiple_choice", "definition"} and len(cleaned_user_answer) == 1:
            option_index = ord(cleaned_user_answer.upper()) - ord("A")
            options = question.get("options", [])
            if 0 <= option_index < len(options):
                cleaned_user_answer = options[option_index]

        elif question.get("question_type") == "true_false":
            lowered = cleaned_user_answer.lower()
            if lowered in {"a", "t", "true"}:
                cleaned_user_answer = "True"
            elif lowered in {"b", "f", "false"}:
                cleaned_user_answer = "False"

        is_correct = cleaned_user_answer.strip().lower() == correct.strip().lower()
        if is_correct:
            score += 1

        results.append(
            {
                "question_number": question["question_number"],
                "question_type": question.get("question_type", "unknown"),
                "question": question["question"],
                "user_answer": cleaned_user_answer,
                "correct_answer": correct,
                "is_correct": is_correct,
                "explanation": question.get("explanation", ""),
            }
        )

    percentage = round((score / len(questions)) * 100, 2) if questions else 0.0

    return {
        "topic": quiz_data.get("topic", "Unknown Topic"),
        "difficulty": quiz_data.get("difficulty", "unknown"),
        "score": score,
        "total": len(questions),
        "percentage": percentage,
        "results": results,
        "graded_at": datetime.now().isoformat(),
    }


def save_quiz_results(results_data: Dict, filename: Optional[str] = None) -> str:
    if filename is None:
        safe_topic = re.sub(r"[^a-zA-Z0-9_-]", "_", results_data.get("topic", "quiz"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{safe_topic}_results_{timestamp}.json"

    with open(filename, "w", encoding="utf-8") as file:
        json.dump(results_data, file, indent=4)

    return filename


def print_quiz_cli(quiz_data: Dict) -> None:
    print(f"\nAthena Quiz: {quiz_data['topic']}")
    print(f"Difficulty: {quiz_data['difficulty'].title()}")
    print("-" * 60)

    for question in quiz_data["questions"]:
        q_type = question.get("question_type", "unknown").replace("_", " ").title()
        print(f"\nQuestion {question['question_number']} ({q_type}): {question['question']}")
        for idx, option in enumerate(question["options"]):
            print(f"  {chr(65 + idx)}. {option}")


def run_cli_demo() -> None:
    try:
        topic = input("Enter a topic for your quiz: ").strip()
        difficulty = input("Choose difficulty (easy, medium, hard): ").strip().lower()
        num_questions = int(input("How many questions do you want? ").strip())

        quiz_data = generate_quiz_for_topic(topic, difficulty=difficulty, num_questions=num_questions)
        print_quiz_cli(quiz_data)

        user_answers = []
        print("\nYou can answer with A, B, C, or D.")
        print("For true/false, A = True and B = False.")
        for question in quiz_data["questions"]:
            answer = input(f"Answer for question {question['question_number']}: ").strip()
            user_answers.append(answer)

        graded_results = grade_quiz(quiz_data, user_answers)
        results_file = save_quiz_results(graded_results)

        print("\nQuiz complete.")
        print(f"Score: {graded_results['score']}/{graded_results['total']} ({graded_results['percentage']}%)")
        print(f"Results saved to: {results_file}")

        for result in graded_results["results"]:
            if result.get("explanation"):
                print(f"\nExplanation for Question {result['question_number']}: {result['explanation']}")

    except AthenaQuizError as error:
        print(f"Athena error: {error}")
    except ValueError:
        print("Please enter a valid number of questions.")


if __name__ == "__main__":
    run_cli_demo()