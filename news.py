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
import requests
from PIL import Image, ImageTk
from io import BytesIO

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
            # Using OpenWeatherMap's free API (you can get a free API key at openweathermap.org)
            # For demo purposes, using a mock weather service
            lat = self.location_data['lat']
            lon = self.location_data['lon']
            
            # Alternative free weather API (no key required)
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
                    'is_day': 1 if data.get('dt') < data.get('sys', {}).get('sunset', 0) else 0,  # Day or Night
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
            0: "☀️" if is_day else "🌙",  # Clear sky
            1: "🌤️" if is_day else "🌙",  # Mainly clear
            2: "⛅",  # Partly cloudy
            3: "☁️",  # Overcast
            45: "🌫️",  # Fog
            48: "🌫️",  # Depositing rime fog
            51: "🌦️",  # Light drizzle
            53: "🌦️",  # Moderate drizzle
            55: "🌧️",  # Dense drizzle
            61: "🌧️",  # Slight rain
            63: "🌧️",  # Moderate rain
            65: "🌧️",  # Heavy rain
            71: "🌨️",  # Slight snow
            73: "🌨️",  # Moderate snow
            75: "❄️",  # Heavy snow
            95: "⛈️",  # Thunderstorm
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
        self.unique_article_ids = set() # Add this line
        
    def load_favorites(self):
        """Load saved favorite articles"""
        try:
            if os.path.exists('favorites.json'):
                with open('favorites.json', 'r') as f:
                    return json.load(f)
        except:
            pass
        return []
    
    def save_favorites(self):
        """Save favorite articles"""
        try:
            with open('favorites.json', 'w') as f:
                json.dump(self.favorites, f, indent=2)
        except Exception as e:
            print(f"Error saving favorites: {e}")
    
    def fetch_news(self, progress_callback=None):
        """Fetch news from all sources"""
        self.articles = []
        self.unique_article_ids = set() # Re-initialize for a fresh fetch
        total_sources = len(self.news_sources)
        
        for i, (source, url) in enumerate(self.news_sources.items()):
            try:
                if progress_callback:
                    progress_callback(f"Fetching from {source}...", i, total_sources)
                
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    article_link = entry.link if hasattr(entry, 'link') and entry.link else None

                    # Use link as unique ID; if no link, generate a unique ID
                    # A more robust fallback ID combining source, title, and published date
                    article_id = article_link if article_link else f"{source}_{entry.title if hasattr(entry, 'title') else ''}_{entry.published if hasattr(entry, 'published') else ''}"

                    if article_id and article_id not in self.unique_article_ids:
                        article = {
                            'title': entry.title if hasattr(entry, 'title') else 'No Title',
                            'summary': entry.summary if hasattr(entry, 'summary') else entry.description if hasattr(entry, 'description') else 'No Summary',
                            'link': article_link if article_link else '', # Store the actual link or empty string
                            'published': self.parse_date(entry.published if hasattr(entry, 'published') else ''),
                            'source': source,
                            'category': self.categorize_article(entry.title + ' ' + (entry.summary if hasattr(entry, 'summary') else '')),
                            'id': article_id # Use the determined unique ID
                        }
                        self.articles.append(article)
                        self.unique_article_ids.add(article_id) # Add the unique ID to the set
                        
            except Exception as e:
                print(f"Error fetching from {source}: {e}")
                continue
        
        # Sort articles by date (newest first)
        self.articles.sort(key=lambda x: x['published'], reverse=True)
        self.filtered_articles = self.articles.copy()
        today = datetime.now().date()
        self.articles = [a for a in self.articles if a['published'].date() == today]
        self.filtered_articles = self.articles.copy()
        if progress_callback:
            progress_callback("Complete!", total_sources, total_sources)

    def parse_date(self, date_str):
        """Parse date string to datetime object"""
        if not date_str:
            return datetime.now()
        
        try:
            # Try different date formats
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
                    # Convert to naive datetime (remove timezone info)
                    if parsed_date.tzinfo is not None:
                        parsed_date = parsed_date.replace(tzinfo=None)
                    return parsed_date
                except:
                    continue
            
            # If all formats fail, try with feedparser's built-in date parsing
            try:
                import time
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
        self.root.configure(bg='#f8f9fa')
        
        self.news_aggregator = NewsAggregator()
        self.weather_service = WeatherService()
        self.setup_styles()
        self.setup_ui()
        
        # Fetch weather and news
        self.fetch_weather()
        self.auto_refresh()
    
    def setup_styles(self):
        """Setup modern elegant styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Modern color palette
        colors = {
            'primary': '#2c3e50',
            'secondary': '#3498db',
            'success': '#27ae60',
            'warning': '#f39c12',
            'danger': '#e74c3c',
            'light': '#ecf0f1',
            'dark': '#34495e',
            'muted': '#7f8c8d'
        }
        
        # Configure modern styles
        style.configure('Modern.TFrame', background='#f8f9fa')  # Add this line
        style.configure('Header.TFrame', background='#2c3e50')
        style.configure('Header.TLabel', background='#2c3e50', foreground='white', font=('Segoe UI', 11, 'bold'))
        style.configure('Weather.TLabel', background='#3498db', foreground='white', font=('Segoe UI', 10), padding=(10, 5))
        style.configure('Modern.TLabelFrame', font=('Segoe UI', 10, 'bold')) 
        style.configure('Title.TLabel', font=('Segoe UI', 11, 'bold'), foreground='#2c3e50')
        style.configure('Source.TLabel', font=('Segoe UI', 9), foreground='#7f8c8d')
        style.configure('Date.TLabel', font=('Segoe UI', 8), foreground='#95a5a6')
        style.configure('Category.TLabel', font=('Segoe UI', 8, 'bold'), foreground='#e74c3c')
        style.configure('Modern.TButton', font=('Segoe UI', 9), padding=(10, 5))
        style.configure('Search.TEntry', font=('Segoe UI', 10), fieldbackground='white')
        
        
        # Modern button styles
        style.map('Modern.TButton',
                background=[('active', '#3498db'), ('pressed', '#2980b9')],
                foreground=[('active', 'white')])
    
    def setup_ui(self):
        """Setup the elegant user interface"""
        # Main container with modern styling
        main_frame = ttk.Frame(self.root, padding="15", style='Modern.TFrame')
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)
        
        # Header with weather
        self.setup_header(main_frame)
        
        # Modern controls
        self.setup_controls(main_frame)
        
        # Content area
        self.setup_content(main_frame)
        
        # Status bar
        self.setup_status_bar(main_frame)
    
    def setup_header(self, parent):
        """Setup elegant header with weather"""
        header_frame = ttk.Frame(parent, style='Header.TFrame', padding="10")
        header_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        header_frame.columnconfigure(1, weight=1)
        
        # App title
        title_label = ttk.Label(header_frame, text="🗞️ Advanced News Hub", 
                               style='Header.TLabel', font=('Segoe UI', 16, 'bold'))
        title_label.grid(row=0, column=0, sticky=tk.W)
        
        # Weather widget
        weather_frame = ttk.Frame(header_frame, style='Header.TFrame')
        weather_frame.grid(row=0, column=2, sticky=tk.E)
        
        self.weather_label = ttk.Label(weather_frame, text="🌤️ Loading weather...", 
                                      style='Weather.TLabel')
        self.weather_label.pack(padx=10, pady=5)
        
        # Current time
        self.time_label = ttk.Label(header_frame, text="", style='Header.TLabel', font=('Segoe UI', 10))
        self.time_label.grid(row=0, column=1, sticky=tk.E, padx=(0, 20))
        self.update_time()
    
    def setup_controls(self, parent):
        """Setup modern control panel"""
        controls_frame = ttk.LabelFrame(parent, text="🔍 News Controls", 
                                    #    style='Modern.TLabelFrame', 
                                    padding="10")
        controls_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        controls_frame.columnconfigure(1, weight=1)
        
        # Search section
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
        
        # Filters section
        filter_frame = ttk.Frame(controls_frame)
        filter_frame.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E))
        
        # Category filter
        ttk.Label(filter_frame, text="📂 Category:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=0, padx=(0, 8))
        self.category_var = tk.StringVar(value='All')
        categories = ['All'] + list(self.news_aggregator.categories.keys()) + ['General']
        category_combo = ttk.Combobox(filter_frame, textvariable=self.category_var, 
                                     values=categories, state='readonly', width=15, font=('Segoe UI', 9))
        category_combo.grid(row=0, column=1, padx=(0, 15))
        category_combo.bind('<<ComboboxSelected>>', self.on_category_change)
        
        # Source filter
        ttk.Label(filter_frame, text="📺 Source:", font=('Segoe UI', 10, 'bold')).grid(row=0, column=2, padx=(0, 8))
        self.source_var = tk.StringVar(value='All')
        sources = ['All'] + list(self.news_aggregator.news_sources.keys())
        source_combo = ttk.Combobox(filter_frame, textvariable=self.source_var, 
                                   values=sources, state='readonly', width=15, font=('Segoe UI', 9))
        source_combo.grid(row=0, column=3, padx=(0, 15))
        source_combo.bind('<<ComboboxSelected>>', self.on_source_change)
        
        # Action buttons
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
        
        # Sidebar
        sidebar_frame = ttk.LabelFrame(content_frame, text="📊 News Analytics", 
                                    #   style='Modern.TLabelFrame', 
                                      padding="10")
        sidebar_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 15))
        
        self.stats_text = scrolledtext.ScrolledText(sidebar_frame, width=25, height=20, 
                                                   font=('Segoe UI', 9), bg='#f8f9fa', 
                                                   borderwidth=1, relief='solid')
        self.stats_text.pack(fill=tk.BOTH, expand=True)
        
        # News display
        news_frame = ttk.LabelFrame(content_frame, text="📰 Latest Headlines", 
                                #    style='Modern.TLabelFrame',
                                     padding="10")
        news_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S))
        news_frame.columnconfigure(0, weight=1)
        news_frame.rowconfigure(0, weight=1)
        
        # News list
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
        
        # Elegant scrollbars
        scrollbar_v = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.news_listbox.yview)
        scrollbar_v.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.news_listbox.configure(yscrollcommand=scrollbar_v.set)
        
        # Preview panel
        preview_frame = ttk.LabelFrame(news_frame, text="👁️ Article Preview", 
                                    #   style='Modern.TLabelFrame', 
                                      padding="10")
        preview_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        preview_frame.columnconfigure(0, weight=1)
        preview_frame.rowconfigure(0, weight=1)
        
        self.preview_text = scrolledtext.ScrolledText(preview_frame, height=8, font=('Segoe UI', 9), 
                                                     wrap=tk.WORD, bg='#f8f9fa', borderwidth=1, 
                                                     relief='solid', highlightthickness=0)
        self.preview_text.pack(fill=tk.BOTH, expand=True)
        
        self.news_listbox.bind('<<ListboxSelect>>', self.show_preview)
        
        # Context menu
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
        
        # Tips
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
        self.root.after(60000, self.update_time)  # Update every minute
    
    def update_progress(self, message, current, total):
        """Update progress status"""
        self.status_var.set(f"{message} ({current}/{total})")
        self.root.update_idletasks()
    
    def refresh_news(self):
        """Refresh news in background thread"""
        def fetch_thread():
            try:
                self.news_aggregator.fetch_news(self.update_progress)
                self.root.after(0, self.update_display)
            except Exception as e:
                error_msg = f"Failed to fetch news: {str(e)}"
                self.root.after(0, lambda msg=error_msg: messagebox.showerror("Error", msg))
        
        threading.Thread(target=fetch_thread, daemon=True).start()
    
    def update_display(self):
        """Update the news display with elegant formatting"""
        self.news_listbox.delete(0, tk.END)
        
        for i, article in enumerate(self.news_aggregator.filtered_articles):
            # Elegant display format
            date_str = article['published'].strftime('%m/%d %H:%M')
            category_emoji = self.get_category_emoji(article['category'])
            display_text = f"{category_emoji} {article['title']} • 🔗{article['source']} • {date_str}"
            self.news_listbox.insert(tk.END, display_text)
            
            # Modern color coding
            color_map = {
                'Politics': '#e74c3c',
                'Technology': '#3498db', 
                'Sports': '#27ae60',
                'Business': '#f39c12',
                'Health': '#e67e22',
                'Science': '#9b59b6',
                'World': '#34495e',
                'Entertainment': '#e91e63'
            }
            
            color = color_map.get(article['category'], '#2c3e50')
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
        self.stats_text.delete(1.0, tk.END)
        
        if not self.news_aggregator.articles:
            self.stats_text.insert(tk.END, "📊 No data available\n\nClick '🔄 Refresh' to load articles")
            return
        
        # Category and source statistics
        category_counts = defaultdict(int)
        source_counts = defaultdict(int)
        
        for article in self.news_aggregator.articles:
            category_counts[article['category']] += 1
            source_counts[article['source']] += 1
        
        # Elegant stats display
        self.stats_text.insert(tk.END, "📊 ANALYTICS DASHBOARD\n")
        self.stats_text.insert(tk.END, "─" * 25 + "\n\n")
        
        self.stats_text.insert(tk.END, f"📰 Total Articles: {len(self.news_aggregator.articles)}\n")
        self.stats_text.insert(tk.END, f"🔍 Filtered: {len(self.news_aggregator.filtered_articles)}\n")
        self.stats_text.insert(tk.END, f"⭐ Favorites: {len(self.news_aggregator.favorites)}\n\n")
        # Category breakdown
        self.stats_text.insert(tk.END, "📂 BY CATEGORY\n")
        self.stats_text.insert(tk.END, "─" * 15 + "\n")
        
        sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
        for category, count in sorted_categories:
            emoji = self.get_category_emoji(category)
            percentage = (count / len(self.news_aggregator.articles)) * 100
            self.stats_text.insert(tk.END, f"{emoji} {category}: {count} ({percentage:.1f}%)\n")
        
        self.stats_text.insert(tk.END, "\n📺 BY SOURCE\n")
        self.stats_text.insert(tk.END, "─" * 12 + "\n")
        
        sorted_sources = sorted(source_counts.items(), key=lambda x: x[1], reverse=True)[:10]  # Top 10 sources
        for source, count in sorted_sources:
            percentage = (count / len(self.news_aggregator.articles)) * 100
            self.stats_text.insert(tk.END, f"• {source}: {count} ({percentage:.1f}%)\n")
        
        # Recent activity
        self.stats_text.insert(tk.END, "\n⏰ RECENT ACTIVITY\n")
        self.stats_text.insert(tk.END, "─" * 16 + "\n")
        
        now = datetime.now()
        recent_count = sum(1 for article in self.news_aggregator.articles 
                          if (now - article['published']).total_seconds() < 3600)  # Last hour
        today_count = sum(1 for article in self.news_aggregator.articles 
                         if article['published'].date() == now.date())  # Today
        
        self.stats_text.insert(tk.END, f"🔥 Last hour: {recent_count} articles\n")
        self.stats_text.insert(tk.END, f"📅 Today: {today_count} articles\n")
        
        # Trending topics (simple keyword analysis)
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
                
                self.preview_text.delete(1.0, tk.END)
                
                # Format preview elegantly
                preview_content = f"📰 {article['title']}\n\n"
                preview_content += f"🔗 Source: {article['source']}\n"
                preview_content += f"📅 Published: {article['published'].strftime('%A, %B %d, %Y at %I:%M %p')}\n"
                preview_content += f"📂 Category: {article['category']}\n"
                preview_content += f"⭐ Favorited: {'Yes' if article['id'] in [fav['id'] for fav in self.news_aggregator.favorites] else 'No'}\n"
                preview_content += "─" * 50 + "\n\n"
                
                # Clean up summary
                summary = article['summary']
                if len(summary) > 5000:
                    summary = summary[:5000] + "..."
                
                # Remove HTML tags
                summary = re.sub(r'<[^>]+>', '', summary)
                preview_content += f"📝 Summary:\n{summary}\n\n"
                preview_content += f"🌐 Link: {article['link']}"
                
                self.preview_text.insert(tk.END, preview_content)
    
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
        """Show article summary in a new window with 5000-word limit and read more functionality"""
        selection = self.news_listbox.curselection()
        if not selection:
            messagebox.showwarning("Selection Required", "Please select an article first!")
            return
        
        index = selection[0]
        if index >= len(self.news_aggregator.filtered_articles):
            return
        
        article = self.news_aggregator.filtered_articles[index]
        
        # Create a new top-level window for the summary
        summary_window = tk.Toplevel(self.root)
        summary_window.title(f"Summary - {article['title'][:50]}...")
        summary_window.geometry("1200x650+0+0")  # Increased height slightly for new button
        summary_window.configure(bg='#f8f9fa')
        summary_window.resizable(True, True)
        
        # Make window modal
        summary_window.transient(self.root)
        summary_window.grab_set()
        
        # TTS control variables
        tts_playing = {'is_playing': False, 'process': None}
        
        # Create main scrollable frame
        canvas = tk.Canvas(summary_window, bg='#f8f9fa', highlightthickness=0)
        scrollbar = ttk.Scrollbar(summary_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas, style='Modern.TFrame')
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True, padx=(15, 0), pady=15)
        scrollbar.pack(side="right", fill="y", padx=(0, 15), pady=15)
        
        # Content frame
        content_frame = ttk.Frame(scrollable_frame, padding="20", style='Modern.TFrame')
        content_frame.pack(fill="both", expand=True)
        content_frame.columnconfigure(0, weight=1)
        
        # Article title
        title_label = ttk.Label(
            content_frame, 
            text=f"📰 {article['title']}", 
            font=('Segoe UI', 16, 'bold'), 
            style='Title.TLabel',
            wraplength=600
        )
        title_label.grid(row=0, column=0, pady=(0, 15), sticky="ew")
        
        # Article metadata
        metadata_frame = ttk.Frame(content_frame, style='Modern.TFrame')
        metadata_frame.grid(row=1, column=0, pady=(0, 20), sticky="ew")
        metadata_frame.columnconfigure(0, weight=1)
        
        source_info = f"🔗 {article['source']} • 📅 {article['published'].strftime('%B %d, %Y at %I:%M %p')} • 📂 {article['category']}"
        metadata_label = ttk.Label(
            metadata_frame, 
            text=source_info, 
            font=('Segoe UI', 10), 
            style='Source.TLabel'
        )
        metadata_label.grid(row=0, column=0, sticky="w")
        
        # Try to fetch and display article image
        image_label = None
        try:
            # Attempt to extract image from RSS feed entry
            # This is a simplified approach - you might need to enhance based on your RSS feed structure
            image_url = None
            
            # Try to get image from feed (common RSS image fields)
            import feedparser
            # Re-fetch the specific article to get media content
            for source_name, source_url in self.news_aggregator.news_sources.items():
                if source_name == article['source']:
                    try:
                        feed = feedparser.parse(source_url)
                        for entry in feed.entries:
                            if hasattr(entry, 'link') and entry.link == article['link']:
                                # Try different image fields
                                if hasattr(entry, 'media_thumbnail') and entry.media_thumbnail:
                                    image_url = entry.media_thumbnail[0]['url']
                                elif hasattr(entry, 'media_content') and entry.media_content:
                                    image_url = entry.media_content[0]['url']
                                elif hasattr(entry, 'enclosures') and entry.enclosures:
                                    for enclosure in entry.enclosures:
                                        if enclosure.type.startswith('image/'):
                                            image_url = enclosure.href
                                            break
                                # Try to extract image from description/summary
                                elif hasattr(entry, 'summary'):
                                    import re
                                    img_match = re.search(r'<img[^>]+src="([^"]+)"', entry.summary)
                                    if img_match:
                                        image_url = img_match.group(1)
                                break
                        break
                    except:
                        continue
            
            # If we found an image URL, try to load and display it
            if image_url:
                try:
                    response = requests.get(image_url, timeout=10)
                    if response.status_code == 200:
                        img = Image.open(BytesIO(response.content))
                        
                        # Resize image while maintaining aspect ratio
                        img.thumbnail((400, 300), Image.Resampling.LANCZOS)
                        
                        # Convert to PhotoImage
                        img_tk = ImageTk.PhotoImage(img)
                        
                        # Create image label
                        image_label = ttk.Label(content_frame, image=img_tk)
                        image_label.image = img_tk  # Keep reference
                        image_label.grid(row=2, column=0, pady=(0, 20))
                        
                except Exception as e:
                    print(f"Error loading image: {e}")
                    
        except Exception as e:
            print(f"Error fetching article image: {e}")
        
        # If no image was loaded, show a placeholder
        if image_label is None:
            placeholder_frame = ttk.Frame(content_frame, style='Modern.TFrame')
            placeholder_frame.grid(row=2, column=0, pady=(0, 20))
            
            placeholder_label = ttk.Label(
                placeholder_frame, 
                text="🖼️ No image available", 
                font=('Segoe UI', 12), 
                style='Source.TLabel',
                background='#ecf0f1',
                padding=(20, 40)
            )
            placeholder_label.pack()
        
        # Process article summary with 5000-word limit
        def process_article_summary(text, word_limit=5000):
            """Process article summary with word limit and determine if truncation is needed"""
            import re
            # Remove HTML tags
            clean_text = re.sub(r'<[^>]+>', '', text)
            # Remove extra whitespace
            clean_text = ' '.join(clean_text.split())
            
            words = clean_text.split()
            total_words = len(words)
            
            if total_words <= word_limit:
                return clean_text, False, total_words  # Full text, not truncated, word count
            else:
                truncated = ' '.join(words[:word_limit])
                return truncated, True, total_words  # Truncated text, is truncated, total word count
        
        # Process the summary
        processed_summary, is_truncated, total_words = process_article_summary(article['summary'], 5000)
        
        # Summary section with word count info
        summary_title_text = f"📝 Article Summary ({total_words} words)"
        if is_truncated:
            summary_title_text += f" - Showing first 5,000 words"
        
        summary_title = ttk.Label(
            content_frame, 
            text=summary_title_text, 
            font=('Segoe UI', 12, 'bold'), 
            style='Title.TLabel'
        )
        summary_title.grid(row=3, column=0, pady=(10, 5), sticky="w")
        
        # Create summary text widget
        summary_frame = ttk.Frame(content_frame, style='Modern.TFrame')
        summary_frame.grid(row=4, column=0, pady=(0, 20), sticky="ew")
        summary_frame.columnconfigure(0, weight=1)
        
        # Calculate height based on content length (minimum 8, maximum 20)
        estimated_lines = max(8, min(20, len(processed_summary) // 80))
        
        summary_text = tk.Text(
            summary_frame, 
            height=estimated_lines, 
            font=('Segoe UI', 11), 
            wrap=tk.WORD, 
            bg='white', 
            borderwidth=1, 
            relief='solid',
            highlightthickness=0,
            padx=15,
            pady=15,
            state=tk.NORMAL
        )
        summary_text.grid(row=0, column=0, sticky="ew")
        summary_text.columnconfigure(0, weight=1)
        
        # Insert the processed summary
        summary_text.insert('1.0', processed_summary)
        
        # Add truncation notice if content was truncated
        if is_truncated:
            summary_text.insert(tk.END, f"\n\n{'='*50}\n")
            summary_text.insert(tk.END, f"📖 Content truncated. Full article has {total_words:,} words.\n")
            summary_text.insert(tk.END, "Click 'Read Full Article' button below to view the complete content.")
        
        summary_text.config(state=tk.DISABLED)  # Make read-only
        
        # TTS Functions
        def detect_language(text):
            """Detect language of the text using simple heuristics and langdetect"""
            try:
                from langdetect import detect
                detected_lang = detect(text)
                
                # Map detected language codes to gTTS supported codes
                lang_mapping = {
                    'en': 'en',    # English
                    'es': 'es',    # Spanish
                    'fr': 'fr',    # French
                    'de': 'de',    # German
                    'it': 'it',    # Italian
                    'pt': 'pt',    # Portuguese
                    'ru': 'ru',    # Russian
                    'ja': 'ja',    # Japanese
                    'ko': 'ko',    # Korean
                    'zh': 'zh',    # Chinese
                    'ar': 'ar',    # Arabic
                    'hi': 'hi',    # Hindi
                    'bn': 'bn',    # Bengali
                    'ur': 'ur',    # Urdu
                    'ta': 'ta',    # Tamil
                    'te': 'te',    # Telugu
                    'ml': 'ml',    # Malayalam
                    'kn': 'kn',    # Kannada
                    'gu': 'gu',    # Gujarati
                    'pa': 'pa',    # Punjabi
                    'mr': 'mr',    # Marathi
                    'ne': 'ne',    # Nepali
                    'si': 'si',    # Sinhala
                    'my': 'my',    # Myanmar
                    'th': 'th',    # Thai
                    'vi': 'vi',    # Vietnamese
                    'id': 'id',    # Indonesian
                    'ms': 'ms',    # Malay
                    'tl': 'tl',    # Filipino
                    'sw': 'sw',    # Swahili
                    'tr': 'tr',    # Turkish
                    'pl': 'pl',    # Polish
                    'nl': 'nl',    # Dutch
                    'sv': 'sv',    # Swedish
                    'da': 'da',    # Danish
                    'no': 'no',    # Norwegian
                    'fi': 'fi',    # Finnish
                    'cs': 'cs',    # Czech
                    'sk': 'sk',    # Slovak
                    'hu': 'hu',    # Hungarian
                    'ro': 'ro',    # Romanian
                    'bg': 'bg',    # Bulgarian
                    'hr': 'hr',    # Croatian
                    'sr': 'sr',    # Serbian
                    'sl': 'sl',    # Slovenian
                    'et': 'et',    # Estonian
                    'lv': 'lv',    # Latvian
                    'lt': 'lt',    # Lithuanian
                    'uk': 'uk',    # Ukrainian
                    'be': 'be',    # Belarusian
                    'mk': 'mk',    # Macedonian
                    'sq': 'sq',    # Albanian
                    'ca': 'ca',    # Catalan
                    'eu': 'eu',    # Basque
                    'gl': 'gl',    # Galician
                    'cy': 'cy',    # Welsh
                    'ga': 'ga',    # Irish
                    'mt': 'mt',    # Maltese
                    'is': 'is',    # Icelandic
                    'fa': 'fa',    # Persian
                    'he': 'iw',    # Hebrew (gTTS uses 'iw')
                    'af': 'af',    # Afrikaans
                    'zu': 'zu',    # Zulu
                    'xh': 'xh',    # Xhosa
                    'st': 'st',    # Sesotho
                    'tn': 'tn',    # Setswana
                    'zu': 'zu',    # Zulu
                }
                
                return lang_mapping.get(detected_lang, 'en')  # Default to English
                
            except Exception as e:
                print(f"Language detection error: {e}")
                return 'en'  # Default to English if detection fails
        
        def read_summary_aloud():
            """Read the summary using gTTS with auto-detected language"""
            try:
                # Check if already playing
                if tts_playing['is_playing']:
                    stop_reading()
                    return
                
                # Import required libraries
                try:
                    from gtts import gTTS
                    import pygame
                    import tempfile
                except ImportError as e:
                    missing_lib = str(e).split("'")[1] if "'" in str(e) else "required library"
                    messagebox.showerror(
                        "Missing Library", 
                        f"Please install {missing_lib}:\n\n"
                        f"pip install gtts pygame langdetect\n\n"
                        f"Then restart the application."
                    )
                    return
                
                # Update button to show "Preparing..."
                read_btn.config(text="🔄 Preparing...", state='disabled')
                summary_window.update()
                
                def tts_thread():
                    try:
                        # Prepare text for reading (first 1000 words to avoid very long audio)
                        words = processed_summary.split()
                        reading_text = ' '.join(words[:1000])  # Limit to 1000 words for reasonable audio length
                        
                        if len(words) > 1000:
                            reading_text += "... The full article continues online."
                        
                        # Detect language
                        detected_lang = detect_language(reading_text)
                        print(f"Detected language: {detected_lang}")
                        
                        # Create TTS object
                        tts = gTTS(text=reading_text, lang=detected_lang, slow=False)
                        
                        # Create temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as tmp_file:
                            tts.save(tmp_file.name)
                            audio_file = tmp_file.name
                        
                        # Initialize pygame mixer
                        pygame.mixer.init()
                        
                        # Load and play audio
                        pygame.mixer.music.load(audio_file)
                        
                        # Update UI on main thread
                        def update_ui_playing():
                            tts_playing['is_playing'] = True
                            read_btn.config(text="⏹️ Stop Reading", state='normal')
                            
                            # Show language info
                            lang_names = {
                                'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German',
                                'it': 'Italian', 'pt': 'Portuguese', 'ru': 'Russian', 'ja': 'Japanese',
                                'ko': 'Korean', 'zh': 'Chinese', 'ar': 'Arabic', 'hi': 'Hindi',
                                'bn': 'Bengali', 'ur': 'Urdu', 'ta': 'Tamil', 'te': 'Telugu',
                                'ml': 'Malayalam', 'kn': 'Kannada', 'gu': 'Gujarati', 'pa': 'Punjabi',
                                'mr': 'Marathi', 'ne': 'Nepali', 'si': 'Sinhala', 'my': 'Myanmar',
                                'th': 'Thai', 'vi': 'Vietnamese', 'id': 'Indonesian', 'ms': 'Malay',
                                'tl': 'Filipino', 'sw': 'Swahili', 'tr': 'Turkish', 'pl': 'Polish',
                                'nl': 'Dutch', 'sv': 'Swedish', 'da': 'Danish', 'no': 'Norwegian',
                                'fi': 'Finnish', 'cs': 'Czech', 'sk': 'Slovak', 'hu': 'Hungarian',
                                'ro': 'Romanian', 'bg': 'Bulgarian', 'hr': 'Croatian', 'sr': 'Serbian',
                                'sl': 'Slovenian', 'et': 'Estonian', 'lv': 'Latvian', 'lt': 'Lithuanian',
                                'uk': 'Ukrainian', 'be': 'Belarusian', 'mk': 'Macedonian', 'sq': 'Albanian',
                                'ca': 'Catalan', 'eu': 'Basque', 'gl': 'Galician', 'cy': 'Welsh',
                                'ga': 'Irish', 'mt': 'Maltese', 'is': 'Icelandic', 'fa': 'Persian',
                                'iw': 'Hebrew', 'af': 'Afrikaans', 'zu': 'Zulu', 'xh': 'Xhosa'
                            }
                            lang_name = lang_names.get(detected_lang, detected_lang.upper())
                            
                            # Update status
                            if hasattr(summary_window, 'winfo_exists') and summary_window.winfo_exists():
                                try:
                                    self.status_var.set(f"🔊 Reading article summary in {lang_name}...")
                                except:
                                    pass
                        
                        summary_window.after(0, update_ui_playing)
                        
                        # Play audio
                        pygame.mixer.music.play()
                        
                        # Wait for playback to finish
                        while pygame.mixer.music.get_busy():
                            pygame.time.wait(100)
                            if not tts_playing['is_playing']:  # Check if stopped
                                break
                        
                        # Clean up
                        pygame.mixer.music.stop()
                        pygame.mixer.quit()
                        
                        # Remove temporary file
                        try:
                            os.unlink(audio_file)
                        except:
                            pass
                        
                        # Update UI when finished
                        def update_ui_finished():
                            if hasattr(summary_window, 'winfo_exists') and summary_window.winfo_exists():
                                try:
                                    tts_playing['is_playing'] = False
                                    read_btn.config(text="🔊 Read Summary", state='normal')
                                    self.status_var.set("🔇 Reading completed")
                                except:
                                    pass
                        
                        summary_window.after(0, update_ui_finished)
                        
                    except Exception as e:
                        error_msg = f"TTS Error: {str(e)}"
                        print(error_msg)
                        
                        def show_error():
                            if hasattr(summary_window, 'winfo_exists') and summary_window.winfo_exists():
                                try:
                                    tts_playing['is_playing'] = False
                                    read_btn.config(text="🔊 Read Summary", state='normal')
                                    messagebox.showerror("Text-to-Speech Error", f"Could not read summary:\n{error_msg}")
                                except:
                                    pass
                        
                        summary_window.after(0, show_error)
                
                # Start TTS in background thread
                threading.Thread(target=tts_thread, daemon=True).start()
                
            except Exception as e:
                tts_playing['is_playing'] = False
                read_btn.config(text="🔊 Read Summary", state='normal')
                messagebox.showerror("Error", f"Could not initialize text-to-speech: {str(e)}")
        
        def stop_reading():
            """Stop the current TTS playback"""
            try:
                import pygame
                if pygame.mixer.get_init():
                    pygame.mixer.music.stop()
                    pygame.mixer.quit()
                
                tts_playing['is_playing'] = False
                read_btn.config(text="🔊 Read Summary", state='normal')
                self.status_var.set("🔇 Reading stopped")
                
            except Exception as e:
                print(f"Error stopping TTS: {e}")
        
        # Action buttons frame
        button_frame = ttk.Frame(content_frame, style='Modern.TFrame')
        button_frame.grid(row=5, column=0, pady=(10, 0))
        
        def open_full_article():
            """Open the full article in browser"""
            try:
                # Stop reading if in progress
                if tts_playing['is_playing']:
                    stop_reading()
                
                webbrowser.open(article['link'])
                self.status_var.set(f"🌐 Opened: {article['title'][:50]}...")
                summary_window.destroy()  # Close summary window after opening article
            except Exception as e:
                messagebox.showerror("Error", f"Could not open article: {str(e)}")
        
        def add_to_favorites():
            """Add article to favorites"""
            if self.news_aggregator.add_to_favorites(article):
                messagebox.showinfo("Success", f"Added to favorites!")
                self.update_stats()  # Update the main window stats
            else:
                messagebox.showwarning("Info", "Article is already in favorites!")
        
        def copy_article_link():
            """Copy article link to clipboard"""
            summary_window.clipboard_clear()
            summary_window.clipboard_append(article['link'])
            messagebox.showinfo("Copied", "Article link copied to clipboard!")
        
        # Create buttons with modern styling
        # Make "Read Full Article" button more prominent if content is truncated
        read_more_text = "📖 Read Full Article" if is_truncated else "📖 View Online"
        if is_truncated:
            read_more_text += f" ({total_words:,} words)"
        
        read_more_btn = ttk.Button(
            button_frame, 
            text=read_more_text, 
            command=open_full_article, 
            style='Modern.TButton'
        )
        read_more_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        # Add TTS Read Summary button
        read_btn = ttk.Button(
            button_frame, 
            text="🔊 Read Summary", 
            command=read_summary_aloud, 
            style='Modern.TButton'
        )
        read_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        favorite_btn = ttk.Button(
            button_frame, 
            text="⭐ Add to Favorites", 
            command=add_to_favorites, 
            style='Modern.TButton'
        )
        favorite_btn.pack(side=tk.LEFT, padx=(0, 10))
        
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
            command=lambda: [stop_reading() if tts_playing['is_playing'] else None, summary_window.destroy()], 
            style='Modern.TButton'
        )
        close_btn.pack(side=tk.LEFT)
        
        # Add info label if content was truncated
        if is_truncated:
            info_frame = ttk.Frame(content_frame, style='Modern.TFrame')
            info_frame.grid(row=6, column=0, pady=(10, 0))
            
            info_label = ttk.Label(
                info_frame,
                text=f"ℹ️ This article has been truncated to 5,000 words. Click 'Read Full Article' to view all {total_words:,} words online.",
                font=('Segoe UI', 9, 'italic'),
                style='Source.TLabel',
                wraplength=600
            )
            info_label.pack()
        
        # Add TTS info label
        tts_info_frame = ttk.Frame(content_frame, style='Modern.TFrame')
        tts_info_frame.grid(row=7, column=0, pady=(5, 0))
        
        tts_info_label = ttk.Label(
            tts_info_frame,
            text="🎵 Audio reading is limited to first 1,000 words for optimal performance. Language is auto-detected.",
            font=('Segoe UI', 8, 'italic'),
            style='Source.TLabel',
            wraplength=600
        )
        tts_info_label.pack()
        
        # Bind mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        # Bind mousewheel to canvas
        canvas.bind("<MouseWheel>", _on_mousewheel)  # Windows
        canvas.bind("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))  # Linux
        canvas.bind("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))   # Linux
        
        # Focus on the window
        summary_window.focus_set()
        
        # Handle window closing
        def on_summary_close():
            # Stop TTS if playing
            if tts_playing['is_playing']:
                stop_reading()
            summary_window.grab_release()
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
        """Show favorites window"""
        if not self.news_aggregator.favorites:
            messagebox.showinfo("Favorites", "No favorite articles saved yet!")
            return
        
        # Create favorites window
        fav_window = tk.Toplevel(self.root)
        fav_window.title("⭐ Favorite Articles")
        fav_window.geometry("800x600")
        fav_window.configure(bg='#f8f9fa')
        
        # Main frame
        main_frame = ttk.Frame(fav_window, padding="15")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Header
        header_label = ttk.Label(main_frame, text="⭐ Your Favorite Articles", 
                                font=('Segoe UI', 14, 'bold'), style='Title.TLabel')
        header_label.grid(row=0, column=0, pady=(0, 15))
        
        # Favorites list
        list_frame = ttk.Frame(main_frame)
        list_frame.grid(row=1, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        fav_listbox = tk.Listbox(list_frame, font=('Segoe UI', 10), bg='white',
                                borderwidth=1, relief='solid', highlightthickness=0)
        fav_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=fav_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        fav_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Populate favorites
        for i, article in enumerate(self.news_aggregator.favorites):
            date_str = article['published'].strftime('%m/%d/%Y %H:%M')
            display_text = f"{self.get_category_emoji(article['category'])} {article['title']} • {article['source']} • {date_str}"
            fav_listbox.insert(tk.END, display_text)
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
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
                if messagebox.askyesno("Confirm", f"Remove '{article['title'][:50]}...' from favorites?"):
                    self.news_aggregator.remove_from_favorites(article['id'])
                    fav_listbox.delete(selection[0])
                    self.update_stats()
        
        ttk.Button(button_frame, text="🔗 Open Article", command=open_favorite,
                  style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="🗑️ Remove", command=remove_favorite,
                  style='Modern.TButton').pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="✖️ Close", command=fav_window.destroy,
                  style='Modern.TButton').pack(side=tk.LEFT)
        
        # Double-click to open
        fav_listbox.bind('<Double-Button-1>', lambda e: open_favorite())
    
    def auto_refresh(self):
        """Auto-refresh news every 30 minutes"""
        self.refresh_news()
        # Schedule next refresh (30 minutes = 1800000 milliseconds)
        self.root.after(1800000, self.auto_refresh)

def main():
    """Main application entry point"""
    root = tk.Tk()
    app = NewsApp(root)
    
    # # Handle window closing
    # def on_closing():
    #     if messagebox.askokcancel("Quit", "Do you want to quit the News Hub?"):
    #         root.destroy()
    
    # root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Center window on screen
    # root.update_idletasks()
    # width = root.winfo_width()
    # height = root.winfo_height()
    # x = (root.winfo_screenwidth() // 2) - (width // 2)
    # y = (root.winfo_screenheight() // 2) - (height // 2)
    # root.geometry(f"{width}x{height}+{x}+{y}")
    
    # Start the application
    root.mainloop()
    
if __name__ == "__main__":
    main()