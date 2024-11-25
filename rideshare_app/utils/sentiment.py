import requests
import statistics
import re
from datetime import datetime, timedelta
from typing import List, Dict, Union
from utils.db import db
from config import Config  # Import the config

class SentimentAnalyzer:
    def __init__(self, api_key):
        """
        Initialize sentiment analyzer with API key from config
        """
        self.api_url = "https://api-inference.huggingface.co/models/lxyuan/distilbert-base-multilingual-cased-sentiments-student"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        
    def _basic_sentiment_analysis(self, text: str) -> float:
        """
        Fallback method for basic sentiment analysis when API fails
        """
        text = text.lower()
        
        positive_words = {'good', 'great', 'excellent', 'amazing', 'wonderful', 'fantastic',
                         'helpful', 'friendly', 'nice', 'best', 'happy', 'satisfied', 'thank',
                         'thanks', 'awesome', 'perfect', 'comfortable', 'clean', 'safe'}
        
        negative_words = {'bad', 'poor', 'terrible', 'horrible', 'awful', 'worst',
                         'rude', 'unhelpful', 'late', 'dirty', 'unsafe', 'uncomfortable',
                         'slow', 'dangerous', 'unprofessional', 'disappointed'}
        
        words = set(re.findall(r'\w+', text))
        
        positive_count = len(words.intersection(positive_words))
        negative_count = len(words.intersection(negative_words))
        
        if positive_count == 0 and negative_count == 0:
            return 3.0
        
        total_matches = positive_count + negative_count
        sentiment_ratio = (positive_count - negative_count) / total_matches
        
        score = 3 + (sentiment_ratio * 2)
        return min(5.0, max(1.0, score))

    def analyze_sentiment(self, text: str) -> float:
        """
        Analyze text sentiment using HuggingFace API with fallback
        """
        if not text or not isinstance(text, str) or not text.strip():
            return 3.0
            
        # First try the API
        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={"inputs": text},
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                
                if isinstance(result, list) and result:
                    sentiment_data = result[0]
                    score = 0
                    for item in sentiment_data:
                        if item['label'] == 'positive':
                            score += 5 * item['score']
                        elif item['label'] == 'neutral':
                            score += 3 * item['score']
                        else:  # negative
                            score += 1 * item['score']
                    return min(5.0, max(1.0, score))
            
        except Exception as e:
            print(f"API Error: {str(e)}, falling back to basic analysis")
        
        # If API fails, use basic sentiment analysis
        return self._basic_sentiment_analysis(text)

    def get_rating_stats(self, feedbacks: List, window_days: int = 30) -> Dict[str, Union[float, int, Dict]]:
        """
        Calculate detailed rating statistics
        """
        default_stats = {
            'average': 0.0,
            'total_ratings': 0,
            'rating_distribution': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0},
            'recent_trend': 0.0,
            'recent_average': 0.0,
            'weekly_averages': [],
            'response_rate': 0.0,
            'confidence_score': 0.0
        }
        
        if not feedbacks:
            return default_stats
            
        try:
            distribution = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            scores = []
            recent_scores = []
            weekly_scores = {}
            
            cutoff_date = datetime.now() - timedelta(days=window_days)
            
            for feedback in feedbacks:
                if not feedback.comment:
                    continue
                    
                score = self.analyze_sentiment(feedback.comment)
                rounded_score = round(score)
                distribution[rounded_score] += 1
                scores.append(score)
                
                if feedback.created_at >= cutoff_date:
                    recent_scores.append(score)
                
                week_num = feedback.created_at.isocalendar()[1]
                if week_num not in weekly_scores:
                    weekly_scores[week_num] = []
                weekly_scores[week_num].append(score)
            
            if not scores:
                return default_stats

            total_ratings = len(scores)
            confidence_factor = min(1.0, total_ratings / 10)
            
            raw_average = statistics.mean(scores)
            weighted_average = (raw_average * confidence_factor) + (3.0 * (1 - confidence_factor))
            
            recent_average = statistics.mean(recent_scores) if recent_scores else weighted_average
            recent_trend = recent_average - weighted_average
            
            weekly_averages = [
                {
                    'week': week,
                    'average': round(statistics.mean(scores), 1),
                    'count': len(scores)
                }
                for week, scores in sorted(weekly_scores.items())
            ]
            
            total_rides = len(feedbacks)
            response_rate = (total_ratings / total_rides * 100) if total_rides > 0 else 0
            
            return {
                'average': round(weighted_average, 1),
                'total_ratings': total_ratings,
                'rating_distribution': distribution,
                'recent_trend': round(recent_trend, 1),
                'recent_average': round(recent_average, 1),
                'weekly_averages': weekly_averages[-12:],
                'response_rate': round(response_rate, 1),
                'confidence_score': round(confidence_factor * 100, 1)
            }
            
        except Exception as e:
            print(f"Error calculating rating stats: {str(e)}")
            return default_stats

    def update_driver_rating(self, driver, feedbacks: List) -> Dict[str, Union[float, int, Dict]]:
        """
        Calculate rating stats and update driver rating
        """
        rating_stats = self.get_rating_stats(feedbacks)
        
        if driver.update_rating(rating_stats):
            try:
                db.session.commit()
            except Exception as e:
                db.session.rollback()
                print(f"Error updating driver rating: {str(e)}")
        
        return rating_stats