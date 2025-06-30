import React, { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  Eye, 
  Heart, 
  MessageCircle, 
  Globe, 
  Play, 
  Sparkles,
  Database,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Calendar,
  BarChart3
} from 'lucide-react';

const FASTAPI_BASE_URL = "http://localhost:8000";

function App() {
  const [countries, setCountries] = useState([]);
  const [selectedCountry, setSelectedCountry] = useState('US');
  const [trendingVideos, setTrendingVideos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [stats, setStats] = useState(null);
  const [categories, setCategories] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [lastRefresh, setLastRefresh] = useState(new Date());
  const [activeTab, setActiveTab] = useState('trending'); // 'trending' or 'categories'

  // Fetch countries on component mount
  useEffect(() => {
    const fetchCountries = async () => {
      try {
        const response = await fetch(`${FASTAPI_BASE_URL}/countries`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setCountries(data);
        if (data.includes('US')) {
          setSelectedCountry('US');
        } else if (data.length > 0) {
          setSelectedCountry(data[0]);
        }
      } catch (e) {
        setError("Failed to fetch countries: " + e.message);
        console.error("Error fetching countries:", e);
      }
    };
    fetchCountries();
  }, []);

  // Fetch trending videos whenever selectedCountry changes
  useEffect(() => {
    const fetchVideos = async () => {
      if (!selectedCountry || activeTab !== 'trending') return;

      setLoading(true);
      setError(null);
      try {
        const response = await fetch(`${FASTAPI_BASE_URL}/trending-videos/${selectedCountry}?limit=50`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        const data = await response.json();
        setTrendingVideos(data);
      } catch (e) {
        setError(`Failed to fetch trending videos for ${selectedCountry}: ` + e.message);
        console.error(`Error fetching videos for ${selectedCountry}:`, e);
        setTrendingVideos([]);
      } finally {
        setLoading(false);
      }
    };
    fetchVideos();
  }, [selectedCountry, activeTab]);

  const formatNumber = (num) => {
    if (num >= 1000000) {
      return (num / 1000000).toFixed(1) + 'M';
    } else if (num >= 1000) {
      return (num / 1000).toFixed(1) + 'K';
    }
    return num?.toLocaleString() || '0';
  };

  const getViralColor = (isViral) => {
    return isViral ? 'text-pink-400' : 'text-gray-400';
  };

  const getCategoryColor = (category) => {
    const colors = {
      'Music': 'bg-purple-500/20 text-purple-300 border-purple-500/30',
      'Gaming': 'bg-green-500/20 text-green-300 border-green-500/30',
      'Sports': 'bg-orange-500/20 text-orange-300 border-orange-500/30',
      'Entertainment': 'bg-pink-500/20 text-pink-300 border-pink-500/30',
      'News': 'bg-red-500/20 text-red-300 border-red-500/30',
      'Education': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    };
    return colors[category] || 'bg-gray-500/20 text-gray-300 border-gray-500/30';
  };

  const fetchCategoriesStats = async () => {
    try {
      const response = await fetch(`${FASTAPI_BASE_URL}/categories/stats`);
      if (!response.ok) throw new Error('Failed to fetch stats');
      const data = await response.json();
      setStats(data);
    } catch (err) {
      setError(err.message);
    }
  };

  const fetchCategories = async () => {
    try {
      const response = await fetch(`${FASTAPI_BASE_URL}/categories`);
      if (!response.ok) throw new Error('Failed to fetch categories');
      const data = await response.json();
      setCategories(data.categories || []);
    } catch (err) {
      setError(err.message);
    }
  };

  const refreshCategories = async () => {
    setRefreshing(true);
    try {
      const response = await fetch(`${FASTAPI_BASE_URL}/refresh-categories`, {
        method: 'POST',
      });
      if (!response.ok) throw new Error('Failed to refresh categories');
      await fetchCategoriesStats();
      await fetchCategories();
      setLastRefresh(new Date());
    } catch (err) {
      setError(err.message);
    } finally {
      setRefreshing(false);
    }
  };

  // Load categories data when categories tab is active
  useEffect(() => {
    const loadCategoriesData = async () => {
      if (activeTab !== 'categories') return;
      
      setLoading(true);
      await Promise.all([fetchCategoriesStats(), fetchCategories()]);
      setLoading(false);
    };
    
    loadCategoriesData();

    // Auto-refresh every 5 minutes when categories tab is active
    let interval;
    if (activeTab === 'categories') {
      interval = setInterval(fetchCategoriesStats, 5 * 60 * 1000);
    }
    
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [activeTab]);

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleString();
  };

  const formatDuration = (hours) => {
    if (!hours) return 'N/A';
    if (hours < 1) return `${Math.round(hours * 60)} minutes`;
    if (hours < 24) return `${Math.round(hours)} hours`;
    return `${Math.round(hours / 24)} days`;
  };

  const getCacheStatus = () => {
    if (!stats) return { status: 'unknown', color: 'gray', icon: AlertCircle };
    
    if (stats.cache_valid) {
      return { status: 'Valid', color: 'green', icon: CheckCircle };
    } else {
      return { status: 'Expired', color: 'red', icon: AlertCircle };
    }
  };

  const cacheStatus = getCacheStatus();
  const StatusIcon = cacheStatus.icon;

  const renderTrendingContent = () => (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-8">
      {/* Sidebar */}
      <aside className="lg:col-span-1">
        <div className="bg-black/20 backdrop-blur-xl rounded-3xl border border-white/10 p-6 shadow-2xl">
          <div className="flex items-center gap-3 mb-6">
            <Globe className="w-6 h-6 text-blue-400" />
            <h2 className="text-xl font-semibold text-white">Filters</h2>
          </div>
          
          {error && (
            <div className="mb-4 p-4 bg-red-500/20 border border-red-500/30 rounded-xl text-red-300">
              {error}
            </div>
          )}
          
          <div className="space-y-2">
            <label htmlFor="country-select" className="block text-sm font-medium text-gray-300 mb-3">
              Select Country
            </label>
            <select
              id="country-select"
              value={selectedCountry}
              onChange={(e) => setSelectedCountry(e.target.value)}
              className="w-full px-4 py-3 bg-white/5 border border-white/20 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all duration-200 backdrop-blur-sm"
            >
              {countries.length > 0 ? (
                countries.map(country => (
                  <option key={country} value={country} className="bg-slate-800 text-white">
                    {country}
                  </option>
                ))
              ) : (
                <option value="" className="bg-slate-800 text-gray-400">Loading countries...</option>
              )}
            </select>
          </div>

          {/* Stats Card */}
          <div className="mt-8 p-4 bg-gradient-to-r from-blue-500/10 to-purple-500/10 rounded-xl border border-blue-500/20">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="w-5 h-5 text-blue-400" />
              <span className="text-sm font-medium text-blue-300">Currently Tracking</span>
            </div>
            <div className="text-2xl font-bold text-white">{trendingVideos.length}</div>
            <div className="text-sm text-gray-400">trending videos</div>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="lg:col-span-3">
        <div className="bg-black/20 backdrop-blur-xl rounded-3xl border border-white/10 shadow-2xl overflow-hidden">
          <div className="p-6 border-b border-white/10">
            <h2 className="text-2xl font-bold text-white flex items-center gap-3">
              <Sparkles className="w-7 h-7 text-yellow-400" />
              Trending in {selectedCountry}
            </h2>
            <p className="text-gray-400 mt-1">Real-time viral content analysis</p>
          </div>

          <div className="p-6">
            {loading ? (
              <div className="flex items-center justify-center py-16">
                <div className="relative">
                  <div className="w-16 h-16 border-4 border-blue-500/20 border-t-blue-500 rounded-full animate-spin"></div>
                  <div className="absolute inset-0 w-16 h-16 border-4 border-pink-500/20 border-t-pink-500 rounded-full animate-spin animate-reverse delay-150"></div>
                </div>
              </div>
            ) : error ? (
              <div className="text-center py-16">
                <div className="text-red-400 text-lg font-medium">{error}</div>
              </div>
            ) : trendingVideos.length > 0 ? (
              <div className="space-y-4">
                {trendingVideos.map((video, index) => (
                  <div
                    key={video.video_id}
                    className="group p-6 bg-white/5 hover:bg-white/10 rounded-2xl border border-white/10 hover:border-white/20 transition-all duration-300 hover:shadow-xl hover:shadow-purple-500/10 opacity-0 animate-fadeInUp"
                    style={{
                      animationDelay: `${index * 50}ms`,
                      animationFillMode: 'forwards'
                    }}
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex-1">
                        <h3 className="text-lg font-semibold text-white group-hover:text-blue-300 transition-colors duration-200 line-clamp-2 mb-2">
                          {video.title}
                        </h3>
                        <p className="text-gray-400 font-medium">{video.channel_title}</p>
                      </div>
                      <div className={`px-3 py-1 rounded-full border text-xs font-medium ${getCategoryColor(video.category_name)}`}>
                        {video.category_name}
                      </div>
                    </div>

                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                      <div className="flex items-center gap-2 text-gray-300">
                        <Eye className="w-4 h-4 text-blue-400" />
                        <span className="text-sm font-medium">{formatNumber(video.view_count)}</span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-300">
                        <Heart className="w-4 h-4 text-red-400" />
                        <span className="text-sm font-medium">{formatNumber(video.like_count)}</span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-300">
                        <MessageCircle className="w-4 h-4 text-green-400" />
                        <span className="text-sm font-medium">{formatNumber(video.comment_count)}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Sparkles className={`w-4 h-4 ${getViralColor(video.is_viral_spike)}`} />
                        <span className={`text-sm font-medium ${getViralColor(video.is_viral_spike)}`}>
                          {video.is_viral_spike ? 'Viral!' : 'Trending'}
                        </span>
                      </div>
                    </div>

                    {video.view_count_change && (
                      <div className="mt-4 pt-4 border-t border-white/10">
                        <div className="flex items-center gap-2 text-green-400">
                          <TrendingUp className="w-4 h-4" />
                          <span className="text-sm font-medium">+{formatNumber(video.view_count_change)} views</span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-center py-16">
                <div className="w-24 h-24 mx-auto mb-6 bg-gradient-to-r from-gray-500/20 to-gray-600/20 rounded-full flex items-center justify-center">
                  <Play className="w-12 h-12 text-gray-400" />
                </div>
                <p className="text-gray-400 text-lg">No trending video data available for the selected country.</p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );

  const renderCategoriesContent = () => (
    <div className="max-w-7xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
              <BarChart3 className="text-purple-400" />
              Video Categories Dashboard
            </h1>
            <p className="text-gray-300">Monitor and manage YouTube video categories cache</p>
          </div>
          <button
            onClick={refreshCategories}
            disabled={refreshing}
            className="flex items-center gap-2 bg-purple-600 hover:bg-purple-700 disabled:bg-purple-800 text-white px-6 py-3 rounded-lg font-medium transition-all duration-200 transform hover:scale-105 disabled:scale-100"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
            {refreshing ? 'Refreshing...' : 'Refresh Categories'}
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <div className="bg-white/10 backdrop-blur-md rounded-xl p-6 border border-white/20">
          <div className="flex items-center gap-3 mb-4">
            <Database className="w-8 h-8 text-blue-400" />
            <h3 className="text-lg font-semibold text-white">Total Categories</h3>
          </div>
          <p className="text-3xl font-bold text-blue-400">
            {stats?.total_categories || 0}
          </p>
        </div>
      </div>

      {/* Last Refresh Info */}
      <div className="mb-6 bg-white/5 backdrop-blur-md rounded-lg p-4 border border-white/10">
        <div className="flex items-center gap-2 text-gray-300">
          <TrendingUp className="w-4 h-4" />
          <span className="text-sm">
            Dashboard last refreshed: {lastRefresh.toLocaleString()}
          </span>
        </div>
      </div>

      {/* Categories Table */}
      <div className="bg-white/10 backdrop-blur-md rounded-xl border border-white/20 overflow-hidden">
        <div className="p-6 border-b border-white/20">
          <h2 className="text-2xl font-bold text-white flex items-center gap-2">
            <Database className="w-6 h-6 text-purple-400" />
            Categories List
          </h2>
          <p className="text-gray-300 mt-1">
            {categories.length} categories loaded from cache
          </p>
        </div>
        
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-white/5">
              <tr>
                <th className="text-left p-4 text-gray-300 font-medium">ID</th>
                <th className="text-left p-4 text-gray-300 font-medium">Name</th>
                <th className="text-left p-4 text-gray-300 font-medium">Assignable</th>
                <th className="text-left p-4 text-gray-300 font-medium">Last Updated</th>
              </tr>
            </thead>
            <tbody>
              {categories.length === 0 ? (
                <tr>
                  <td colSpan="4" className="text-center p-8 text-gray-400">
                    No categories data available
                  </td>
                </tr>
              ) : (
                categories.map((category, index) => (
                  <tr 
                    key={category.id} 
                    className={`border-t border-white/10 hover:bg-white/5 transition-colors ${
                      index % 2 === 0 ? 'bg-white/2' : ''
                    }`}
                  >
                    <td className="p-4 font-mono text-purple-300">{category.id}</td>
                    <td className="p-4 text-white font-medium">{category.name}</td>
                    <td className="p-4">
                      <span 
                        className={`px-2 py-1 rounded-full text-xs font-medium ${
                          category.assignable === 'true' 
                            ? 'bg-green-500/20 text-green-300 border border-green-500/30' 
                            : 'bg-red-500/20 text-red-300 border border-red-500/30'
                        }`}
                      >
                        {category.assignable === 'true' ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="p-4 text-gray-300 text-sm">
                      {formatDate(category.last_updated)}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer */}
      <div className="mt-8 text-center text-gray-400 text-sm">
        <p>Categories are automatically refreshed every 24 hours to optimize API usage.</p>
      </div>
    </div>
  );

  if (loading && activeTab === 'categories' && categories.length === 0) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 flex items-center justify-center">
        <div className="text-center">
          <div className="w-16 h-16 border-4 border-purple-500 border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
          <p className="text-white text-lg">Loading categories data...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated background elements */}
      <div className="fixed inset-0 overflow-hidden pointer-events-none">
        <div className="absolute -top-40 -right-40 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl animate-pulse"></div>
        <div className="absolute -bottom-40 -left-40 w-80 h-80 bg-blue-500/10 rounded-full blur-3xl animate-pulse delay-1000"></div>
      </div>

      {/* Header */}
      <header className="relative z-10 bg-black/20 backdrop-blur-xl border-b border-white/10">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="p-3 bg-gradient-to-r from-red-500 to-pink-500 rounded-2xl shadow-lg shadow-red-500/25">
                <Play className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-4xl font-bold bg-gradient-to-r from-white via-gray-100 to-gray-300 bg-clip-text text-transparent">
                  YouTube Dashboard
                </h1>
                <p className="text-gray-400 mt-1">Discover trending content and manage categories</p>
              </div>
            </div>

            {/* Tab Navigation */}
            <div className="flex bg-black/30 rounded-xl p-1">
              <button
                onClick={() => setActiveTab('trending')}
                className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 ${
                  activeTab === 'trending'
                    ? 'bg-blue-500 text-white shadow-lg'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                Trending Videos
              </button>
              <button
                onClick={() => setActiveTab('categories')}
                className={`px-6 py-2 rounded-lg font-medium transition-all duration-200 ${
                  activeTab === 'categories'
                    ? 'bg-purple-500 text-white shadow-lg'
                    : 'text-gray-300 hover:text-white hover:bg-white/10'
                }`}
              >
                Categories
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="px-6 py-8 relative z-10">
        {error && (
          <div className="max-w-7xl mx-auto mb-6 bg-red-900/50 border border-red-500 text-red-100 px-4 py-3 rounded-lg flex items-center gap-2">
            <AlertCircle className="w-5 h-5" />
            <span>Error: {error}</span>
          </div>
        )}

        {activeTab === 'trending' ? renderTrendingContent() : renderCategoriesContent()}
      </div>

      <style jsx>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        .animate-fadeInUp {
          animation: fadeInUp 0.6s ease-out forwards;
        }
        
        .animate-reverse {
          animation-direction: reverse;
        }
        
        .line-clamp-2 {
          display: -webkit-box;
          -webkit-line-clamp: 2;
          -webkit-box-orient: vertical;
          overflow: hidden;
        }
      `}</style>
    </div>
  );
}

export default App;