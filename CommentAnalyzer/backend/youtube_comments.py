import re
import time
import pandas as pd
import numpy as np
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from langdetect import detect, LangDetectException
import emoji
import nltk
from nltk.corpus import stopwords
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import NMF
from sentence_transformers import SentenceTransformer
from transformers import pipeline
from tqdm.auto import tqdm
import torch

nltk.download('stopwords', quiet=True)
nltk.download('wordnet', quiet=True)
nltk.download('omw-1.4', quiet=True)

def fetch_comments(video_id: str, api_key: str, max_comments=5000):
    
    youtube = build('youtube', 'v3', developerKey=api_key)
    comments = []
    next_page_token = None
    

    requests_needed = (max_comments // 100) + 1
    pbar = tqdm(total=max_comments, desc="Fetching comments")
    
    try:
        request_count = 0
        
        while len(comments) < max_comments and request_count < 100:  
            try:
                request = youtube.commentThreads().list(
                    part='snippet,replies',
                    videoId=video_id,
                    maxResults=100,
                    pageToken=next_page_token,
                    textFormat='plainText',
                    order='relevance'
                )
                
                resp = request.execute()
                request_count += 1
                
            except HttpError as e:
                error_reason = e.error_details[0]['reason'] if e.error_details else str(e)
                if 'quotaExceeded' in error_reason:
                    print(f"\n⚠️  API Quota Exceeded after {len(comments)} comments")
                    print("You've hit the daily limit. Try again tomorrow or use another API key.")
                elif 'commentsDisabled' in error_reason:
                    print(f"\n⚠️  Comments are disabled for this video")
                else:
                    print(f"\n❌ API Error: {error_reason}")
                break
            except Exception as e:
                print(f"\n❌ Unexpected error: {e}")
                break
            
            if not resp.get('items'):
                print(f"\n✓ No more comments available (fetched {len(comments)})")
                break
            
            
            for item in resp.get('items', []):
                if len(comments) >= max_comments:
                    break
                    
                top = item['snippet']['topLevelComment']['snippet']
                comments.append({
                    'commentId': top.get('id'),
                    'author': top.get('authorDisplayName'),
                    'text': top.get('textDisplay'),
                    'publishedAt': top.get('publishedAt'),
                    'likeCount': top.get('likeCount', 0),
                    'replyCount': item['snippet'].get('totalReplyCount', 0)
                })
                
                
                if item.get('replies'):
                    for r in item['replies'].get('comments', [])[:3]:  
                        if len(comments) >= max_comments:
                            break
                        rs = r['snippet']
                        comments.append({
                            'commentId': rs.get('id'),
                            'author': rs.get('authorDisplayName'),
                            'text': rs.get('textDisplay'),
                            'publishedAt': rs.get('publishedAt'),
                            'likeCount': rs.get('likeCount', 0),
                            'replyCount': 0
                        })
                
                pbar.update(1)
            
            
            if len(comments) >= max_comments:
                print(f"\n✓ Reached target of {max_comments} comments")
                break
            
            next_page_token = resp.get('nextPageToken')
            if not next_page_token:
                print(f"\n✓ Fetched all available comments ({len(comments)} total)")
                break
            
        
            time.sleep(0.15)
            
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
    finally:
        pbar.close()
    
    print(f"\n{'='*60}")
    print(f" FETCH SUMMARY: {len(comments)} comments from {request_count} API requests")
    print(f"{'='*60}")
    
    return pd.DataFrame(comments)



URL_RE = re.compile(r'https?://\S+|www\.\S+')
MENTION_RE = re.compile(r'@\w+')
HTML_RE = re.compile(r'<.*?>')
MULTI_SPACE = re.compile(r'\s+')
PUNCT_RE = re.compile(r'[^\w\s]')

def remove_emoji(text):
    return emoji.replace_emoji(text, replace='')


stop_words = set(stopwords.words('english'))
# Remove YouTube spam words that pollute topics
youtube_junk = [
    'video', 'watch', 'like', 'subscribe', 'channel', 'comment', 'please', 'thanks',
    'youtube', 'youtuber', 'zyada', 'yha', 'yes', 'content', 'creator', 'viewers',
    'first', 'second', 'third', 'pin', 'heart', 'bro', 'guys', 'everyone', 'one',
    'get', 'make', 'want', 'would', 'could', 'really', 'much', 'thing', 'things'
]
stop_words.update(youtube_junk)

lemmatizer = WordNetLemmatizer()

def clean_text(text: str, remove_emojis=True, remove_urls=True, lower=True):
    if not isinstance(text, str) or len(text.strip()) == 0:
        return ''
    
    txt = text
    if remove_urls:
        txt = URL_RE.sub('', txt)
    txt = HTML_RE.sub('', txt)
    txt = MENTION_RE.sub('', txt)
    if remove_emojis:
        txt = remove_emoji(txt)
    if lower:
        txt = txt.lower()
    txt = PUNCT_RE.sub(' ', txt)
    txt = MULTI_SPACE.sub(' ', txt).strip()
    
    return txt

def is_valid_comment(text: str, min_length=5, max_length=2000):
    if not text or len(text) < min_length or len(text) > max_length:
        return False
    
    words = text.split()
    if len(words) > 0:
        unique_ratio = len(set(words)) / len(words)
        if unique_ratio < 0.25:
            return False
    
    alpha_chars = sum(c.isalpha() or c.isspace() for c in text)
    if len(text) > 0 and alpha_chars / len(text) < 0.5:
        return False
    
    if re.match(r'^(.)\1+$', text.replace(' ', '')):
        return False
    
    return True

def preprocess_text(text: str):
    if not isinstance(text, str):
        return '', 'unknown'
    
    if not is_valid_comment(text):
        return '', 'invalid'
    
    cleaned = clean_text(text)
    
    lang = 'unknown'
    try:
        if len(text) > 5:
            lang = detect(text)
    except LangDetectException:
        lang = 'unknown'
    
    
    tokens = []
    for tok in cleaned.split():
        if len(tok) > 2 and tok not in stop_words and tok.isalpha():
            lemma = lemmatizer.lemmatize(tok)
            tokens.append(lemma)
    
    if len(tokens) < 2:
        return '', 'invalid'
    
    return ' '.join(tokens), lang


def batch_sentiment_analysis(texts, batch_size=32):
    sentiments = []
    device = 0 if torch.cuda.is_available() else -1
    
    sentiment_pipe = pipeline(
        "sentiment-analysis", 
        model="cardiffnlp/twitter-roberta-base-sentiment-latest",
        device=device,
        truncation=True,
        max_length=512
    )
    
    for i in tqdm(range(0, len(texts), batch_size), desc="Analyzing sentiment"):
        batch = texts[i:i+batch_size]
        try:
            results = sentiment_pipe(batch)
            sentiments.extend(results)
        except Exception as e:
            print(f"\nError in sentiment batch {i}: {e}")
            sentiments.extend([{'label': 'neutral', 'score': 0.5}] * len(batch))
    
    return sentiments


def extract_better_topics(df_en, n_topics=6):
    

    print("Extracting meaningful topics...")
    

    tfidf = TfidfVectorizer(
        max_df=0.75,  
        min_df=5,     
        ngram_range=(1, 3),  
        max_features=2000,
        stop_words='english'
    )
    
    X = tfidf.fit_transform(df_en['cleaned'].fillna(''))
    
    if X.shape[0] < 20:
        return ["Insufficient data for topic extraction"]
    
    
    n_topics = min(n_topics, max(3, len(df_en) // 100))
    
    nmf = NMF(
        n_components=n_topics,
        random_state=42,
        max_iter=500,
        alpha_W=0.1,
        alpha_H=0.1,
        l1_ratio=0.5
    )
    
    W = nmf.fit_transform(X)
    H = nmf.components_
    
    feature_names = tfidf.get_feature_names_out()
    topics = []
    
    for topic_idx in range(n_topics):
        
        top_indices = H[topic_idx].argsort()[-20:][::-1]
        
        
        topic_terms = []
        seen = set()
        
        for idx in top_indices:
            term = feature_names[idx]
            
            
            if term in seen or len(term) < 3:
                continue
            
            
            if ' ' in term:
                topic_terms.append(term)
                seen.add(term)
                
                for word in term.split():
                    seen.add(word)
            elif term not in seen:
                topic_terms.append(term)
                seen.add(term)
            
            if len(topic_terms) >= 4:
                break
        
        if topic_terms:
            
            topic_label = ", ".join(topic_terms[:4])
            topics.append(topic_label)
    
    
    unique_topics = []
    for topic in topics:
        is_duplicate = False
        for existing in unique_topics:
            
            topic_words = set(topic.lower().split())
            existing_words = set(existing.lower().split())
            overlap = len(topic_words & existing_words) / max(len(topic_words), len(existing_words))
            if overlap > 0.6:
                is_duplicate = True
                break
        if not is_duplicate:
            unique_topics.append(topic)
    
    return unique_topics if unique_topics else ["Topics could not be clearly identified"]


def analyze(df: pd.DataFrame, min_comment_length=5):
    if df.empty:
        return df, []
    
    print(f"\n{'='*60}")
    print("🔍 Starting Analysis...")
    print(f"{'='*60}")
    
    
    df['cleaned'], df['lang'] = zip(*df['text'].map(preprocess_text))
    
    df_en = df[
        (df['lang'] == 'en') & 
        (df['cleaned'].str.len() > 0) &
        (df['text'].str.len() >= min_comment_length)
    ].copy()
    
    filtered_out = len(df) - len(df_en)
    print(f"📊 Found {len(df_en)} valid English comments ({filtered_out} filtered out)")
    
    if df_en.empty or len(df_en) < 10:
        return df_en, ["Not enough valid English comments found."]
    

    print(f"\n💭 Analyzing sentiment for {len(df_en)} comments...")
    sentiments = batch_sentiment_analysis(df_en['cleaned'].tolist())
    
    df_en['sentiment_label'] = [r['label'] for r in sentiments]
    df_en['sentiment_score'] = [r.get('score', 0.5) for r in sentiments]
    
    
    label_map = {
        'LABEL_0': 'negative',
        'LABEL_1': 'neutral', 
        'LABEL_2': 'positive',
        'positive': 'positive',
        'negative': 'negative',
        'neutral': 'neutral'
    }
    df_en['sentiment_label'] = df_en['sentiment_label'].map(lambda x: label_map.get(x, x.lower()))
    
    print("\n🧠 Generating embeddings...")
    embed_model = SentenceTransformer('all-MiniLM-L6-v2')
    df_en['embedding'] = list(
        embed_model.encode(
            df_en['cleaned'].tolist(), 
            show_progress_bar=True,
            batch_size=64
        )
    )
    
    topics = extract_better_topics(df_en)
    
    print(f"\n{'='*60}")
    print(f"✅ Analysis Complete: {len(df_en)} comments processed")
    print(f"{'='*60}\n")
    
    return df_en, topics


if __name__ == "__main__":
    API_KEY = "AIzaSyAhVg7skNeI5PThG3kuNTGAyCXoSGGQp4U"
    VIDEO_ID = "3JZ_D3ELwOQ"
    
    print("Fetching comments...")
    df = fetch_comments(VIDEO_ID, API_KEY, max_comments=5000)
    print(f"Fetched {len(df)} comments")
    
    print("\nAnalyzing comments...")
    analyzed_df, topics = analyze(df)
    
    if not analyzed_df.empty:
        analyzed_df.to_csv("youtube_comments_analysis.csv", index=False)
        print("\nSaved youtube_comments_analysis.csv")
        
        print("\n=== ANALYSIS RESULTS ===")
        print(f"Total analyzed: {len(analyzed_df)} comments")
        
        print("\nSentiment Distribution:")
        print(analyzed_df['sentiment_label'].value_counts())
        
        print("\nTop Topics:")
        for i, t in enumerate(topics, 1):
            print(f"{i}. {t}")
    else:
        print("No valid comments to analyze.")