from flask import Flask, jsonify, request
from flask_cors import CORS
import youtube_comments

app = Flask(__name__)
CORS(app)

API_KEY = "AIzaSyAhVg7skNeI5PThG3kuNTGAyCXoSGGQp4U"

@app.route('/analyze/<video_id>')
def analyze_video_comments(video_id):
    if not API_KEY or API_KEY == "YOUR_YOUTUBE_API_KEY_HERE":
        return jsonify({"error": "YouTube API key is not set in server.py"}), 500
    
    
    max_comments = request.args.get('max_comments', default=5000, type=int)
    max_comments = min(max_comments, 10000)  
    
    try:
        print(f"\n{'='*70}")
        print(f"🎬 Analyzing Video: {video_id}")
        print(f"🎯 Target: {max_comments} comments")
        print(f"{'='*70}\n")
        
        df = youtube_comments.fetch_comments(video_id, API_KEY, max_comments=max_comments)
        
        if df.empty:
            return jsonify({
                "error": "No comments found. Comments may be disabled or API failed."
            }), 404

        print(f"\n✓ Fetched {len(df)} raw comments")
        
        analyzed_df, topics = youtube_comments.analyze(df)

        if analyzed_df.empty or len(analyzed_df) < 5:
            return jsonify({
                "commentCount": 0,
                "totalFetched": len(df),
                "sentiment": {"positive": 0, "negative": 0, "neutral": 0},
                "topics": [f"Only {len(analyzed_df)} valid English comments found. Most comments may be in other languages or too short."],
                "topPositiveComment": "N/A",
                "topNegativeComment": "N/A",
                "avgSentimentScore": 0,
                "warning": f"Fetched {len(df)} comments but only {len(analyzed_df)} were analyzable."
            })

        
        sentiment_counts = analyzed_df['sentiment_label'].value_counts().to_dict()
        sentiment_dict = {
            "positive": sentiment_counts.get('positive', 0),
            "negative": sentiment_counts.get('negative', 0),
            "neutral": sentiment_counts.get('neutral', 0)
        }
        
    
        positive_comments = analyzed_df[
            analyzed_df['sentiment_label'] == 'positive'
        ].nlargest(5, 'sentiment_score')
        
        negative_comments = analyzed_df[
            analyzed_df['sentiment_label'] == 'negative'
        ].nsmallest(5, 'sentiment_score')
        
        # Best positive
        if not positive_comments.empty:
            top_positive = positive_comments.iloc[0]['text']
            if len(top_positive) < 15 and len(positive_comments) > 1:
                top_positive = positive_comments.iloc[1]['text']
        else:
            top_positive = "No clearly positive comments found."
        
        # Best negative
        if not negative_comments.empty:
            top_negative = negative_comments.iloc[0]['text']
            if len(top_negative) < 15 and len(negative_comments) > 1:
                top_negative = negative_comments.iloc[1]['text']
        else:
            top_negative = "No clearly negative comments found."
        
        # Stats
        avg_sentiment = float(analyzed_df['sentiment_score'].mean())
        top_liked = analyzed_df.nlargest(1, 'likeCount').iloc[0]
        analysis_rate = (len(analyzed_df) / len(df)) * 100
        
        results = {
            "commentCount": len(analyzed_df),
            "totalFetched": len(df),
            "analysisRate": round(analysis_rate, 1),
            "sentiment": sentiment_dict,
            "topics": topics if topics else ["Topics could not be identified"],
            "topPositiveComment": top_positive,
            "topNegativeComment": top_negative,
            "avgSentimentScore": round(avg_sentiment, 3),
            "mostLikedComment": {
                "text": top_liked['text'],
                "likes": int(top_liked['likeCount']),
                "sentiment": top_liked['sentiment_label']
            },
            "sentimentBreakdown": {
                "positivePercent": round((sentiment_dict['positive'] / len(analyzed_df)) * 100, 1),
                "negativePercent": round((sentiment_dict['negative'] / len(analyzed_df)) * 100, 1),
                "neutralPercent": round((sentiment_dict['neutral'] / len(analyzed_df)) * 100, 1)
            }
        }
        
        print(f"\n{'='*70}")
        print(f"✅ SUCCESS: {len(analyzed_df)}/{len(df)} comments analyzed ({analysis_rate:.1f}%)")
        print(f"{'='*70}\n")
        
        return jsonify(results)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({
        "status": "running",
        "message": "YouTube Comment Analyzer API is active",
        "defaultCommentLimit": 5000
    })

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🚀 YouTube Comment Analyzer Server")
    print("="*70)
    print("📍 Server: http://127.0.0.1:5000")
    print("📊 Default limit: 5000 comments")
    print("⚡ Ready to analyze!")
    print("="*70 + "\n")
    app.run(debug=True, port=5000, threaded=True)