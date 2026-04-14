# Athena
By: Ashley Chin, Kimberly Maynard

Athena is a **full-stack AI-powered quiz generation web application** that creates interactive quizzes based on any topic the user enters.

Instead of using static or pre-written questions, Athena dynamically pulls information from Wikipedia and uses AI to generate **natural, high-quality questions**, explanations, and adaptive difficulty.

---

## Features

- **Topic-based quiz generation** (e.g., *AI*, *Machine Learning*, *Organic Chemistry*)
- **AI-enhanced question generation** (not just basic scraping)
- **Difficulty levels**
  - Easy
  - Medium
  - Hard
- **Multiple question types**
  - Multiple Choice (A, B, C, D)
  - True / False (clickable like A/B)
  - Definition-based questions
- **Timer system** (auto-submit when time runs out)
- **Progress bar** (fills as you answer)
- **Answer explanations** shown after submission
- **Retry / regenerate quiz functionality**
- **Full-stack architecture**
  - Python (Flask backend)
  - HTML / CSS / JavaScript frontend

---

## Tech Stack

### Frontend
- HTML5  
- CSS3  
- Vanilla JavaScript  

### Backend
- Python 3  
- Flask  
- NLTK (text processing)  
- Scikit-learn (TF-IDF keyword extraction)  
- Requests (Wikipedia API calls)  

### APIs
- Wikipedia API (content source)  
- OpenAI API (AI-generated questions & explanations)  

---

## Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/kimmaynard/athena.git
cd athena
```

### 2. Create Virtual Environment

#### Mac / Linux

```bash
python3 -m venv venv
source venv/bin/activate
```

#### Windows

```bash
python -m venv venv
venv\Scripts\activate
```


### 3. Install Dependencies

```bash
pip install flask nltk requests scikit-learn openai
```


### 4. Set OpenAI API Key

#### Mac / Linux

```bash
export OPENAI_API_KEY="your_api_key_here"
```

#### Windows (PowerShell)

```bash
setx OPENAI_API_KEY "your_api_key_here"
```


### 5. Run Backend Server

```bash
python app.py
```

You should see:

```
Running on http://127.0.0.1:5000/
```


### 6. Run Frontend

```bash
open index.html
```

Or use **Live Server in VS Code**.

---

## 🎮 How to Use

1. Enter a topic (e.g., **"AI"**)  
2. Select difficulty (**Easy / Medium / Hard**)  
3. Choose number of questions (**3, 5, 10**)  
4. Click **Start Quiz**  
5. Answer questions  
6. Click **Submit**  
7. View results + explanations  

---

## 📁 Project Structure

```bash
athena/
│
├── app.py                  # Flask API server
├── athena_quiz_engine.py   # Core quiz logic
│
├── index.html              # Frontend UI
├── style.css               # Styling
├── script.js               # Frontend logic
│
├── venv/                   # Virtual environment
└── README.md
```

---

## Future Improvements

- User accounts  
- Quiz history  
- Leaderboard  
- Better AI explanations  
- Mobile optimization  

---

## Project Responsibilities

### **Ashley Chin**

- Implemented and integrated **frontend–backend communication using Flask API endpoints**
  - Connected to `/api/quiz` for quiz generation
  - Connected to `/api/grade` for grading and feedback
- Designed and managed the **end-to-end quiz workflow**:
  - User input → API request → rendering → submission → results
- Structured and handled **JSON-based API requests and responses**
- Built dynamic **state management system** for answers, progress tracking, and submission state
- Implemented **timer system with auto-submit functionality**
- Developed the **interactive quiz interface**, including:
  - Dynamic question rendering
  - Answer selection handling
  - Progress bar updates
- Debugged and resolved **integration and functionality issues** across frontend and API
- Designed and refined the **user interface (UI/UX)** for usability and consistency
- Authored and structured the **project README documentation**, including setup and usage instructions

### **Kimberly Maynard**

- Developed the **backend quiz generation engine** using Python and Flask
- Implemented and structured **API endpoints**:
  - `/api/quiz` for quiz generation
  - `/api/grade` for grading logic
- Integrated **Wikipedia API** for dynamic content retrieval
- Implemented **text processing pipeline** using NLTK for sentence extraction and filtering
- Applied **TF-IDF (Scikit-learn)** for keyword extraction and ranking
- Built **distractor generation logic** for realistic answer options
- Implemented **grading system** with scoring and detailed results output
- Created the **final project report and PowerPoint presentation** documenting system design and implementation

---

## License

This project is for educational use.

---

## Final Thoughts

Athena transforms passive learning into an **interactive AI-powered experience**.

Users don’t just memorize — they engage, understand, and learn smarter.

## Presentation Demo Youtube Link

https://youtu.be/0k9ZWB_4OvM
