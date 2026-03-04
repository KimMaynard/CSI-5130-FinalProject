# Athena
By: Kimberly Maynard + Ashley Chin

Athena is a Python-based application that automatically creates quiz questions from educational text. The goal of this project is to explore how Natural Language Processing (NLP) and basic AI techniques can be used to convert raw text into interactive learning material.

Instead of manually writing quizzes, users will eventually be able to enter a topic, and the system will automatically gather information and generate a quiz from that knowledge.

This project is designed as an introductory AI application that demonstrates practical uses of:
	•	Natural Language Processing
	•	Keyword extraction
	•	Automated question generation
	•	Educational AI tools

## Project Goals

The purpose of this project is to demonstrate how basic artificial intelligence techniques can assist with educational content creation.

Key goals include:
	•	Exploring practical applications of **Natural Language Processing (NLP)**
	•	Automating quiz generation from informational text
	•	Integrating external knowledge sources
	•	Building a simple but functional **AI-powered learning tool**

## Current Implementation (Temporary)

At the moment, the system works using a manual text input approach.

Users paste a block of text into the program, and the application generates quiz questions based on that content.

### Current Workflow
	1.	User provides text input
	•	Example: lecture notes, textbook paragraphs, article excerpts
	2.	Text preprocessing
	•	Removes punctuation
	•	Removes stopwords (common words like the, is, and)
	3.	Keyword extraction
	•	Uses TF-IDF (Term Frequency–Inverse Document Frequency) to identify important terms in the text
	4.	Question generation
	•	Sentences containing important keywords are converted into fill-in-the-blank questions
	5.	Multiple choice creation
	•	Uses WordNet from the NLTK library to generate distractor answers
	6.	Quiz output
	•	Displays a multiple-choice quiz along with an answer key

Note:
This text-input system is temporary and mainly used for development and testing purposes.

## Planned Feature: Wikipedia API Integration

In the next stage of development, the application will integrate the Wikipedia API to automatically gather information about a topic.

Instead of pasting text manually, users will be able to:

Enter a topic → retrieve information from Wikipedia → generate a quiz automatically.

### Planned Workflow
	1.	User enters a topic
	•	Example: "Cryptography" or "Machine Learning"
	2.	Wikipedia API request
	•	The application retrieves article summaries or sections related to the topic
	3.	Content extraction
	•	Relevant text is collected and cleaned for processing
	4.	AI text analysis
	•	NLP techniques identify key concepts and important terms
	5.	Automatic quiz generation
	•	Questions are generated from the extracted knowledge
	6.	Quiz output
	•	Displays a multiple-choice quiz based on real informational sources

This approach allows the system to generate quizzes from real-world knowledge sources instead of manually provided text.

## Features

### Current Features
	•	Automatic keyword extraction using TF-IDF
	•	Sentence-based fill-in-the-blank questions
	•	Multiple-choice quiz generation
	•	Distractor answers generated using WordNet
	•	Adjustable number of quiz questions
	•	Basic difficulty selection

### Planned Features
	•	Wikipedia API integration
	•	Automatic quiz generation from topic search
	•	Multiple question types
	•	True/False
	•	Definition-based questions
	•	Improved distractor quality
	•	Styled quiz interface (HTML/CSS)
	•	Export quizzes to files (PDF or text)

## Summary

The AI Quiz Generator demonstrates how artificial intelligence techniques can be applied to automate the creation of educational quizzes. By combining NLP, keyword extraction, and external data sources, the system aims to transform raw informational text into structured learning assessments.

While the current version uses manually provided text, the future implementation will rely on the Wikipedia API to dynamically generate quizzes from real-world knowledg
