import tempfile
from gtts import gTTS
import pygame
import requests
import requests
import feedparser
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import webbrowser
from datetime import datetime, timedelta
import threading
import time
from urllib.parse import urlparse
import re
from collections import defaultdict
import json
import os
from PIL import Image, ImageTk
from io import BytesIO
from openai import OpenAI
from langdetect import detect
from gtts.lang import tts_langs
from deep_translator import GoogleTranslator
from gtts import gTTS
import pygame
import tempfile
import time
from json import JSONEncoder

class DateTimeEncoder(JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

# Initialize OpenRouter API client
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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",
)

class WeatherService:
    def __init__(self):
        self.weather_data = None
        self.location_data = None
        
    def get_location_by_ip(self):
        """Get location based on IP address"""
        try:
            response = requests.get('http://ip-api.com/json/', timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data['status'] == 'success':
                    self.location_data = {
                        'city': data.get('city', 'Unknown'),
                        'country': data.get('country', 'Unknown'),
                        'lat': data.get('lat', 0),
                        'lon': data.get('lon', 0)
                    }
                    return True
        except:
            pass
        return False
    
    def get_weather(self):
        """Get weather data using OpenWeatherMap API (free tier)"""
        if not self.location_data:
            if not self.get_location_by_ip():
                return None
        
        try:
            city = self.location_data['city']
            api_key = '7a5218c60230d67529d572c12887acd6'
            url = f'https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric'
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                current = data.get('main', {})
                weather = data.get('weather', [{}])[0]
                
                self.weather_data = {
                    'temperature': current.get('temp', 0),
                    'humidity': current.get('humidity', 0),
                    'wind_speed': data.get('wind', {}).get('speed', 0),
                    'weather_code': weather.get('id', 0),
                    'weather_description': weather.get('description', ''),
                    'is_day': 1 if data.get('dt') < data.get('sys', {}).get('sunset', 0) else 0,
                    'city': city,
                    'country': self.location_data['country']
                }
                return self.weather_data
        except Exception as e:
            print(f"Weather fetch error: {e}")
        return None
    
    def get_weather_emoji(self, weather_code, is_day):
        """Get weather emoji based on weather code"""
        weather_emojis = {
            0: "☀️" if is_day else "🌙",
            1: "🌤️" if is_day else "🌙",
            2: "⛅",
            3: "☁️",
            45: "🌫️",
            48: "🌫️",
            51: "🌦️",
            53: "🌦️",
            55: "🌧️",
            61: "🌧️",
            63: "🌧️",
            65: "🌧️",
            71: "🌨️",
            73: "🌨️",
            75: "❄️",
            95: "⛈️",
        }
        return weather_emojis.get(weather_code, "🌤️")

class NewsAggregator:
    def __init__(self):
        self.news_sources = {
            'BBC News': 'http://feeds.bbci.co.uk/news/rss.xml',
            'CNN': 'http://rss.cnn.com/rss/edition.rss',
            'Reuters': 'https://www.reuters.com/rssFeed/worldNews',
            'Associated Press': 'https://feeds.apnews.com/rss/apf-topnews',
            'Al Jazeera': 'https://www.aljazeera.com/xml/rss/all.xml',
            'NPR': 'https://feeds.npr.org/1001/rss.xml',
            'The Guardian': 'https://www.theguardian.com/world/rss',
            'ABC News': 'https://feeds.abcnews.com/abcnews/topstories',
            'CBS News': 'https://www.cbsnews.com/latest/rss/main',
            'Fox News': 'http://feeds.foxnews.com/foxnews/latest',
            'The Hindu': 'https://www.thehindu.com/news/national/feeder/default.rss',
            'Hindustan Times': 'https://www.hindustantimes.com/rss/topnews/rssfeed.xml',
            'India Today': 'https://www.indiatoday.in/rss/home',
            'Times of India': 'https://timesofindia.indiatimes.com/rssfeeds/-2128936835.cms',
            'NDTV': 'https://feeds.feedburner.com/ndtvnews-top-stories'
        }
        
        self.categories = {
            'World': ['world', 'international', 'global', 'foreign'],
            'Politics': ['politics', 'government', 'election', 'policy', 'congress', 'senate'],
            'Technology': ['technology', 'tech', 'software', 'ai', 'artificial intelligence', 'computer'],
            'Business': ['business', 'economy', 'finance', 'market', 'stock', 'trade'],
            'Sports': ['sports', 'football', 'basketball', 'baseball', 'soccer', 'tennis'],
            'Health': ['health', 'medical', 'disease', 'covid', 'medicine', 'hospital'],
            'Science': ['science', 'research', 'study', 'discovery', 'space', 'climate'],
            'Entertainment': ['entertainment', 'celebrity', 'movie', 'music', 'hollywood', 'film'],
            'India': ['india', 'modi', 'parliament', 'delhi', 'bjp', 'congress', 'lok sabha', 'rajya sabha']
        }
        
        self.articles = []
        self.filtered_articles = []
        self.favorites = self.load_favorites()
        self.unique_article_ids = set()
    
    def load_favorites(self):
        """Load saved favorite articles with proper datetime conversion"""
        try:
            if os.path.exists('favorites.json'):
                with open('favorites.json', 'r') as f:
                    loaded = json.load(f)
                    # Convert ISO strings back to datetime objects
                    for fav in loaded:
                        if isinstance(fav['published'], str):  # Only convert if it's a string
                            fav['published'] = datetime.fromisoformat(fav['published'])
                    return loaded
        except Exception as e:
            print(f"Error loading favorites: {e}")
        return []
        
    def save_favorites(self):
        """Save favorite articles using custom JSON encoder"""
        try:
            with open('favorites.json', 'w') as f:
                json.dump(self.favorites, f, indent=2, cls=DateTimeEncoder)
        except Exception as e:
            print(f"Error saving favorites: {e}")
        
    def fetch_news(self, progress_callback=None):
        """Fetch news from all sources, filtering for English content only"""
        self.articles = []
        self.unique_article_ids = set()
        total_sources = len(self.news_sources)
        
        for i, (source, url) in enumerate(self.news_sources.items()):
            try:
                if progress_callback:
                    progress_callback(f"Fetching from {source}...", i, total_sources)
                
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    article_link = entry.link if hasattr(entry, 'link') and entry.link else None
                    article_id = article_link if article_link else f"{source}_{entry.title if hasattr(entry, 'title') else ''}_{entry.published if hasattr(entry, 'published') else ''}"

                    if article_id and article_id not in self.unique_article_ids:
                        # Get raw content
                        raw_title = entry.title if hasattr(entry, 'title') else 'No Title'
                        raw_summary = entry.summary if hasattr(entry, 'summary') else entry.description if hasattr(entry, 'description') else ''
                        
                        # Skip non-English content
                        if not self.is_english_content(raw_title + ' ' + raw_summary):
                            continue
                            
                        article = {
                            'title': raw_title,
                            'summary': raw_summary,
                            'link': article_link if article_link else '',
                            'published': self.parse_date(entry.published if hasattr(entry, 'published') else ''),
                            'source': source,
                            'category': self.categorize_article(raw_title + ' ' + raw_summary),
                            'id': article_id,
                            'language': 'en'  # Mark as English since we filtered
                        }
                        self.articles.append(article)
                        self.unique_article_ids.add(article_id)
                        
            except Exception as e:
                print(f"Error fetching from {source}: {e}")
                continue
        
        self.articles.sort(key=lambda x: x['published'], reverse=True)
        self.filtered_articles = self.articles.copy()

    def is_english_content(self, text):
        """Determine if content is English with simple heuristics"""
        if not text:
            return False
        
        text = text.lower()
        
        # Simple keyword check for common non-English indicators
        non_english_indicators = [
            # Hindi
            'हिंदी', 'भारत', 'की', 'से', 'के', 'में',
            # Other common Indian languages
            'தமிழ்', 'తెలుగు', 'ಕನ್ನಡ', 'മലയാളം', 'বাংলা'
        ]
        
        if any(indicator in text for indicator in non_english_indicators):
            return False
        
        # Check character distribution (English is mostly ASCII)
        non_ascii = sum(1 for char in text if ord(char) > 127)
        if non_ascii / len(text) > 0.1:  # More than 10% non-ASCII
            return False
        
        # Check for common English words
        english_indicators = [
            'the', 'and', 'for', 'are', 'this', 'that',
            'with', 'have', 'from', 'they', 'would'
        ]
        
        english_word_count = sum(1 for word in english_indicators if word in text)
        return english_word_count >= 3  # At least 3 common English words

    def parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return datetime.now()
        
        try:
            formats = [
                '%a, %d %b %Y %H:%M:%S %Z',
                '%a, %d %b %Y %H:%M:%S %z',
                '%Y-%m-%dT%H:%M:%SZ',
                '%Y-%m-%dT%H:%M:%S%z',
                '%a, %d %b %Y %H:%M:%S GMT',
                '%a, %d %b %Y %H:%M:%S UTC'
            ]
            
            for fmt in formats:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    if parsed_date.tzinfo is not None:
                        parsed_date = parsed_date.replace(tzinfo=None)
                    return parsed_date
                except:
                    continue
            
            try:
                parsed_time = feedparser._parse_date(date_str)
                if parsed_time:
                    return datetime.fromtimestamp(time.mktime(parsed_time))
            except:
                pass
                    
            return datetime.now()
        except:
            return datetime.now()
    
    def categorize_article(self, text):
        """Categorize article based on keywords"""
        text_lower = text.lower()
        
        for category, keywords in self.categories.items():
            for keyword in keywords:
                if keyword in text_lower:
                    return category
        return 'General'
    
    def search_articles(self, query):
        """Search articles by query"""
        if not query:
            self.filtered_articles = self.articles.copy()
            return
        
        query_lower = query.lower()
        self.filtered_articles = [
            article for article in self.articles
            if query_lower in article['title'].lower() or 
               query_lower in article['summary'].lower() or
               query_lower in article['source'].lower()
        ]
    
    def filter_by_category(self, category):
        """Filter articles by category"""
        if category == 'All':
            self.filtered_articles = self.articles.copy()
        else:
            self.filtered_articles = [
                article for article in self.articles
                if article['category'] == category
            ]
    
    def filter_by_source(self, source):
        """Filter articles by source"""
        if source == 'All':
            self.filtered_articles = self.articles.copy()
        else:
            self.filtered_articles = [
                article for article in self.articles
                if article['source'] == source
            ]
    
    def add_to_favorites(self, article):
        """Add article to favorites"""
        if article['id'] not in [fav['id'] for fav in self.favorites]:
            self.favorites.append(article)
            self.save_favorites()
            return True
        return False
    
    def remove_from_favorites(self, article_id):
        """Remove article from favorites"""
        self.favorites = [fav for fav in self.favorites if fav['id'] != article_id]
        self.save_favorites()

class NewsApp:
    def __init__(self, root):
        self.root = root
        self.root.title("🗞️ Advanced News Hub")
        self.root.geometry("1350x650+0+0")
        self.root.iconbitmap('newspaper.ico')
        self.root.configure(bg='#f8f9fa')
        
        self.news_aggregator = NewsAggregator()
        self.weather_service = WeatherService()
        self.setup_styles()
        self.setup_ui()
        self.root.bind('<Control-d>', self.toggle_theme)
        self.root.after(500, self.show_welcome_message)
        
        self.fetch_weather()
        self.auto_refresh()
    
    def show_welcome_message(self):
        """Show welcome message using messagebox"""
        welcome_msg = """
        🎉 Welcome to Advanced News Hub! 🎉

        For the best experience:
        
        1. Please maximize this window to full screen
        2. Keyboard shortcuts available:
        - Ctrl+D: Toggle Dark/Light mode
        - Double-click: Open articles
        - Right-click: Quick actions menu
        
        Features:
        • Click 🌐 icons to translate articles
        • Click 🔊 icons to hear summaries
        • Star (⭐) articles to save favorites
        
        Pro Tip: Check the analytics dashboard for trends!
        """
        
        # Create a custom-styled messagebox
        messagebox.showinfo("Welcome to News Hub",  welcome_msg.strip())
    
    def setup_styles(self):
        """Setup modern elegant styles with theme support"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Light theme colors
        self.light_theme = {
            'bg': '#f8f9fa',
            'fg': '#2c3e50',
            'header_bg': '#2c3e50',
            'header_fg': 'white',
            'text_bg': 'white',
            'text_fg': 'black',
            'listbox_bg': 'white',
            'listbox_fg': '#2c3e50',
            'button_bg': '#3498db',
            'button_fg': 'white'
        }
        
        # Dark theme colors
        self.dark_theme = {
            'bg': '#2d2d2d',
            'fg': '#e0e0e0',
            'header_bg': '#1a1a1a',
            'header_fg': '#e0e0e0',
            'text_bg': '#3d3d3d',
            'text_fg': '#e0e0e0',
            'listbox_bg': '#3d3d3d',
            'listbox_fg': '#e0e0e0',
            'button_bg': '#505050',
            'button_fg': '#e0e0e0'
        }
        self.category_colors = {
        'light': {
            'Politics': '#e74c3c',
            'Technology': '#3498db',
            'Sports': '#27ae60',
            'Business': '#f39c12',
            'Health': '#e67e22',
            'Science': '#9b59b6',
            'World': '#34495e',
            'Entertainment': '#e91e63',
            'General': '#2c3e50'
        },
        'dark': {
            'Politics': '#ff6b6b',
            'Technology': '#5dade2',
            'Sports': '#58d68d',
            'Business': '#f7dc6f',
            'Health': '#f8c471',
            'Science': '#bb8fce',
            'World': '#85929e',
            'Entertainment': '#f48fb1',
            'General': '#e0e0e0'
        }
    }
        
        self.current_theme = self.light_theme  # Start with light theme
        
        # Configure styles for both themes
        self.configure_styles()
   
    def configure_styles(self):
        """Configure widget styles based on current theme"""
        style = ttk.Style()
        
        # Frame styles
        style.configure('Modern.TFrame', background=self.current_theme['bg'])
        style.configure('Header.TFrame', background=self.current_theme['header_bg'])
        
        # Label styles
        style.configure('Header.TLabel', 
                    background=self.current_theme['header_bg'],
                    foreground=self.current_theme['header_fg'],
                    font=('Segoe UI', 11, 'bold'))
        style.configure('Weather.TLabel', 
                    background=self.current_theme['button_bg'],
                    foreground=self.current_theme['button_fg'],
                    font=('Segoe UI', 10),
                    padding=(10, 5))
        style.configure('Modern.TLabelFrame', 
                    font=('Segoe UI', 10, 'bold'),
                    background=self.current_theme['bg'])
        style.configure('Title.TLabel', 
                    font=('Segoe UI', 11, 'bold'),
                    foreground=self.current_theme['fg'])
        style.configure('Source.TLabel', 
                    font=('Segoe UI', 9),
                    foreground=self.current_theme['fg'])
        
        # Button styles
        style.configure('Modern.TButton', 
                    font=('Segoe UI', 9),
                    padding=(10, 5),
                    background=self.current_theme['button_bg'],
                    foreground=self.current_theme['button_fg'])
        
        style.map('Modern.TButton',
                background=[('active', self.current_theme['button_bg']),
                            ('pressed', self.current_theme['button_bg'])],
                foreground=[('active', self.current_theme['button_fg'])])
        
        # Entry styles
        style.configure('Search.TEntry', 
                    font=('Segoe UI', 10),
                    fieldbackground='white')
    
    def toggle_theme(self, event=None):
        """Toggle between light and dark themes"""
        if self.current_theme == self.light_theme:
            self.current_theme = self.dark_theme
        else:
            self.current_theme = self.light_theme
        
        # Reconfigure all styles
        self.configure_styles()
        self.update_widget_colors()
        self.update_display()  # Refresh article colors
        
        theme_name = "Dark" if self.current_theme == self.dark_theme else "Light"
        self.status_var.set(f"Switched to {theme_name} theme")
    
    def update_widget_colors(self):
        """Update colors for non-themed widgets"""
        # Root background
        self.root.configure(bg=self.current_theme['bg'])
        
        # Listbox colors
        self.news_listbox.configure(
            bg=self.current_theme['listbox_bg'],
            fg=self.current_theme['listbox_fg'],
            selectbackground=self.current_theme['button_bg'],
            selectforeground=self.current_theme['button_fg']
        )
        
        # Text widgets
        text_widgets = [self.stats_text, self.preview_text]
        for widget in text_widgets:
            widget.configure(
                bg=self.current_theme['text_bg'],
                fg=self.current_theme['text_fg'],
                insertbackground=self.current_theme['text_fg']  # Cursor color
            )
   
    def setup_ui(self):
        """Setup the elegant user interface"""
        main_frame = ttk.Frame(self.root, padding="15", style='Modern.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Set up all UI components
        self.setup_header(main_frame)
        self.setup_controls(main_frame)
        self.setup_content(main_frame)
        self.setup_status_bar(main_frame)
        
        # Initial theme application
        self.update_widget_colors()
   
    def setup_header(self, parent):
        """Setup elegant header with weather"""
        header_frame = ttk.Frame(parent, style='Header.TFrame', padding="10")
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(1, weight=1)
        
        title_label = ttk.Label(header_frame, text="🗞️ Advanced News Hub", 
                               style='Header.TLabel', font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        weather_frame = ttk.Frame(header_frame, style='Header.TFrame')
        weather_frame.grid(row=0, column=2, sticky=tk.E)
        
        self.weather_label = ttk.Label(weather_frame, text="🌤️ Loading weather...", 
                                      style='Weather.TLabel')
        self.weather_label.pack(padx=10, pady=5)
        
        self.time_label = ttk.Label(header_frame, text="", style='Header.TLabel', font=('Segoe UI', 10))
        self.time_label.grid(row=0, column=1, sticky=tk.E, padx=(0, 20))
        self.update_time()
    
    def setup_controls(self, parent):
        """Setup modern control panel"""
        controls_frame = ttk.LabelFrame(parent, text="🔍 News Controls", padding="10")
        controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        controls_frame.columnconfigure(1, weight=1)
        
        search_frame = ttk.Frame(controls_frame)
        search_frame.grid(row=0, column=0, columnspan=4, sticky=(tk.W, tk.E), pady=(0, 10))
        search_frame.columnconfigure(1, weight=1)
        
        ttk.Label(search_frame, text="🔎 Search:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=(0, 8))
        self.search_var = tk.StringVar()
        self.search_entry = ttk.Entry(search_frame, textvariable=self.search_var, 
                                     style='Search.TEntry', font=('Segoe UI', 10), width=40)
        self.search_entry.grid(row=0, column=1, sticky=(tk.W, tk.E), padx=(0, 8))
        self.search_entry.bind('<KeyRelease>', self.on_search)
        
        ttk.Button(search_frame, text="Clear", command=self.clear_search, 
                  style='Modern.TButton').grid(row=0, column=2)
        
        filter_frame = ttk.Frame(controls_frame)
        filter_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
        ttk.Label(filter_frame, text="📂 Category:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=(0, 8))
        self.category_var = tk.StringVar(value='All')
        categories = ['All'] + list(self.news_aggregator.categories.keys()) + ['General']
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, 
                                     values=categories, state='readonly', width=15, font=('Segoe UI', 9))
        category_combo.grid(row=0, column=1, padx=(0, 15))
        category_combo.bind('<<ComboboxSelected>>', self.on_category_change)
        
        ttk.Label(filter_frame, text="📺 Source:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, padx=(0, 8))
        self.source_var = tk.StringVar(value='All')
        sources = ['All'] + list(self.news_aggregator.news_sources.keys())
        source_combo = ttk.Combobox(filter_frame, textvariable=self.source_var, 
                                   values=sources, state='readonly', width=15, font=('Segoe UI', 9))
        source_combo.grid(row=0, column=3, padx=(0, 15))
        source_combo.bind('<<ComboboxSelected>>', self.on_source_change)
        
        button_frame = ttk.Frame(filter_frame)
        button_frame.grid(row=0, column=4, sticky=tk.E)
        
        ttk.Button(button_frame, text="🔄 Refresh", command=self.refresh_news, 
                  style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="⭐ Favorites", command=self.show_favorites, 
                  style='Modern.TButton').pack(side=tk.LEFT)
    
    def setup_content(self, parent):
        """Setup main content area"""
        content_frame = ttk.Frame(parent)
        content_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        content_frame.columnconfigure(1, weight=1)
        content_frame.rowconfigure(0, weight=1)
        
        sidebar_frame = ttk.LabelFrame(content_frame, text="📊 News Analytics", padding="10")
        sidebar_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 15))
        
        self.stats_text = scrolledtext.ScrolledText(sidebar_frame, width=25, height=20, 
                                                   font=('Segoe UI', 9), bg='#f8f9fa', 
                                                   borderwidth=1, relief='solid',state='disabled')
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        news_frame = ttk.LabelFrame(content_frame, text="📰 Latest Headlines", padding="10")
        news_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        news_frame.columnconfigure(0, weight=1)
        news_frame.rowconfigure(0, weight=1)
        
        list_frame = ttk.Frame(news_frame)
        list_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        self.news_listbox = tk.Listbox(list_frame, font=('Segoe UI', 10), selectmode=tk.SINGLE,
                                      bg='white', borderwidth=1, relief='solid', highlightthickness=0)
        self.news_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        self.news_listbox.bind('<Double-Button-1>', self.open_article)
        self.news_listbox.bind('<Button-1>', self.on_single_click)
        self.news_listbox.bind('<Button-3>', self.show_context_menu)
        
        scrollbar_v = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.news_listbox.yview)
        scrollbar_v.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.news_listbox.configure(yscrollcommand=scrollbar_v.set)
        
        preview_frame = ttk.LabelFrame(news_frame, text="👁️ Article Preview", padding="10")
        preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=8, font=('Segoe UI', 9), 
                                                     wrap=tk.WORD, bg='#f8f9fa', borderwidth=1, 
                                                     relief='solid', highlightthickness=0,state='disabled')
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        self.news_listbox.bind('<<ListboxSelect>>', self.show_preview)
        
        self.context_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.context_menu.add_command(label="🔗 Open Article", command=self.open_article)
        self.context_menu.add_command(label="⭐ Add to Favorites", command=self.add_to_favorites)
        self.context_menu.add_command(label="📋 Copy Link", command=self.copy_link)
        self.context_menu.add_command(label="📝 Show Summary", command=self.show_article_summary)
    
    def setup_status_bar(self, parent):
        """Setup elegant status bar"""
        status_frame = ttk.Frame(parent, padding="5")
        status_frame.grid(row=3, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(10, 0))
        status_frame.columnconfigure(0, weight=1)
        
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(status_frame, textvariable=self.status_var, 
                              relief=tk.SUNKEN, padding="8", font=('Segoe UI', 9))
        status_bar.grid(row=0, column=0, sticky=(tk.W, tk.E))
        
        tips_label = ttk.Label(status_frame, 
                              text="💡 Click 🔗 source names to open articles instantly | Double-click anywhere for same effect", 
                              font=('Segoe UI', 8), foreground='#7f8c8d')
        tips_label.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(5, 0))
    
    def fetch_weather(self):
        """Fetch weather in background"""
        def weather_thread():
            weather_data = self.weather_service.get_weather()
            if weather_data:
                emoji = self.weather_service.get_weather_emoji(
                    weather_data['weather_code'], 
                    weather_data['is_day']
                )
                weather_text = f"{emoji} {weather_data['temperature']:.1f}°C • {weather_data['city']}, {weather_data['country']}"
                self.root.after(0, lambda: self.weather_label.config(text=weather_text))
            else:
                self.root.after(0, lambda: self.weather_label.config(text="🌍 Weather unavailable"))
        
        threading.Thread(target=weather_thread, daemon=True).start()
    
    def update_time(self):
        """Update current time display"""
        current_time = datetime.now().strftime("%A, %B %d, %Y • %I:%M %p")
        self.time_label.config(text=current_time)
        self.root.after(1000, self.update_time)
    
    def update_progress(self, message, current, total):
        """Update progress status"""
        self.status_var.set(f"{message} ({current}/{total})")
        self.root.update_idletasks()
    
    def refresh_news(self):
        """Refresh news in background thread"""
        def fetch_thread():
            try:
                self.fetch_weather()
                self.news_aggregator.fetch_news(self.update_progress)
                self.root.after(0, self.update_display)
            except Exception as e:
                error_msg = f"Failed to fetch news: {str(e)}"
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def update_display(self):
        """Update the news display with theme-aware colors"""
        self.news_listbox.delete(0, tk.END)
        
        current_theme = 'light' if self.current_theme == self.light_theme else 'dark'
        
        for i, article in enumerate(self.news_aggregator.filtered_articles):
            date_str = article['published'].strftime('%m/%d %H:%M')
            category_emoji = self.get_category_emoji(article['category'])
            display_text = f"{category_emoji} {article['title']} • 🔗{article['source']} • {date_str}"
            self.news_listbox.insert(tk.END, display_text)
            
            # Get color based on current theme and category
            color = self.category_colors[current_theme].get(
                article['category'], 
                self.category_colors[current_theme]['General']
            )
            self.news_listbox.itemconfig(i, {'fg': color})
        
        self.update_stats()
        self.status_var.set(f"📊 Loaded {len(self.news_aggregator.filtered_articles)} articles • Last updated: {datetime.now().strftime('%H:%M')}")
    
    def get_category_emoji(self, category):
        """Get emoji for category"""
        emoji_map = {
            'Politics': '🏛️',
            'Technology': '💻',
            'Sports': '⚽',
            'Business': '💼',
            'Health': '🏥',
            'Science': '🔬',
            'World': '🌍',
            'Entertainment': '🎬',
            'General': '📰'
        }
        return emoji_map.get(category, '📰')
    
    def update_stats(self):
        """Update statistics with elegant formatting"""
        self.stats_text.config(state='normal')
        self.stats_text.delete(1.0, tk.END)
        
        if not self.news_aggregator.articles:
            self.stats_text.insert(tk.END, "📊 No data available\n\nClick '🔄 Refresh' to load articles")
            self.stats_text.config(state='disabled')
            return
        
        category_counts = defaultdict(int)
        source_counts = defaultdict(int)
        
        for article in self.news_aggregator.articles:
            category_counts[article['category']] += 1
            source_counts[article['source']] += 1
        
        self.stats_text.insert(tk.END, "📊 ANALYTICS DASHBOARD\n")
        self.stats_text.insert(tk.END, "─" * 25 + "\n\n")
        
        self.stats_text.insert(tk.END, f"📰 Total Articles: {len(self.news_aggregator.articles)}\n")
        self.stats_text.insert(tk.END, f"🔍 Filtered: {len(self.news_aggregator.filtered_articles)}\n")
        self.stats_text.insert(tk.END, f"⭐ Favorites: {len(self.news_aggregator.favorites)}\n\n")
        
        self.stats_text.insert(tk.END, "📂 BY CATEGORY\n")
        self.stats_text.insert(tk.END, "─" * 15 + "\n")
        
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories:
            emoji = self.get_category_emoji(category)
            percentage = (count / len(self.news_aggregator.articles)) * 100
            self.stats_text.insert(tk.END, f"{emoji} {category}: {count} ({percentage:.1f}%)\n")
        
        self.stats_text.insert(tk.END, "\n📺 BY SOURCE\n")
        self.stats_text.insert(tk.END, "─" * 12 + "\n")
        
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        for source, count in sorted_sources:
            percentage = (count / len(self.news_aggregator.articles)) * 100
            self.stats_text.insert(tk.END, f"• {source}: {count} ({percentage:.1f}%)\n")
        
        self.stats_text.insert(tk.END, "\n⏰ RECENT ACTIVITY\n")
        self.stats_text.insert(tk.END, "─" * 16 + "\n")
        
        now = datetime.now()
        recent_count = sum(1 for article in self.news_aggregator.articles 
                          if (now - article['published']).total_seconds() < 3600)
        today_count = sum(1 for article in self.news_aggregator.articles 
                         if article['published'].date() == now.date())
        
        self.stats_text.insert(tk.END, f"🔥 Last hour: {recent_count} articles\n")
        self.stats_text.insert(tk.END, f"📅 Today: {today_count} articles\n")
        
        self.stats_text.insert(tk.END, "\n🔥 TRENDING KEYWORDS\n")
        self.stats_text.insert(tk.END, "─" * 18 + "\n")
        
        word_counts = defaultdict(int)
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
        
        for article in self.news_aggregator.articles:
            words = re.findall(r'\b\w+\b', article['title'].lower())
            for word in words:
                if len(word) > 3 and word not in stop_words:
                    word_counts[word] += 1
        
        trending_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:8]
        for word, count in trending_words:
            self.stats_text.insert(tk.END, f"• {word.title()}: {count}x\n")
        self.stats_text.config(state='disabled')
    
    def on_search(self, event=None):
        """Handle search input"""
        query = self.search_var.get()
        self.news_aggregator.search_articles(query)
        self.update_display()
    
    def clear_search(self):
        """Clear search and reset filters"""
        self.search_var.set('')
        self.news_aggregator.search_articles('')
        self.update_display()
    
    def on_category_change(self, event=None):
        """Handle category filter change"""
        category = self.category_var.get()
        self.news_aggregator.filter_by_category(category)
        self.update_display()
    
    def on_source_change(self, event=None):
        """Handle source filter change"""
        source = self.source_var.get()
        self.news_aggregator.filter_by_source(source)
        self.update_display()
    
    def on_single_click(self, event):
        """Handle single click for preview"""
        self.show_preview(event)
    
    def show_preview(self, event=None):
        """Show article preview"""
        selection = self.news_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.news_aggregator.filtered_articles):
                article = self.news_aggregator.filtered_articles[index]
                
                # Enable widget for editing
                self.preview_text.config(state='normal')
                self.preview_text.delete(1.0, tk.END)
                
                preview_content = f"📰 {article['title']}\n\n"
                preview_content += f"🔗 Source: {article['source']}\n"
                preview_content += f"📅 Published: {article['published'].strftime('%A, %B %d, %Y at %I:%M %p')}\n"
                preview_content += f"📂 Category: {article['category']}\n"
                preview_content += f"⭐ Favorited: {'Yes' if article['id'] in [fav['id'] for fav in self.news_aggregator.favorites] else 'No'}\n"
                preview_content += "─" * 50 + "\n\n"
                
                summary = re.sub(r'<[^>]+>', '', article['summary'])
                preview_content += f"📝 Summary:\n{summary}\n\n"
                preview_content += f"🌐 Link: {article['link']}"
                
                self.preview_text.insert(tk.END, preview_content)
                self.preview_text.config(state='disabled')  # Disable after update
  
    def open_article(self, event=None):
        """Open selected article in browser"""
        selection = self.news_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.news_aggregator.filtered_articles):
                article = self.news_aggregator.filtered_articles[index]
                try:
                    webbrowser.open(article['link'])
                    self.status_var.set(f"🌐 Opened: {article['title'][:50]}...")
                except Exception as e:
                    messagebox.showerror("Error", f"Could not open article: {str(e)}")
    
    def show_context_menu(self, event):
        """Show context menu on right-click"""
        selection = self.news_listbox.nearest(event.y)
        self.news_listbox.selection_clear(0, tk.END)
        self.news_listbox.selection_set(selection)
        self.news_listbox.activate(selection)
        
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()
 
    def show_article_summary(self):
        """Show AI-generated article summary with non-blocking TTS functionality"""
        selection = self.news_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select an article first!")
            return
        
        index = selection[0]
        if index >= len(self.news_aggregator.filtered_articles):
            return
        
        article = self.news_aggregator.filtered_articles[index]
        
        # Create summary window
        summary_window = tk.Toplevel(self.root)
        summary_window.title(f"Summary - {article['title'][:50]}...")
        summary_window.geometry("1200x650+0+0")
        summary_window.iconbitmap('newspaper.ico')
        summary_window.configure(bg=self.current_theme['bg'])
        summary_window.resizable(True, True)
        
        # State management
        app_state = {
            'tts_playing': False,
            'tts_process': None,
            'audio_file': None,
            'stop_requested': False,
            'is_translating': False,
            'original_summary': '',
            'translated_summary': '',
            'current_lang': 'en',
            'selected_text': ''
        }
        
        # Supported languages
        supported_languages = {
            'en': {'name': 'English', 'emoji': '🇬🇧'},
            'hi': {'name': 'Hindi', 'emoji': '🇮🇳'},
            'es': {'name': 'Spanish', 'emoji': '🇪🇸'},
            'fr': {'name': 'French', 'emoji': '🇫🇷'},
            'de': {'name': 'German', 'emoji': '🇩🇪'},
            'gu': {'name': 'Gujarati', 'emoji': '🇮🇳'},
            'pa': {'name': 'Punjabi', 'emoji': '🇮🇳'},
            'zh': {'name': 'Chinese', 'emoji': '🇨🇳'},
            'bn': {'name': 'Bengali', 'emoji': '🇧🇩'}
        }
        
        # Create custom styles
        style = ttk.Style()
        
        # Configure header style - purple in dark mode
        if self.current_theme == self.dark_theme:
            header_fg = '#bb86fc'  # Purple
            star_emoji = "🌟"
        else:
            header_fg = self.current_theme['fg']
            star_emoji = "⭐"
        
        style.configure(
            'Summary.TFrame',
            background=self.current_theme['bg']
        )
        
        style.configure(
            'SummaryHeader.TLabel',
            font=('Segoe UI', 16, 'bold'),
            foreground=header_fg,
            background=self.current_theme['bg']
        )
        
        # UI Setup
        canvas = tk.Canvas(summary_window, bg=self.current_theme['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(summary_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Summary.TFrame')
        
        scrollable_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=15)
        scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=15)
        
        content_frame = ttk.Frame(scrollable_frame, padding="20", style='Summary.TFrame')
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=1)
        
        # Article title with themed styling
        title_label = ttk.Label(
            content_frame, 
            text=f"{star_emoji} {article['title']}", 
            style='SummaryHeader.TLabel',
            wraplength=600
        )
        title_label.grid(row=0, column=0, pady=(0, 15), sticky="ew")
        
        # Metadata frame
        metadata_frame = ttk.Frame(content_frame, style='Summary.TFrame')
        metadata_frame.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        
        source_info = f"🔗 {article['source']} • 📅 {article['published'].strftime('%B %d, %Y at %I:%M %p')} • 📂 {article['category']}"
        metadata_label = ttk.Label(
            metadata_frame, 
            text=source_info, 
            font=('Segoe UI', 10), 
            foreground=self.current_theme['fg'],
            background=self.current_theme['bg']
        )
        metadata_label.pack()
        
        # Try to load article image
        image_label = None
        try:
            image_url = None
            for source_name, source_url in self.news_aggregator.news_sources.items():
                if source_name == article['source']:
                    try:
                        feed = feedparser.parse(source_url)
                        for entry in feed.entries:
                            if hasattr(entry, 'link') and entry.link == article['link']:
                                if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                                    image_url = entry.media_thumbnail[0]['url']
                                elif hasattr(entry, 'media_content') and entry.media_content:
                                    image_url = entry.media_content[0]['url']
                                elif hasattr(entry, 'enclosures') and entry.enclosures:
                                    for enclosure in entry.enclosures:
                                        if enclosure.type.startswith('image/'):
                                            image_url = enclosure.href
                                            break
                                elif hasattr(entry, 'summary'):
                                    img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.summary)
                                    if img_match:
                                        image_url = img_match.group(1)
                                break
                        break
                    except:
                        continue
            
            if image_url:
                response = requests.get(image_url, timeout=10)
                if response.status_code == 200:
                    img = Image.open(BytesIO(response.content))
                    img.thumbnail((400, 300), Image.Resampling.LANCZOS)
                    img_tk = ImageTk.PhotoImage(img)
                    image_label = ttk.Label(content_frame, image=img_tk)
                    image_label.image = img_tk
                    image_label.grid(row=2, column=0, pady=(0, 20))
        except Exception as e:
            print(f"Error loading image: {e}")
        
        if image_label is None:
            placeholder_frame = ttk.Frame(content_frame, style='Summary.TFrame')
            placeholder_frame.grid(row=2, column=0, pady=(0, 20))
            placeholder_label = ttk.Label(
                placeholder_frame, 
                text="🖼️ No image available", 
                font=('Segoe UI', 12), 
                foreground=self.current_theme['fg'],
                background='#ecf0f1',
                padding=(20, 40)
            )
            placeholder_label.pack()
        
        # Clean the summary and check if content exists
        clean_summary = re.sub(r'<[^>]+>', '', article['summary']) if article.get('summary') else ''
        clean_summary = ' '.join(clean_summary.split())
        
        if not clean_summary:
            messagebox.showinfo("No Content", "This article has no text content available for summarization.")
            summary_window.destroy()
            return

        # Generate AI summary with error handling
        def generate_ai_summary(text):
            """Generate AI summary with proper error handling"""
            try:
                # Detect language first
                try:
                    lang = detect(text)
                    if lang not in ['en', 'hi', 'es', 'fr']:  # Supported languages for best results
                        self.status_var.set(f"⚠️ Non-English content detected ({lang}), translation may be needed")
                except:
                    pass  # Language detection failed, proceed anyway

                prompt = (
                    f"Summarize this in English in 150-200 words, preserving key information.\n"
                    f"First detect if this is English or needs translation:\n\n{text[:3000]}"  # Limit input size
                )
                
                completion = client.chat.completions.create(
                    extra_headers={"X-Title": "NewsApp"},
                    model="qwen/qwen2.5-vl-32b-instruct:free",
                    messages=[
                        {"role": "system", "content": "You summarize news articles concisely in English. "
                        "If content isn't English, first note 'NON-ENGLISH CONTENT DETECTED' then summarize."},
                        {"role": "user", "content": prompt}
                    ],
                    timeout=30  # Add timeout
                )
                
                result = completion.choices[0].message.content.strip()
                return result if result else "Could not generate summary (empty response)"
                
            except Exception as e:
                print(f"AI summary error: {e}")
                return f"⚠️ Summary unavailable: {str(e)}"

        # Generate initial AI summary with content check
        try:
            ai_summary = generate_ai_summary(clean_summary)
            if "unavailable" in ai_summary.lower() or "could not" in ai_summary.lower():
                raise Exception(ai_summary)
                
            app_state['original_summary'] = ai_summary
            app_state['translated_summary'] = ai_summary
            
        except Exception as e:
            messagebox.showwarning("Summary Failed", 
                f"Could not generate summary:\n{str(e)}\n\nShowing raw content instead.")
            app_state['original_summary'] = clean_summary
            app_state['translated_summary'] = clean_summary

        # Translate text
        def translate_text(text, target_lang):
            """Translate text to target language"""
            if target_lang == 'en':
                return text
                
            try:
                translator = GoogleTranslator(source='auto', target=target_lang)
                translated = translator.translate(text)
                return translated
            except Exception as e:
                print(f"Translation error ({target_lang}): {e}")
                return None

        # Threaded translation
        def start_translation(text, target_lang):
            """Start translation in background thread"""
            if app_state['is_translating']:
                return
                
            app_state['is_translating'] = True
            translate_btn.config(text="⏳ Translating...", state='disabled')
            
            def translation_thread():
                try:
                    translated = translate_text(text, target_lang)
                    if translated:
                        app_state['translated_summary'] = translated
                        app_state['current_lang'] = target_lang
                        summary_window.after(0, lambda: update_summary_display(translated))
                    else:
                        summary_window.after(0, lambda: messagebox.showwarning(
                            "Translation Failed", 
                            f"Could not translate to {supported_languages[target_lang]['name']}. Showing English version."
                        ))
                        summary_window.after(0, lambda: update_summary_display(text))
                except Exception as e:
                    print(f"Translation thread error: {e}")
                    summary_window.after(0, lambda: messagebox.showerror(
                        "Error", 
                        f"Translation failed: {str(e)}"
                    ))
                finally:
                    app_state['is_translating'] = False
                    summary_window.after(0, lambda: translate_btn.config(
                        text="🌐 Translate", 
                        state='normal'
                    ))
            
            threading.Thread(target=translation_thread, daemon=True).start()

        # Update summary display
        def update_summary_display(text):
            """Update the summary text widget"""
            summary_text.config(state=tk.NORMAL)
            summary_text.delete('1.0', tk.END)
            summary_text.insert('1.0', text)
            summary_text.config(state=tk.DISABLED)
            
            lang_info = supported_languages[app_state['current_lang']]
            word_count = len(text.split())
            summary_title.config(
                text=f"📝 {lang_info['emoji']} AI-Generated Summary ({word_count} words) • Language: {lang_info['name']}"
            )

        # Generate initial AI summary
        ai_summary = generate_ai_summary(clean_summary)
        app_state['original_summary'] = ai_summary
        app_state['translated_summary'] = ai_summary
        
        # Language selection controls
        lang_frame = ttk.Frame(content_frame, style='Summary.TFrame')
        lang_frame.grid(row=3, column=0, pady=(10, 5), sticky="w")
        
        ttk.Label(lang_frame, text="🌐 Language:", font=('Segoe UI', 10, 'bold')).pack(side=tk.LEFT, padx=(0, 8))
        
        lang_var = tk.StringVar(value='English 🇬🇧')
        lang_names = [f"{info['emoji']} {info['name']}" for code, info in supported_languages.items()]
        lang_combo = ttk.Combobox(
            lang_frame, 
            textvariable=lang_var, 
            values=lang_names,
            state='readonly', 
            width=20, 
            font=('Segoe UI', 9)
        )
        lang_combo.pack(side=tk.LEFT, padx=(0, 10))
        lang_combo.current(0)  # Default to English
        
        translate_btn = ttk.Button(
            lang_frame, 
            text="🌐 Translate", 
            command=lambda: start_translation(
                app_state['original_summary'],
                list(supported_languages.keys())[lang_combo.current()]
            ), 
            style='Modern.TButton'
        )
        translate_btn.pack(side=tk.LEFT)
        
        # Summary display area
        summary_title = ttk.Label(
            content_frame, 
            text="📝 🇬🇧 AI-Generated Summary", 
            font=('Segoe UI', 12, 'bold'), 
            foreground=header_fg,
            background=self.current_theme['bg']
        )
        summary_title.grid(row=4, column=0, pady=(10, 5), sticky="w")
        
        summary_frame = ttk.Frame(content_frame, style='Summary.TFrame')
        summary_frame.grid(row=5, column=0, pady=(0, 20), sticky="ew")
        summary_frame.columnconfigure(0, weight=1)
        
        summary_text = tk.Text(
            summary_frame, 
            height=15, 
            font=('Segoe UI', 11), 
            wrap=tk.WORD, 
            bg=self.current_theme['text_bg'],
            fg=self.current_theme['text_fg'],
            borderwidth=1, 
            relief='solid',
            highlightthickness=0,
            padx=15,
            pady=15,
            state=tk.NORMAL
        )
        summary_text.grid(row=0, column=0, sticky="ew")
        summary_text.insert('1.0', ai_summary)
        summary_text.config(state=tk.DISABLED)
        
        # Add right-click context menu for text selection
        text_context_menu = tk.Menu(summary_window, tearoff=0, font=('Segoe UI', 9))
        text_context_menu.add_command(label="🔊 Speak Selected", command=lambda: speak_selected_text())
        text_context_menu.add_command(label="📋 Copy", command=lambda: copy_selected_text())
        
        def show_text_context_menu(event):
            """Show context menu for text selection"""
            try:
                app_state['selected_text'] = summary_text.get(tk.SEL_FIRST, tk.SEL_LAST)
                if app_state['selected_text'].strip():
                    text_context_menu.tk_popup(event.x_root, event.y_root)
            except tk.TclError:
                pass  # No text selected
        
        summary_text.bind("<Button-3>", show_text_context_menu)
        
        # Action buttons
        button_frame = ttk.Frame(content_frame, style='Summary.TFrame')
        button_frame.grid(row=6, column=0, pady=(10, 0))
        
        # Improved TTS functionality
        def read_summary_aloud():
            """Read the summary aloud using TTS with non-blocking playback"""
            if app_state['tts_playing']:
                stop_reading()
                return
            
            try:
                read_btn.config(text="🔄 Preparing...", state='disabled')
                speak_selected_btn.config(state='disabled')
                summary_window.update()
                
                def tts_thread():
                    try:
                        reading_text = summary_text.get('1.0', tk.END).strip()
                        current_lang = app_state['current_lang']
                        lang_name = supported_languages[current_lang]['name']
                        
                        tts = gTTS(text=reading_text, lang=current_lang, slow=False)
                        temp_file_path = os.path.join(tempfile.gettempdir(), f"newsapp_tts_{int(time.time())}.mp3")
                        tts.save(temp_file_path)
                        
                        if not os.path.exists(temp_file_path):
                            raise Exception("Failed to create TTS audio file")
                            
                        app_state['audio_file'] = temp_file_path
                        
                        def update_ui_playing():
                            app_state['tts_playing'] = True
                            app_state['stop_requested'] = False
                            read_btn.config(text="⏹️ Stop Reading", state='normal')
                            self.status_var.set(f"🔊 Reading summary in {lang_name}...")
                        
                        summary_window.after(0, update_ui_playing)
                        
                        pygame.mixer.init()
                        pygame.mixer.music.load(temp_file_path)
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy() and not app_state['stop_requested']:
                            time.sleep(0.1)
                        
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                        try:
                            os.unlink(temp_file_path)
                        except:
                            pass
                        
                        def update_ui_finished():
                            app_state['tts_playing'] = False
                            app_state['stop_requested'] = False
                            read_btn.config(text="🔊 Read Summary", state='normal')
                            speak_selected_btn.config(state='normal')
                            if app_state['stop_requested']:
                                self.status_var.set("🔇 Reading stopped")
                            else:
                                self.status_var.set("✅ Reading completed")
                        
                        summary_window.after(0, update_ui_finished)
                        
                    except Exception as e:
                        error_msg = f"TTS Error: {str(e)}"
                        print(error_msg)
                        def show_error():
                            if summary_window.winfo_exists():
                                app_state['tts_playing'] = False
                                read_btn.config(text="🔊 Read Summary", state='normal')
                                speak_selected_btn.config(state='normal')
                                messagebox.showerror("Text-to-Speech Error", f"Could not read summary:\n{error_msg}")
                        summary_window.after(0, show_error)
                
                threading.Thread(target=tts_thread, daemon=True).start()
                
            except Exception as e:
                app_state['tts_playing'] = False
                read_btn.config(text="🔊 Read Summary", state='normal')
                speak_selected_btn.config(state='normal')
                messagebox.showerror("Error", f"Could not initialize text-to-speech: {str(e)}",parent=summary_window)

        def stop_reading():
            """Stop TTS playback without freezing UI"""
            if not app_state['tts_playing']:
                return
            
            app_state['stop_requested'] = True
            read_btn.config(text="🔄 Stopping...", state='disabled')
            speak_selected_btn.config(state='disabled')
            self.status_var.set("🛑 Stopping playback...")
            
            def force_stop():
                try:
                    if pygame.mixer.get_init():
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                except:
                    pass
                
                if app_state['audio_file'] and os.path.exists(app_state['audio_file']):
                    try:
                        os.unlink(app_state['audio_file'])
                    except:
                        pass
                
                def update_ui():
                    app_state['tts_playing'] = False
                    app_state['stop_requested'] = False
                    read_btn.config(text="🔊 Read Summary", state='normal')
                    speak_selected_btn.config(state='normal')
                    self.status_var.set("🔇 Playback stopped")
                
                summary_window.after(0, update_ui)
            
            threading.Thread(target=force_stop, daemon=True).start()

        def speak_selected_text():
            """Read the selected text aloud using TTS"""
            if app_state['tts_playing']:
                stop_reading()
                return
            
            try:
                try:
                    selected_text = summary_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                except tk.TclError:
                    messagebox.showwarning("No Selection", "Please select some text first!",parent=summary_window)
                    return
                
                if not selected_text:
                    messagebox.showwarning("No Selection", "Please select some text first!",parent=summary_window)
                    return
                
                if len(selected_text.split()) > 500:
                    messagebox.showwarning("Text Too Long", "Please select less text (max 500 words).",parent=summary_window)
                    return
                
                speak_selected_btn.config(text="🔄 Preparing...", state='disabled')
                read_btn.config(state='disabled')
                summary_window.update()
                
                def tts_selected_thread():
                    try:
                        current_lang = app_state['current_lang']
                        lang_name = supported_languages[current_lang]['name']
                        
                        tts = gTTS(text=selected_text, lang=current_lang, slow=False)
                        temp_file_path = os.path.join(tempfile.gettempdir(), f"newsapp_tts_selected_{int(time.time())}.mp3")
                        tts.save(temp_file_path)
                        
                        if not os.path.exists(temp_file_path):
                            raise Exception("Failed to create TTS audio file")
                            
                        app_state['audio_file'] = temp_file_path
                        
                        def update_ui_playing():
                            app_state['tts_playing'] = True
                            app_state['stop_requested'] = False
                            speak_selected_btn.config(text="⏹️ Stop", state='normal')
                            self.status_var.set(f"🔊 Reading selected text in {lang_name}...")
                        
                        summary_window.after(0, update_ui_playing)
                        
                        pygame.mixer.init()
                        pygame.mixer.music.load(temp_file_path)
                        pygame.mixer.music.play()
                        
                        while pygame.mixer.music.get_busy() and not app_state['stop_requested']:
                            time.sleep(0.1)
                        
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                        
                        def update_ui_finished():
                            app_state['tts_playing'] = False
                            app_state['stop_requested'] = False
                            speak_selected_btn.config(text="🔈 Speak Selected", state='normal')
                            read_btn.config(state='normal')
                            if app_state['stop_requested']:
                                self.status_var.set("🔇 Reading stopped")
                            else:
                                self.status_var.set("✅ Reading completed")
                            
                            try:
                                if os.path.exists(temp_file_path):
                                    os.unlink(temp_file_path)
                            except Exception as e:
                                print(f"Error cleaning up audio file: {e}")
                        
                        summary_window.after(0, update_ui_finished)
                        
                    except Exception as e:
                        error_msg = f"TTS Error: {str(e)}"
                        print(error_msg)
                        def show_error():
                            if summary_window.winfo_exists():
                                app_state['tts_playing'] = False
                                speak_selected_btn.config(text="🔈 Speak Selected", state='normal')
                                read_btn.config(state='normal')
                                messagebox.showerror("Text-to-Speech Error", f"Could not read text:\n{error_msg}",parent=summary_window)
                        summary_window.after(0, show_error)
                
                threading.Thread(target=tts_selected_thread, daemon=True).start()
                
            except Exception as e:
                app_state['tts_playing'] = False
                speak_selected_btn.config(text="🔈 Speak Selected", state='normal')
                read_btn.config(state='normal')
                messagebox.showerror("Error", f"Could not initialize text-to-speech: {str(e)}",parent=summary_window)

        def copy_selected_text():
            """Copy selected text to clipboard"""
            try:
                selected_text = summary_text.get(tk.SEL_FIRST, tk.SEL_LAST).strip()
                if selected_text:
                    summary_window.clipboard_clear()
                    summary_window.clipboard_append(selected_text)
                    self.status_var.set("📋 Copied selected text to clipboard")
            except tk.TclError:
                messagebox.showwarning("No Selection", "Please select some text first!",parent=summary_window)

        # Add the new "Speak Selected" button
        speak_selected_btn = ttk.Button(
            button_frame, 
            text="🔈 Speak Selected", 
            command=speak_selected_text,
            style='Modern.TButton'
        )
        speak_selected_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Then add the existing buttons
        def open_full_article():
            """Open the full article in browser"""
            if app_state['tts_playing']:
                stop_reading()
            webbrowser.open(article['link'])
            self.status_var.set(f"🌐 Opened: {article['title'][:50]}...")
            summary_window.destroy()
        
        read_more_btn = ttk.Button(
            button_frame, 
            text="📖 View Online", 
            command=open_full_article, 
            style='Modern.TButton'
        )
        read_more_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        read_btn = ttk.Button(
            button_frame, 
            text="🔊 Read Summary", 
            command=read_summary_aloud, 
            style='Modern.TButton'
        )
        read_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        def add_to_favorites():
            """Add article to favorites"""
            if self.news_aggregator.add_to_favorites(article):
                messagebox.showinfo("Success", "Added to favorites!",parent=summary_window)
                self.update_stats()
            else:
                messagebox.showwarning("Info", "Article is already in favorites!",parent=summary_window)
        
        favorite_btn = ttk.Button(
            button_frame, 
            text="⭐ Add to Favorites", 
            command=add_to_favorites, 
            style='Modern.TButton'
        )
        favorite_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        def copy_article_link():
            """Copy article link to clipboard"""
            summary_window.clipboard_clear()
            summary_window.clipboard_append(article['link'])
            messagebox.showinfo("Copied", "Article link copied to clipboard!",parent=summary_window)
        
        copy_btn = ttk.Button(
            button_frame, 
            text="📋 Copy Link", 
            command=copy_article_link, 
            style='Modern.TButton'
        )
        copy_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        close_btn = ttk.Button(
            button_frame, 
            text="✖️ Close", 
            command=lambda: [stop_reading() if app_state['tts_playing'] else None, summary_window.destroy()], 
            style='Modern.TButton'
        )
        close_btn.pack(side=tk.LEFT)
        
        # TTS info frame
        tts_info_frame = ttk.Frame(content_frame, style='Summary.TFrame')
        tts_info_frame.grid(row=7, column=0, pady=(5, 0))
        
        tts_info_label = ttk.Label(
            tts_info_frame,
            text="🎵 Audio reading uses AI-generated summary in the selected language.",
            font=('Segoe UI', 8, 'italic'),
            foreground=self.current_theme['fg'],
            background=self.current_theme['bg'],
            wraplength=600
        )
        tts_info_label.pack()
        
        # Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        canvas.bind("<MouseWheel>", _on_mousewheel)
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
        summary_window.focus_set()
        
        # Update theme if changed while window is open
        def update_summary_theme():
            summary_window.configure(bg=self.current_theme['bg'])
            
            if self.current_theme == self.dark_theme:
                header_fg = '#bb86fc'
                star_emoji = "🌟"
            else:
                header_fg = self.current_theme['fg']
                star_emoji = "⭐"
            
            style.configure('Summary.TFrame', background=self.current_theme['bg'])
            style.configure('SummaryHeader.TLabel', foreground=header_fg, background=self.current_theme['bg'])
            
            title_label.config(
                text=f"{star_emoji} {article['title']}",
                style='SummaryHeader.TLabel'
            )
            
            # Update all text widgets
            text_widgets = [summary_text, metadata_label, tts_info_label, summary_title]
            for widget in text_widgets:
                if isinstance(widget, tk.Text):
                    widget.configure(
                        bg=self.current_theme['text_bg'],
                        fg=self.current_theme['text_fg'],
                        insertbackground=self.current_theme['text_fg']
                    )
                else:
                    widget.configure(
                        foreground=self.current_theme['fg'],
                        background=self.current_theme['bg']
                    )
        
        # Bind theme update
        self.root.bind('<<ThemeChanged>>', lambda e: update_summary_theme())
        # Bind Ctrl+D to toggle theme in summary window
        summary_window.bind('<Control-d>', lambda e: [
            self.toggle_theme(),
            update_summary_theme()  # Refresh the summary window's theme
        ])
        
        # Handle window close
        def on_summary_close():
            if app_state['tts_playing']:
                stop_reading()
            self.root.unbind('<<ThemeChanged>>')
            summary_window.destroy()
        
        summary_window.protocol("WM_DELETE_WINDOW", on_summary_close)
    
    def add_to_favorites(self):
        """Add selected article to favorites"""
        selection = self.news_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.news_aggregator.filtered_articles):
                article = self.news_aggregator.filtered_articles[index]
                if self.news_aggregator.add_to_favorites(article):
                    messagebox.showinfo("Success", f"Added '{article['title'][:50]}...' to favorites!")
                    self.update_stats()
                else:
                    messagebox.showwarning("Info", "Article is already in favorites!")
    
    def copy_link(self):
        """Copy article link to clipboard"""
        selection = self.news_listbox.curselection()
        if selection:
            index = selection[0]
            if index < len(self.news_aggregator.filtered_articles):
                article = self.news_aggregator.filtered_articles[index]
                self.root.clipboard_clear()
                self.root.clipboard_append(article['link'])
                self.status_var.set(f"📋 Copied link: {article['title'][:40]}...")
    
    def show_favorites(self):
        """Show favorites window with Remove All button"""
        if not self.news_aggregator.favorites:
            messagebox.showinfo("Favorites", "No favorite articles saved yet!")
            return
        
        fav_window = tk.Toplevel(self.root)
        fav_window.title("⭐ Favorite Articles")
        fav_window.geometry("800x600+0+0")
        fav_window.iconbitmap('newspaper.ico')
        fav_window.configure(bg=self.current_theme['bg'])
        
        # Create custom styles for this window
        style = ttk.Style()
        
        # Header style - purple in dark mode, default in light
        if self.current_theme == self.dark_theme:
            style.configure(
                'FavHeader.TLabel',
                font=('Segoe UI', 14, 'bold'),
                foreground='#bb86fc',  # Purple
                background=self.current_theme['bg']
            )
            star_emoji = "🌟"  # Brighter star for dark mode
        else:
            style.configure(
                'FavHeader.TLabel',
                font=('Segoe UI', 14, 'bold'),
                foreground=self.current_theme['fg'],
                background=self.current_theme['bg']
            )
            star_emoji = "⭐"
        
        # Frame style
        style.configure(
            'Fav.TFrame',
            background=self.current_theme['bg']
        )
        
        main_frame = ttk.Frame(fav_window, padding="15", style='Fav.TFrame')
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header with themed star emoji
        header_label = ttk.Label(
            main_frame, 
            text=f"{star_emoji} Your Favorite Articles", 
            style='FavHeader.TLabel'
        )
        header_label.grid(row=0, column=0, pady=(0, 15))
        
        # List frame
        list_frame = ttk.Frame(main_frame, style='Fav.TFrame')
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # Listbox with theme colors
        fav_listbox = tk.Listbox(
            list_frame, 
            font=('Segoe UI', 10), 
            bg=self.current_theme['listbox_bg'],
            fg=self.current_theme['listbox_fg'],
            selectbackground=self.current_theme['button_bg'],
            selectforeground=self.current_theme['button_fg'],
            borderwidth=1, 
            relief='solid', 
            highlightthickness=0
        )
        fav_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=fav_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        fav_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Populate list with themed colors
        current_theme = 'light' if self.current_theme == self.light_theme else 'dark'
        for i, article in enumerate(self.news_aggregator.favorites):
            date_str = article['published'].strftime('%m/%d/%Y %H:%M')
            display_text = f"{self.get_category_emoji(article['category'])} {article['title']} • {article['source']} • {date_str}"
            fav_listbox.insert(tk.END, display_text)
            
            # Set item color based on category and theme
            color = self.category_colors[current_theme].get(
                article['category'], 
                self.category_colors[current_theme]['General']
            )
            fav_listbox.itemconfig(i, {'fg': color})
        
        # Button frame
        button_frame = ttk.Frame(main_frame, style='Fav.TFrame')
        button_frame.grid(row=2, column=0, pady=(15, 0))
        
        def open_favorite():
            selection = fav_listbox.curselection()
            if selection:
                article = self.news_aggregator.favorites[selection[0]]
                webbrowser.open(article['link'])
        
        def remove_favorite():
            selection = fav_listbox.curselection()
            if selection:
                article = self.news_aggregator.favorites[selection[0]]
                if messagebox.askyesno("Confirm", f"Remove '{article['title'][:50]}...' from favorites?", parent=fav_window):
                    self.news_aggregator.remove_from_favorites(article['id'])
                    fav_listbox.delete(selection[0])
                    self.update_stats()
        
        def remove_all_favorites():
            if messagebox.askyesno("Confirm", "Remove ALL articles from favorites?", parent=fav_window):
                self.news_aggregator.favorites = []
                self.news_aggregator.save_favorites()
                fav_listbox.delete(0, tk.END)
                self.update_stats()
                messagebox.showinfo("Success", "All favorites have been removed.", parent=fav_window)
        
        # Action buttons with themed styles
        ttk.Button(
            button_frame, 
            text="🔗 Open Article", 
            command=open_favorite,
            style='Modern.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="🗑️ Remove", 
            command=remove_favorite,
            style='Modern.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="🔥 Remove All", 
            command=remove_all_favorites,
            style='Modern.TButton'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Button(
            button_frame, 
            text="✖️ Close", 
            command=fav_window.destroy,
            style='Modern.TButton'
        ).pack(side=tk.LEFT)
        
        fav_listbox.bind('<Double-Button-1>', lambda e: open_favorite())
        
        # Update theme if changed while window is open
        def update_fav_theme():
            fav_window.configure(bg=self.current_theme['bg'])
            style.configure('Fav.TFrame', background=self.current_theme['bg'])
            
            if self.current_theme == self.dark_theme:
                style.configure('FavHeader.TLabel', foreground='#bb86fc', background=self.current_theme['bg'])
                header_label.config(text=f"🌟 Your Favorite Articles")
            else:
                style.configure('FavHeader.TLabel', foreground=self.current_theme['fg'], background=self.current_theme['bg'])
                header_label.config(text=f"⭐ Your Favorite Articles")
            
            fav_listbox.configure(
                bg=self.current_theme['listbox_bg'],
                fg=self.current_theme['listbox_fg'],
                selectbackground=self.current_theme['button_bg'],
                selectforeground=self.current_theme['button_fg']
            )
            
            # Update item colors
            current_theme = 'light' if self.current_theme == self.light_theme else 'dark'
            for i, article in enumerate(self.news_aggregator.favorites):
                color = self.category_colors[current_theme].get(
                    article['category'], 
                    self.category_colors[current_theme]['General']
                )
                fav_listbox.itemconfig(i, {'fg': color})
        
        # Bind theme update (you'll need to trigger this when theme changes)
        self.root.bind('<<ThemeChanged>>', lambda e: update_fav_theme())
        # Bind Ctrl+D to toggle theme in favorites window
        fav_window.bind('<Control-d>', lambda e: [
            self.toggle_theme(),
            update_fav_theme()  # Refresh the favorites window's theme
        ])
        
        # Clean up bind when window closes
        def on_close():
            self.root.unbind('<<ThemeChanged>>')
            fav_window.destroy()
        
        fav_window.protocol("WM_DELETE_WINDOW", on_close)
    
    def auto_refresh(self):
        """Auto-refresh news every 30 minutes"""
        self.refresh_news()
        self.root.after(1800000, self.auto_refresh)

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = NewsApp(root)
    root.mainloop()
    
if __name__ == "__main__":
    main()