# SmartTube – AI YouTube Enhancement Extension

## Description

A browser extension that enhances YouTube experience using AI-powered features such as sponsor segment skipping and comment sentiment analysis.

## Features

* Automatic detection and skipping of in-video sponsored segments (non-ad content)
* Comment analysis system to extract and process relevant comments
* Sentiment analysis of comments using AI
* Displays:

  * Percentage of positive vs negative comments
  * Top-liked comments
* Integrated UI button for real-time analysis on YouTube pages

## Tech Stack

* JavaScript
* NLP (Lemmatization)
* RoBERTa (Twitter-based BERT model)
* Browser APIs (DOM manipulation)

## How It Works

The extension interacts with YouTube’s DOM to identify video segments and user comments.
Comments are preprocessed using NLP techniques such as lemmatization and then passed to a RoBERTa model for sentiment classification.
Results are aggregated and displayed directly on the YouTube interface.

## Installation

1. Clone the repository
2. Go to browser extensions settings
3. Enable Developer Mode
4. Click "Load Unpacked"
5. Select the project folder

## Future Improvements

* Improve sponsor detection accuracy
* Add real-time sentiment updates
* Enhance UI/UX
